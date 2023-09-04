import subprocess
import os
import shutil

def import_data_to_local(databases, path_to_exported_data):
    for db in databases:
        try:
            db_path = os.path.join(path_to_exported_data, db)
            auth_args = [
                "--username", "sedam",
                "--password", "SoaDa.660.mongodb",
                "--authenticationDatabase", "admin"
            ]
            subprocess.run(["mongorestore", *auth_args, db_path])
            print(f"Data for database {db} imported successfully")
        except Exception as ex:
            print(f"An error occurred during import of {db}: {ex}")

if __name__ == "__main__":
    # Name of your local database
    databases_to_import = ["d2manifest_en", "ehrenbot", "test"]

    # Path to the exported data
    OUTPUT_DIR = "mongodb_exported_data"

    # Import data into the local MongoDB instance
    import_data_to_local(databases_to_import, OUTPUT_DIR)

    # Optional: Remove the exported data directory
    shutil.rmtree(OUTPUT_DIR)
