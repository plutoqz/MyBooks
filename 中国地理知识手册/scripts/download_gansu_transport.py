# -*- coding: utf-8 -*-
"""下载并解压 Geofabrik 甘肃全要素 OSM Shapefile 数据集
包含：gis_osm_roads_free_1.shp, gis_osm_waterways_free_1.shp, gis_osm_railways_free_1.shp 等
"""
import os
import sys
import urllib.request
import zipfile

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
OUT_DIR = os.path.join(DATA_DIR, "transport", "gansu")
os.makedirs(OUT_DIR, exist_ok=True)

target_shp = os.path.join(OUT_DIR, "gis_osm_roads_free_1.shp")
if os.path.exists(target_shp):
    print(f"Gansu OSM shapefiles already exist at {OUT_DIR}.")
    sys.exit(0)

ZIP_PATH = os.path.join(OUT_DIR, "gansu-latest-free.shp.zip")

valid_url = "https://download.geofabrik.de/asia/china/gansu-latest-free.shp.zip"

print(f"Checking URL: {valid_url}...")
try:
    req = urllib.request.Request(valid_url, method='HEAD', headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=10) as r:
        cl = r.headers.get("Content-Length")
        print(f"Found valid URL: {valid_url} ({int(cl)//(1024*1024)} MB)")
except Exception as e:
    print(f"HEAD request failed: {e}")

if not os.path.exists(ZIP_PATH):
    print(f"Downloading {valid_url} to {ZIP_PATH}...")
    req = urllib.request.Request(valid_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=600) as resp:
        with open(ZIP_PATH, "wb") as f:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total > 0 and downloaded % (5 * 1024 * 1024) < 1024 * 1024:
                    print(f"Downloaded {downloaded / 1024 / 1024:.1f} / {total / 1024 / 1024:.1f} MB ({downloaded / total * 100:.1f}%)")
    print(f"Downloaded: {os.path.getsize(ZIP_PATH) / 1024 / 1024:.2f} MB")

print("Extracting ZIP archive...")
with zipfile.ZipFile(ZIP_PATH, 'r') as zf:
    zf.extractall(OUT_DIR)
print(f"Successfully extracted shapefiles to {OUT_DIR}.")
