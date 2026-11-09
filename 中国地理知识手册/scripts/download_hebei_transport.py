# -*- coding: utf-8 -*-
"""下载并解压 Geofabrik 河北全要素 OSM Shapefile 数据集
包含：gis_osm_roads_free_1.shp, gis_osm_waterways_free_1.shp, gis_osm_railways_free_1.shp, gis_osm_water_a_free_1.shp 等
"""
import os
import urllib.request
import zipfile

DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
OUT_DIR = os.path.join(DATA_DIR, "transport", "hebei")
os.makedirs(OUT_DIR, exist_ok=True)

ZIP_PATH = os.path.join(OUT_DIR, "hebei-latest-free.shp.zip")
URL = "https://download.geofabrik.de/asia/china/hebei-latest-free.shp.zip"

target_shp = os.path.join(OUT_DIR, "gis_osm_roads_free_1.shp")
if os.path.exists(target_shp):
    print(f"Hebei OSM shapefiles already exist at {OUT_DIR}.")
    exit(0)

if not os.path.exists(ZIP_PATH):
    print(f"Downloading {URL} to {ZIP_PATH}...")
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        with open(ZIP_PATH, "wb") as f:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total > 0 and downloaded % (10 * 1024 * 1024) < 1024 * 1024:
                    print(f"Downloaded {downloaded / 1024 / 1024:.1f} / {total / 1024 / 1024:.1f} MB ({downloaded / total * 100:.1f}%)")
    print(f"Downloaded: {os.path.getsize(ZIP_PATH) / 1024 / 1024:.2f} MB")
else:
    print(f"ZIP already exists: {os.path.getsize(ZIP_PATH) / 1024 / 1024:.2f} MB")

print("Extracting files...")
with zipfile.ZipFile(ZIP_PATH, "r") as z:
    z.extractall(OUT_DIR)
print(f"Extracted to {OUT_DIR}")
print("Contents:", [f for f in os.listdir(OUT_DIR) if f.endswith(".shp")])
