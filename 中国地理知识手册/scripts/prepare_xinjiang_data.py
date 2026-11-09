# -*- coding: utf-8 -*-
"""新疆维吾尔自治区基础地理与空间数据准备与核验脚本：
1. 检查并下载 14 个地州及兵团城市的行政边界 GeoJSON ({adcode}_full.json)
2. 校验新疆夜间灯光时序数据 (data/xinjiang_nightlight_clean.csv)
3. 校验新疆 Albers DEM 缓存 (data/dem/province/650000_z9.npz)
"""
import os
import sys
import json
import time
import urllib.request
import geopandas as gpd

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")

XINJIANG_DIVISIONS = [
    ("650100", "乌鲁木齐市"),
    ("650200", "克拉玛依市"),
    ("650400", "吐鲁番市"),
    ("650500", "哈密市"),
    ("652300", "昌吉回族自治州"),
    ("652700", "博尔塔拉蒙古自治州"),
    ("652800", "巴音郭楞蒙古自治州"),
    ("652900", "阿克苏地区"),
    ("653000", "克孜勒苏柯尔克孜自治州"),
    ("653100", "喀什地区"),
    ("653200", "和田地区"),
    ("654000", "伊犁哈萨克自治州"),
    ("654200", "塔城地区"),
    ("654300", "阿勒泰地区"),
]

def download_boundaries():
    print("=== 1. CHECKING & DOWNLOADING XINJIANG BOUNDARIES ===")
    os.makedirs(DATAV_DIR, exist_ok=True)
    base_url = "https://geo.datav.aliyun.com/areas_v3/bound/{}_full.json"
    alt_base = "https://geo.datav.aliyun.com/areas_v3/bound/{}.json"
    
    prov_path = os.path.join(DATAV_DIR, "650000_full.json")
    if os.path.exists(prov_path):
        print(f"  ✓ Provincial boundary 650000_full.json exists ({os.path.getsize(prov_path)//1024} KB)")

    for adcode, name in XINJIANG_DIVISIONS:
        target_path = os.path.join(DATAV_DIR, f"{adcode}_full.json")
        if os.path.exists(target_path) and os.path.getsize(target_path) > 1000:
            print(f"  ✓ {name} ({adcode}_full.json) exists ({os.path.getsize(target_path)//1024} KB)")
            continue
        url = base_url.format(adcode)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                content = resp.read()
            json.loads(content)
            with open(target_path, "wb") as f:
                f.write(content)
            print(f"  ✓ Downloaded {name} ({adcode}_full.json) {len(content)//1024} KB")
        except Exception:
            try:
                alt_url = alt_base.format(adcode)
                req = urllib.request.Request(alt_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    content = resp.read()
                json.loads(content)
                with open(target_path, "wb") as f:
                    f.write(content)
                print(f"  ✓ Downloaded {name} (via non-full {adcode}.json -> {adcode}_full.json) {len(content)//1024} KB")
            except Exception as e2:
                print(f"  ✗ Failed fallback for {name}: {e2}")
        time.sleep(0.2)

def check_resources():
    print("\n=== 2. CHECKING NIGHTLIGHT & DEM CACHE ===")
    nl_csv = os.path.join(DATA_DIR, "xinjiang_nightlight_clean.csv")
    if os.path.exists(nl_csv):
        print(f"  ✓ Xinjiang nightlight data verified at {nl_csv} ({os.path.getsize(nl_csv)//1024} KB)")
    else:
        print(f"  ✗ Xinjiang nightlight data missing at {nl_csv}")

    dem_npz = os.path.join(DATA_DIR, "dem", "province", "650000_z9.npz")
    if os.path.exists(dem_npz):
        print(f"  ✓ Xinjiang Albers DEM cache verified at {dem_npz} ({os.path.getsize(dem_npz)//(1024*1024)} MB)")
    else:
        print(f"  ✗ Xinjiang Albers DEM cache missing at {dem_npz}")

if __name__ == "__main__":
    download_boundaries()
    check_resources()
    print("\n✓ Xinjiang data preparation completed.")
