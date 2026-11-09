# -*- coding: utf-8 -*-
"""下载并解压 Geofabrik 内蒙古全要素 OSM Shapefile 数据集
包含：gis_osm_roads_free_1.shp, gis_osm_waterways_free_1.shp, gis_osm_railways_free_1.shp, gis_osm_water_a_free_1.shp 等
"""
import os
import sys
import urllib.request
import zipfile

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
OUT_DIR = os.path.join(DATA_DIR, "transport", "neimenggu")
os.makedirs(OUT_DIR, exist_ok=True)

ZIP_PATH = os.path.join(OUT_DIR, "neimenggu-latest-free.shp.zip")

# 寻找可用的 Geofabrik 文件名
possible_names = ['inner-mongolia', 'nei-mongol', 'neimenggu', 'neimeng']
valid_url = None

for name in possible_names:
    test_url = f"https://download.geofabrik.de/asia/china/{name}-latest-free.shp.zip"
    try:
        req = urllib.request.Request(test_url, method='HEAD', headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as r:
            cl = r.headers.get("Content-Length")
            print(f"Found valid URL: {test_url} ({int(cl)//(1024*1024)} MB)")
            valid_url = test_url
            break
    except Exception as e:
        print(f"Candidate {name} failed: {e}")

if not valid_url:
    print("Could not find Geofabrik URL, checking html list...")
    # Fetch directory listing
    try:
        req = urllib.request.Request("https://download.geofabrik.de/asia/china.html", headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode('utf-8')
            for line in html.split('\n'):
                if 'shp.zip' in line and any(k in line.lower() for k in ['mongol', 'neimeng']):
                    print("Found in HTML:", line.strip())
    except Exception as e:
        print("Failed to fetch china.html:", e)
    sys.exit(1)

target_shp = os.path.join(OUT_DIR, "gis_osm_roads_free_1.shp")
if os.path.exists(target_shp):
    print(f"Inner Mongolia OSM shapefiles already exist at {OUT_DIR}.")
    sys.exit(0)

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
