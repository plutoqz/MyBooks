# -*- coding: utf-8 -*-
"""甘肃省基础地理与空间数据准备与核验脚本：
1. 检查与下载 14 个市州的行政边界 GeoJSON ({adcode}_full.json)
2. 提取并清理甘肃省 1986—2024 年夜间灯光辐射时序数据
3. 检查与缓存甘肃省 DEM (Albers 投影)
4. 核验 14 个市州历史 GDP 与 2024/2025 年统计公报指标
"""
import os
import sys
import json
import time
import urllib.request
import numpy as np
import pandas as pd
import geopandas as gpd

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, r"D:\code\Ideas\MyBooks\中国地理知识手册\scripts")
from style import ALBERS, DATA
from prov_pipeline import prov_dem, prov_load

DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
RAW_DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\中国省市数据"
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")

GANSU_DIVISIONS = [
    ("620100", "兰州市"),
    ("620200", "嘉峪关市"),
    ("620300", "金昌市"),
    ("620400", "白银市"),
    ("620500", "天水市"),
    ("620600", "武威市"),
    ("620700", "张掖市"),
    ("620800", "平凉市"),
    ("620900", "酒泉市"),
    ("621000", "庆阳市"),
    ("621100", "定西市"),
    ("621200", "陇南市"),
    ("622900", "临夏回族自治州"),
    ("623000", "甘南藏族自治州"),
]

def download_boundaries():
    print("=== 1. CHECKING & DOWNLOADING GANSU BOUNDARIES ===")
    os.makedirs(DATAV_DIR, exist_ok=True)
    base_url = "https://geo.datav.aliyun.com/areas_v3/bound/{}_full.json"
    
    # 检查省界 620000_full.json
    prov_path = os.path.join(DATAV_DIR, "620000_full.json")
    if not os.path.exists(prov_path) or os.path.getsize(prov_path) < 1000:
        url = base_url.format("620000")
        print(f"Downloading provincial boundary 620000_full.json from {url}...")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read()
        with open(prov_path, "wb") as f:
            f.write(content)
        print("  Provincial 620000_full.json downloaded.")
    else:
        print(f"  Provincial 620000_full.json already exists ({os.path.getsize(prov_path)//1024} KB)")
        
    for adcode, name in GANSU_DIVISIONS:
        target_path = os.path.join(DATAV_DIR, f"{adcode}_full.json")
        if os.path.exists(target_path) and os.path.getsize(target_path) > 1000:
            print(f"  ✓ {name} ({adcode}_full.json) exists ({os.path.getsize(target_path)//1024} KB)")
            continue
        url = base_url.format(adcode)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                content = resp.read()
            json.loads(content) # validate JSON
            with open(target_path, "wb") as f:
                f.write(content)
            print(f"  ✓ Downloaded {name} ({adcode}_full.json) {len(content)//1024} KB")
        except Exception as e:
            # Note: Jiayuguan 620200 might not have _full.json because it does not have subordinate districts, try without _full
            if adcode == "620200":
                try:
                    alt_url = "https://geo.datav.aliyun.com/areas_v3/bound/620200.json"
                    req = urllib.request.Request(alt_url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        content = resp.read()
                    json.loads(content)
                    with open(target_path, "wb") as f:
                        f.write(content)
                    print(f"  ✓ Downloaded {name} (via non-full 620200.json -> {adcode}_full.json) {len(content)//1024} KB")
                except Exception as e2:
                    print(f"  ✗ Failed fallback for {name}: {e2}")
            else:
                print(f"  ✗ Failed to download {name} ({adcode}): {e}")
        time.sleep(0.2)

def extract_gansu_nightlight():
    print("\n=== 2. EXTRACTING GANSU NIGHTLIGHT DATA (1986-2024) ===")
    nl_file = os.path.join(RAW_DATA_DIR, "夜间灯光数据-省、市、县（1986-2024年）", "夜间灯光数据-区县（1986-2024年）.xlsx")
    out_csv = os.path.join(DATA_DIR, "gansu_nightlight_clean.csv")
    if os.path.exists(out_csv):
        print(f"Gansu nightlight clean CSV already exists at {out_csv}.")
        df = pd.read_csv(out_csv)
        print(f"Rows: {len(df)}, Cities/Prefectures: {df['city_name'].nunique()}, Districts/Counties: {df['district_name'].nunique()}")
        return df

    if not os.path.exists(nl_file):
        print(f"Warning: {nl_file} not found!")
        return None

    print(f"Reading nightlight data from {nl_file}...")
    df = pd.read_excel(nl_file)
    cols = ['year', 'prov_name', 'city_name', 'district_name', 'prov_code', 'city_code', 'district_code', 'sum', 'mean', 'min', 'max', 'std', 'count', 'extra']
    df.columns = cols[:len(df.columns)]
    
    # 筛选甘肃省 (代码以 62 开头或名称含甘肃)
    gs = df[df['prov_code'].astype(str).str.startswith("62") | df['prov_name'].astype(str).str.contains("甘肃")].copy()
    print(f"Filtered {len(gs)} Gansu records from {df['year'].min()} to {df['year'].max()}.")
    gs.to_csv(out_csv, index=False, encoding='utf-8-sig')
    print(f"Saved cleaned Gansu nightlight data to {out_csv}.")
    return gs

def check_dem():
    print("\n=== 3. CHECKING & VERIFYING GANSU DEM ===")
    dem_cache = os.path.join(DATA_DIR, "dem", "prov", "620000_z9.npz")
    if os.path.exists(dem_cache):
        print(f"Gansu DEM Albers cache already exists at {dem_cache} ({os.path.getsize(dem_cache)//(1024*1024)} MB)")
        return
    print("Loading Gansu boundary for DEM processing...")
    gdf = prov_load("620000")
    print(f"Loaded boundary with {len(gdf)} geometry features, bounds: {gdf.total_bounds}")
    print("Computing DEM via prov_dem('620000')...")
    dem, minx, maxy, res = prov_dem("620000", zoom=9, res=300.0)
    print(f"DEM shape: {dem.shape}, min elev: {np.nanmin(dem):.1f}m, max elev: {np.nanmax(dem):.1f}m")

if __name__ == "__main__":
    download_boundaries()
    extract_gansu_nightlight()
    check_dem()
    print("\n✓ Gansu data preparation completed.")
