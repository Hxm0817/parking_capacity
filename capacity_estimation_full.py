import pandas as pd
import geopandas as gpd
from shapely import wkt
import numpy as np
import os
import matplotlib.pyplot as plt
from sklearn.metrics import mean_absolute_error


CONFIG = {
    "TARGET_ZIPS": ['94105', '94109', '94110', '94112', '94133'],

    "PARKING_SPACE_LENGTH": 22.0,  # ft
    "CURB_EFFICIENCY": 0.75,  # discount factor (eg, driveways, entrance)
    "INTERSECTION_BUFFER": 20.0,  # 20ft reduction per intersection

    "WIDTH_MIN_PARKING": 24.0,  # Width < 24ft: No parking
    "WIDTH_TWO_SIDES": 36.0,  # Width >= 36ft: Both sides

    # File Paths
    "DATA_DIR": "data/",
    "OUTPUT_DIR": "results/",
    "PROJECTED_CRS": "EPSG:26910"  # UTM Zone 10N for accurate length calculation
}

if not os.path.exists(CONFIG["OUTPUT_DIR"]):
    os.makedirs(CONFIG["OUTPUT_DIR"])


def infer_street_width(area, perimeter):
    """Derives equivalent street width from ROW polygon Area and Perimeter."""
    discriminant = perimeter ** 2 - 16 * area
    if discriminant >= 0:
        # Solve quadratic: 2W^2 - PW + 2A = 0; take the smaller root for width
        return (perimeter - np.sqrt(discriminant)) / 4
    return 30.0  # Default fallback width


def get_demand_profile(df, day_type_filter):
    """Generates a 24-hour occupancy profile from SFpark sensor data."""
    sub_df = df[df['DAY_TYPE'].str.contains(day_type_filter, case=False, na=False)].copy()
    # Clean and convert occupancy columns
    for col in ['TOTAL_OCCUPIED_TIME', 'TOTAL_TIME']:
        sub_df[col] = pd.to_numeric(sub_df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

    sub_df['occ_rate'] = np.where(sub_df['TOTAL_TIME'] > 0, sub_df['TOTAL_OCCUPIED_TIME'] / sub_df['TOTAL_TIME'], 0)
    sub_df['hour'] = (pd.to_numeric(sub_df['TIME_OF_DAY'], errors='coerce') // 100).fillna(0).astype(int)

    return sub_df.groupby('hour')['occ_rate'].mean().reindex(range(24)).interpolate().ffill().bfill().fillna(0.5)


def process_parking_optimization(zip_code, gdf_zips, gdf_census, df_sweeping, width_lookup, df_occ_raw):
    """Main execution logic for a single ZIP code area."""
    target_poly = gdf_zips[gdf_zips['zip'].astype(str) == str(zip_code)]
    gdf_zip_segments = gpd.sjoin(gdf_census, target_poly[['geometry']], how='inner', predicate='intersects').copy()

    # Calculate physical segment length in feet
    gdf_proj = gdf_zip_segments.to_crs(CONFIG["PROJECTED_CRS"])
    gdf_zip_segments['length_ft'] = gdf_proj.geometry.length * 3.28084

    # Generate 168-hour demand profile
    weekday_prof = get_demand_profile(df_occ_raw, 'weekday').values
    weekend_prof = get_demand_profile(df_occ_raw, 'weekend').values
    demand_168 = np.concatenate([np.tile(weekday_prof, 5), np.tile(weekend_prof, 2)])

    current_supply = np.zeros(168)
    optimized_supply = np.zeros(168)
    initial_total_cost = 0
    optimized_total_cost = 0
    validation_records = []

    day_map = {'Mon': 0, 'Tue': 1, 'Wed': 2, 'Thu': 3, 'Fri': 4, 'Sat': 5, 'Sun': 6}

    for _, row in gdf_zip_segments.iterrows():
        cnn = str(int(row['CNN']))
        width = width_lookup.get(cnn, 30.0)

        sides = 2 if width >= CONFIG["WIDTH_TWO_SIDES"] else (1 if width >= CONFIG["WIDTH_MIN_PARKING"] else 0)

        # Physical Estimation (Static Capacity)
        usable_length = max(0, row['length_ft'] - 2 * CONFIG["INTERSECTION_BUFFER"])
        static_cap = np.floor((usable_length * sides * CONFIG["CURB_EFFICIENCY"]) / CONFIG["PARKING_SPACE_LENGTH"])

        validation_records.append({
            'CNN': cnn,
            'Street': row['ST_NAME'],
            'Estimated_Cap': static_cap,
            'Census_True': row['PRKG_SPLY']
        })

        # Temporal Masking (Street Sweeping)
        mask = np.ones(168)
        rules = df_sweeping[df_sweeping['CNN'].astype(str) == cnn]
        for _, rule in rules.iterrows():
            day_idx = next((v for k, v in day_map.items() if k in str(rule['WeekDay'])), None)
            if day_idx is not None:
                for h in range(int(rule['FromHour']), int(rule['ToHour'])):
                    mask[day_idx * 24 + h] = 0

        curr_row_supply = mask * static_cap
        current_supply += curr_row_supply

        # Calculate Costs (Demand * Capacity Loss)
        original_loss = static_cap - curr_row_supply
        initial_cost = np.sum(demand_168 * original_loss)
        initial_total_cost += initial_cost

        # Temporal Shift Optimization (Find best shift s within +/- 12 hours)
        best_s, min_cost = 0, initial_cost
        for s in range(-12, 13):
            test_cost = np.sum(demand_168 * np.roll(original_loss, s))
            if test_cost < min_cost:
                min_cost, best_s = test_cost, s

        optimized_total_cost += min_cost
        optimized_supply += np.roll(curr_row_supply, best_s)

    df_val = pd.DataFrame(validation_records)
    mae = mean_absolute_error(df_val['Census_True'], df_val['Estimated_Cap'])
    reduction = (initial_total_cost - optimized_total_cost) / initial_total_cost * 100 if initial_total_cost > 0 else 0

    # Save validation report
    df_val.to_csv(f"{CONFIG['OUTPUT_DIR']}/validation_{zip_code}.csv", index=False)

    return zip_code, mae, reduction, current_supply, optimized_supply, demand_168


if __name__ == "__main__":
    # Pre-load data
    df_zips = pd.read_csv(os.path.join(CONFIG["DATA_DIR"], 'San_Francisco_ZIP_Codes.csv'))
    gdf_zips = gpd.GeoDataFrame(df_zips, geometry=df_zips['geometry'].apply(wkt.loads), crs="EPSG:4326")

    df_census = pd.read_csv(os.path.join(CONFIG["DATA_DIR"], 'On-Street_Parking_Census.csv'))
    gdf_census = gpd.GeoDataFrame(df_census, geometry=df_census['shape'].apply(wkt.loads), crs="EPSG:4326")

    df_sweeping = pd.read_csv(os.path.join(CONFIG["DATA_DIR"], 'Street_Sweeping_Schedule.csv'))
    df_row = pd.read_csv(os.path.join(CONFIG["DATA_DIR"], 'Right_of_Way_Polygons.csv'))
    df_occ_raw = pd.read_csv(os.path.join(CONFIG["DATA_DIR"], 'SFpark_ParkingSensorData_HourlyOccupancy_20112013.csv'),
                             low_memory=False)

    width_lookup = {}
    for _, row in df_row.iterrows():
        try:
            area = float(str(row['Shape_Area']).replace(',', ''))
            leng = float(str(row['Shape_Leng']).replace(',', ''))
            width_lookup[str(int(row['CNN']))] = infer_street_width(area, leng)
        except:
            continue

    # Process all ZIP codes
    for z in CONFIG["TARGET_ZIPS"]:
        zip_id, mae, gain, cur_s, opt_s, dmd = process_parking_optimization(z, gdf_zips, gdf_census, df_sweeping,
                                                                            width_lookup, df_occ_raw)

        print(f"ZIP: {zip_id} | MAE: {mae:.2f} | Efficiency Gain: {gain:.2f}%")

        # Plotting results for each ZIP
        plt.figure(figsize=(12, 6))
        plt.plot(cur_s, label='Baseline Supply', alpha=0.5, linestyle='--')
        plt.plot(opt_s, label='Optimized Supply', color='green', linewidth=2)
        plt.plot(dmd * (max(opt_s) / 1), label='Demand Pattern (Scaled)', color='blue', alpha=0.3)
        plt.title(f"Dynamic Supply Optimization - ZIP {zip_id}")
        plt.xlabel("Weekly Hour")
        plt.ylabel("Capacity")
        plt.legend()
        plt.savefig(f"{CONFIG['OUTPUT_DIR']}/plot_{zip_id}.png")
        plt.close()