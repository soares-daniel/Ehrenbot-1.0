import subprocess
import os
import shutil

from settings import MONGODB_HOST, MONGODB_OPTIONS, MONGODB_PASS, MONGODB_USER

def export_data_from_cloud(uri, output_directory):
    try:
        subprocess.run(["mongodump", "--uri", uri, "--out", output_directory])
        print(f"Data exported successfully to {output_directory}")
    except Exception as ex:
        print(f"An error occurred during export: {ex}")

def import_data_to_local(db_name, path_to_exported_data):
    try:
        subprocess.run(["mongorestore", "--db", db_name, path_to_exported_data])
        print("Data imported successfully")
    except Exception as ex:
        print(f"An error occurred during import: {ex}")

if __name__ == "__main__":
    # URI of your MongoDB cloud instance
    CLOUD_URI = f"mongodb+srv://{MONGODB_USER}:{MONGODB_PASS}@{MONGODB_HOST}/?{MONGODB_OPTIONS}"
    # Output directory for exported data
    OUTPUT_DIR = "mongodb_exported_data"

    # Name of your local database
    LOCAL_DB_NAME = "my_local_database"

    # Create directory for exported data if it doesn't exist
    if not os.path.exists(OUTPUT_DIR):
        os.mkdir(OUTPUT_DIR)

    # Step 1: Export data from the cloud
    export_data_from_cloud(CLOUD_URI, OUTPUT_DIR)

    # Note: At this point, manually transfer the data to your local machine if needed

    # Step 2: Import data into the local MongoDB instance
    import_data_to_local(LOCAL_DB_NAME, OUTPUT_DIR)

    # Optional: Remove the exported data directory
    shutil.rmtree(OUTPUT_DIR)
