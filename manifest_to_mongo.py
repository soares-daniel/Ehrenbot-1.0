# Source: https://gist.github.com/Mijago/e4c51cad141465733ed8b700b7f0ecf0

# python -m pip install pymongo
import json
import os
import sqlite3
import time
import urllib.request
import zipfile

from pymongo.mongo_client import MongoClient

from settings import MONGODB_HOST, MONGODB_OPTIONS, MONGODB_PASS, MONGODB_USER

# %% Settings
#################

# Language can be: en, fr, es, es-mx, de, it, ja, pt-br, ru, pl, ko, zh-cht, zh-chs
MANIFEST_LANGUAGE = "en"

# Code.
# I recommend not to change anything below this line
#################

BUNGIE_BASE = "https://bungie.net/"
BUNGIE_API_BASE = "https://bungie.net/Platform/"

# %% Step1: Find the correct manifest to download
manifestPaths = json.loads(urllib.request.urlopen(BUNGIE_API_BASE + "/Destiny2/Manifest/").read())["Response"]
manifestPath = manifestPaths["mobileWorldContentPaths"][MANIFEST_LANGUAGE]
print("Selected manifest url:", manifestPath)
# %% Step 2, download and unzip the manifest
manifest_name = manifestPath.split("/")[-1]
if os.path.isfile(f"./tmp/{manifest_name}"):
    print("Manifest already downloaded")
else:
    if not os.path.exists("./tmp"):
        os.mkdir("./tmp")

    zipped_manifest = "./tmp/manifest.zip"
    with open(zipped_manifest, "wb") as manifestFile:
        manifestFile.write(urllib.request.urlopen(BUNGIE_BASE + manifestPath).read())
    print("Successfully downloaded the manifest into '" + zipped_manifest + "'")

    # %%
    with zipfile.ZipFile(zipped_manifest, 'r') as zip_ref:
        zip_ref.extractall("./tmp/")
    print("Successfully unzipped the manifest")

    # %% Step 3: Open the SQLite connection

    con = sqlite3.connect("./tmp/" + os.path.basename(manifestPath))
    cur = con.cursor()

    sql_query_selectAllTables = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
    cur.execute(sql_query_selectAllTables)

    manifestTables = [t[0] for t in cur.fetchall() if t[0].endswith("Definition")]

    # %% Step 4: Import!
    # mongodb://[username:password@]host1[:port1][,...hostN[:portN]][/[defaultauthdb][?options]]
    MONGODB_URL = "mongodb+srv://{}:{}@{}/?{}".format(MONGODB_USER,
                                                            MONGODB_PASS,
                                                            MONGODB_HOST,
                                                            MONGODB_OPTIONS)

    client = MongoClient(MONGODB_URL)

    db = client.get_database("d2manifest_" + MANIFEST_LANGUAGE)
    print("Starting import of manifest...")
    start_time = time.monotonic()

    for tableToFill in manifestTables:
        tableName = tableToFill
        print("Start with " + tableName)
        collection = db.get_collection(tableName)
        collection.drop()

        sql_query_selectJson = "select json from " + tableToFill + ";"
        cur.execute(sql_query_selectJson)
        jsonContent = [json.loads(j[0]) for j in cur.fetchall()]
        if len(jsonContent) == 0:
            print("#### WARNING: no content found. Ignoring ####")
        else:
            collection.insert_many(jsonContent)
            print("Done with " + tableName)


    con.close()
    client.close()
    taken_time = time.monotonic() - start_time
    print(f"DONE! Took {taken_time} seconds")
