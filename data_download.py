import os
import requests


def download_data_if_missing(url, target_path):
    """Downloads the dataset from the provided URL if it doesn't exist locally."""
    if os.path.exists(target_path):
        return

    print(f"--- Data Missing: Downloading {os.path.basename(target_path)} ---")
    print(f"Source: {url}")

    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Check for download errors

        with open(target_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Download Complete: {target_path}")
    except Exception as e:
        print(f"Error downloading file: {e}")

if __name__ == "__main__":
    CONFIG = {
        "DATA_DIR": "data",
        "OUTPUT_DIR": "output",
        "TARGET_ZIPS": ['94133', '94112', '94110', '94105', '94109']
    }
    OCC_URL = "https://safitwebapps.blob.core.windows.net/$web/streets/sfpark/SFpark_ParkingSensorData_HourlyOccupancy_20112013.csv"
    OCC_LOCAL_PATH = os.path.join(CONFIG["DATA_DIR"], "SFpark_ParkingSensorData_HourlyOccupancy_20112013.csv")
    download_data_if_missing(OCC_URL, OCC_LOCAL_PATH)