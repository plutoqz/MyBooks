# -*- coding: utf-8 -*-
"""下载并解压 Geofabrik 天津全要素 OSM Shapefile 数据集
包含：gis_osm_roads_free_1.shp, gis_osm_waterways_free_1.shp, gis_osm_railways_free_1.shp 等
"""
import os
import urllib.request
import zipfile

DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
OUT_DIR = os.path.join(DATA_DIR, "transport", "tianjin")
os.makedirs(OUT_DIR, exist_ok=True)

ZIP_PATH = os.path.join(OUT_DIR, "tianjin-latest-free.shp.zip")
URL = "https://download.geofabrik.de/asia/china/tianjin-latest-free.shp.zip"

print(f"Downloading {URL} to {ZIP_PATH}...")
req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=120) as resp:
    data = resp.read()
    with open(ZIP_PATH, "wb") as f:
        f.write(data)
print(f"Downloaded: {len(data) / 1024 / 1024:.2f} MB")

print("Extracting files...")
with zipfile.ZipFile(ZIP_PATH, "r") as z:
    z.extractall(OUT_DIR)
print(f"Extracted to {OUT_DIR}")
print("Contents:", os.listdir(OUT_DIR))
