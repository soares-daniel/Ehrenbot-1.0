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

def import_data_to_local(databases, path_to_exported_data):
    for db in databases:
        try:
            db_path = os.path.join(path_to_exported_data, db)
            subprocess.run(["mongorestore", "--db", db, db_path])
            print(f"Data for database {db} imported successfully")
        except Exception as ex:
            print(f"An error occurred during import of {db}: {ex}")

if __name__ == "__main__":
    # URI of your MongoDB cloud instance
    CLOUD_URI = f"mongodb+srv://{MONGODB_USER}:{MONGODB_PASS}@{MONGODB_HOST}/?{MONGODB_OPTIONS}"
    # Output directory for exported data
    OUTPUT_DIR = "mongodb_exported_data"

    # Name of your local database
    databases_to_import = ["d2manifst_en", "ehrenbot", "test"]

    # Create directory for exported data if it doesn't exist
    if not os.path.exists(OUTPUT_DIR):
        os.mkdir(OUTPUT_DIR)

    # Step 1: Export data from the cloud
    export_data_from_cloud(CLOUD_URI, OUTPUT_DIR)

    # Note: At this point, manually transfer the data to your local machine if needed

    # Step 2: Import data into the local MongoDB instance
    import_data_to_local(databases_to_import, OUTPUT_DIR)
    # Optional: Remove the exported data directory
    shutil.rmtree(OUTPUT_DIR)
