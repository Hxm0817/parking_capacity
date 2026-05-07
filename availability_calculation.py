import pandas as pd
import geopandas as gpd
from shapely import wkt
import os

# Configuration and Day Mapping
DAY_MAP = {
    'Monday': 0, 'Mon': 0,
    'Tuesday': 1, 'Tues': 1,
    'Wednesday': 2, 'Wed': 2,
    'Thursday': 3, 'Thu': 3, 'Thurs': 3,
    'Friday': 4, 'Fri': 4,
    'Saturday': 5, 'Sat': 5,
    'Sunday': 6, 'Sun': 6
}


def get_day_index(day_str):
    """Maps weekday strings to integer indices (0-6)."""
    for key, value in DAY_MAP.items():
        if key in day_str:
            return value
    return None


def generate_availability_csv(zip_code, gdf_zips, gdf_census, df_sweeping, output_dir="output"):
    """
    Processes a single ZIP code to generate a 168-hour parking availability mask
    based on street sweeping regulations.
    """
    # Filter target ZIP boundary
    target_zip = gdf_zips[gdf_zips['zip'].astype(str) == str(zip_code)].copy()
    if target_zip.empty:
        return f"ZIP {zip_code} not found."

    # Spatial join to find segments within the ZIP
    gdf_zip_segments = gpd.sjoin(gdf_census, target_zip[['geometry']], how='inner', predicate='intersects')

    results = []
    # Core algorithm: Iterating through segments to apply temporal masks
    for _, row in gdf_zip_segments.iterrows():
        cnn = str(row['CNN'])
        availability = [1] * 168  # 1 = Open, 0 = Closed (Sweeping)

        # Filter regulations for current segment
        rules = df_sweeping[df_sweeping['CNN'].astype(str) == cnn]

        for _, rule in rules.iterrows():
            day_idx = get_day_index(rule['WeekDay'])
            if day_idx is not None:
                start_h = int(rule['FromHour'])
                end_h = int(rule['ToHour'])
                for h in range(start_h, end_h):
                    hour_idx = day_idx * 24 + h
                    if 0 <= hour_idx < 168:
                        availability[hour_idx] = 0

        entry = {
            'cnn': cnn,
            'street_name': row['ST_NAME'],
            'street_type': row['ST_TYPE'],
            'geometry': row['shape']
        }
        # Expand availability into 168 columns
        for h in range(168):
            entry[f'hour_{h}'] = availability[h]
        results.append(entry)

    if not results:
        return f"No segments found for ZIP {zip_code}."

    # Export to CSV
    df_out = pd.DataFrame(results)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    file_path = os.path.join(output_dir, f'parking_availability_{zip_code}.csv')
    df_out.to_csv(file_path, index=False)
    return f"Processed ZIP {zip_code}: {len(df_out)} segments."


def main(zip_codes_to_process):
    """Entry point for batch processing."""
    # Data Loading
    df_zips = pd.read_csv('data/San_Francisco_ZIP_Codes_20260310.csv')
    df_zips['geometry'] = df_zips['geometry'].apply(wkt.loads)
    gdf_zips = gpd.GeoDataFrame(df_zips, geometry='geometry', crs="EPSG:4326")

    df_census = pd.read_csv('data/On-Street_Parking_Census.csv')
    df_census['geometry'] = df_census['shape'].apply(wkt.loads)
    gdf_census = gpd.GeoDataFrame(df_census, geometry='geometry', crs="EPSG:4326")

    df_sweeping = pd.read_csv('data/Street_Sweeping_Schedule_20260420.csv')

    # Batch Execution
    for zip_code in zip_codes_to_process:
        status = generate_availability_csv(zip_code, gdf_zips, gdf_census, df_sweeping)
        print(status)


if __name__ == "__main__":
    target_zips = ['94133', '94104', '94112', '94110', '94105', '94109']
    main(target_zips)