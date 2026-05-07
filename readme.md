# Dynamic On-street Parking Capacity Estimation and Optimization

This repository contains the source code and analytical framework for the **Dynamic On-street Parking Capacity Estimation and Optimization** project. 

## Overview
This project:
1.  **Phase 1:** Infers static parking capacity using Right-of-Way geometry and physical models.
2.  **Phase 2:** Generates temporal supply & demand curves and applies a **Temporal Shift** strategy to recover the supply reduction due to urban regulation.



## Data Requirements
All raw datasets should be placed in the `data/` directory.

| File Name | Source                                                                                                                                                                                | Description                                                             |
| :--- |:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:------------------------------------------------------------------------|
| `San_Francisco_ZIP_Codes.csv` | [DataSF](https://data.sfgov.org/-/San-Francisco-ZIP-Codes/srq6-hmpi/)                                                                                                                 | ZIP code boundaries for spatial filtering.                              |
| `On-Street_Parking_Census.csv` | [DataSF](https://data.sfgov.org/Transportation/On-Street-Parking-Census/9ivs-nf5y/)                                                                                                   | Official parking census used for validation.             |
| `Street_Sweeping_Schedule.csv` | [DataSF](https://data.sfgov.org/City-Infrastructure/Street-Sweeping-Schedule/yhqp-riqs/)                                                                                              | Municipal sweeping schedules to create temporal supply masks.           |
| `Right_of_Way_Polygons.csv` | [DataSF](https://data.sfgov.org/City-Infrastructure/Right-of-Way-Polygons/a2mg-gwmg/)                                                                                                 | Geometric data for street width and physical capacity inference.        |
| `Parking_Management_Districts.csv` | [DataSF](https://data.sfgov.org/Transportation/Parking-Management-Districts/6vtc-mmhr/)                                                                                               | Spatial mapping to link ZIP codes with demand sensor zones.             |
| `SFpark_ParkingSensorData_HourlyOccupancy_20112013.csv` | [SFPark](https://www.sfmta.com/getting-around/drive-park/demand-responsive-pricing/sfpark-evaluation)([Download](https://safitwebapps.blob.core.windows.net/$web/streets/sfpark/SFpark_ParkingSensorData_HourlyOccupancy_20112013.csv))        | Hourly occupancy rates used for demand profiling. |

---

## Repository Structure

### 1. `capacity_estimation_full.py`
- **Function:** The complete pipeline of the project: static capacity modeling -> dynamic supply modeling -> dynamic supply optimization.
- **Output:** Generates precision validation reports (MAE/Correlation) and supply-demand optimization charts (`.png`) for each target ZIP code.


### 2. `availability_calculation.py`
- **Function:** A lightweight version for calculating parking availability of each road segment. (Scalable to any postal zones)
- **Output:** Generates `.csv` files containing 168-hour availability masks (1 for open, 0 for restricted) for every street segment.

### 3. `data_download.py`
- **Function:** A utility script to download SFPark-Parking Sensor Data (>1GB) and save in the `data/` directory.


## Acknowledgement

This is a course project for UC Berkeley's CE250N/CRP217 (Transportation Policy and Planning), in collaboration with the Metropolitan Transportation Commission (MTC).
