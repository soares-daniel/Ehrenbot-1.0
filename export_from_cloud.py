import subprocess
import os
from settings import MONGODB_HOST, MONGODB_OPTIONS, MONGODB_PASS, MONGODB_USER

def export_data_from_cloud(uri, output_directory):
    try:
        subprocess.run(["mongodump", "--uri", uri, "--out", output_directory])
        print(f"Data exported successfully to {output_directory}")
    except Exception as ex:
        print(f"An error occurred during export: {ex}")

if __name__ == "__main__":
    # URI of your MongoDB cloud instance
    CLOUD_URI = f"mongodb+srv://{MONGODB_USER}:{MONGODB_PASS}@{MONGODB_HOST}/?{MONGODB_OPTIONS}"
    # Output directory for exported data
    OUTPUT_DIR = "mongodb_exported_data"

    # Create directory for exported data if it doesn't exist
    if not os.path.exists(OUTPUT_DIR):
        os.mkdir(OUTPUT_DIR)

    # Export data from the cloud
    export_data_from_cloud(CLOUD_URI, OUTPUT_DIR)
