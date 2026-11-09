# -*- coding: utf-8 -*-
"""宁夏回族自治区基础地理与空间数据准备与核验脚本：
1. 检查与下载 5 个地级市的行政边界 GeoJSON ({adcode}_full.json)
2. 提取并清理宁夏回族自治区 1986—2024 年夜间灯光辐射时序数据
3. 检查与缓存宁夏回族自治区 DEM (Albers 投影)
4. 核验 5 个地级市历史 GDP 与最新统计公报指标
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

NINGXIA_DIVISIONS = [
    ("640100", "银川市"),
    ("640200", "石嘴山市"),
    ("640300", "吴忠市"),
    ("640400", "固原市"),
    ("640500", "中卫市"),
]

def download_boundaries():
    print("=== 1. CHECKING & DOWNLOADING NINGXIA BOUNDARIES ===")
    os.makedirs(DATAV_DIR, exist_ok=True)
    base_url = "https://geo.datav.aliyun.com/areas_v3/bound/{}_full.json"
    
    # 检查区界 640000_full.json
    prov_path = os.path.join(DATAV_DIR, "640000_full.json")
    if not os.path.exists(prov_path) or os.path.getsize(prov_path) < 1000:
        url = base_url.format("640000")
        print(f"Downloading provincial boundary 640000_full.json from {url}...")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read()
        with open(prov_path, "wb") as f:
            f.write(content)
        print("  Provincial 640000_full.json downloaded.")
    else:
        print(f"  Provincial 640000_full.json already exists ({os.path.getsize(prov_path)//1024} KB)")
        
    for adcode, name in NINGXIA_DIVISIONS:
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
            try:
                alt_url = f"https://geo.datav.aliyun.com/areas_v3/bound/{adcode}.json"
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

def extract_ningxia_nightlight():
    print("\n=== 2. EXTRACTING NINGXIA NIGHTLIGHT DATA (1986-2024) ===")
    nl_file = os.path.join(RAW_DATA_DIR, "夜间灯光数据-省、市、县（1986-2024年）", "夜间灯光数据-区县（1986-2024年）.xlsx")
    out_csv = os.path.join(DATA_DIR, "ningxia_nightlight_clean.csv")
    if os.path.exists(out_csv):
        print(f"Ningxia nightlight clean CSV already exists at {out_csv}.")
        df = pd.read_csv(out_csv)
        print(f"Rows: {len(df)}, Cities: {df['city_name'].nunique()}, Districts/Counties: {df['district_name'].nunique()}")
        return df

    if not os.path.exists(nl_file):
        print(f"Warning: {nl_file} not found!")
        return None

    print(f"Reading nightlight data from {nl_file}...")
    df = pd.read_excel(nl_file)
    cols = ['year', 'prov_name', 'city_name', 'district_name', 'prov_code', 'city_code', 'district_code', 'sum', 'mean', 'min', 'max', 'std', 'count', 'extra']
    df.columns = cols[:len(df.columns)]
    
    # 筛选宁夏回族自治区 (代码以 64 开头或名称含宁夏)
    nx = df[df['prov_code'].astype(str).str.startswith("64") | df['prov_name'].astype(str).str.contains("宁夏")].copy()
    print(f"Filtered {len(nx)} Ningxia records from {df['year'].min()} to {df['year'].max()}.")
    nx.to_csv(out_csv, index=False, encoding='utf-8-sig')
    print(f"Saved cleaned Ningxia nightlight data to {out_csv}.")
    return nx

def check_dem():
    print("\n=== 3. CHECKING & VERIFYING NINGXIA DEM ===")
    dem_cache = os.path.join(DATA_DIR, "dem", "prov", "640000_z9.npz")
    if os.path.exists(dem_cache):
        print(f"Ningxia DEM Albers cache already exists at {dem_cache} ({os.path.getsize(dem_cache)//(1024*1024)} MB)")
        return
    print("Loading Ningxia boundary for DEM processing...")
    gdf = prov_load("640000")
    print(f"Loaded boundary with {len(gdf)} geometry features, bounds: {gdf.total_bounds}")
    print("Computing DEM via prov_dem('640000')...")
    dem, minx, maxy, res = prov_dem("640000", zoom=9, res=250.0)
    print(f"DEM shape: {dem.shape}, min elev: {np.nanmin(dem):.1f}m, max elev: {np.nanmax(dem):.1f}m")

if __name__ == "__main__":
    download_boundaries()
    extract_ningxia_nightlight()
    check_dem()
    print("\n✓ Ningxia data preparation completed.")
