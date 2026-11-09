# -*- coding: utf-8 -*-
"""贵州省数据准备与前置环境校验脚本
1. 校验贵州省省界及 9 个分析单元（6 个地级市 + 3 个自治州）的 DataV GeoJSON 边界数据
2. 从区县夜光数据表中提取贵州省（520000）1986—2024年夜光时序数据，生成 data/guizhou_nightlight_clean.csv
3. 校验并确认贵州省 300m DEM 高程栅格缓存 (520000_z9.npz)
"""
import os
import sys
import json
import urllib.request
import pandas as pd
import numpy as np
import geopandas as gpd

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册"
DATA_DIR = os.path.join(BASE_DIR, "data")
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")
DEM_DIR = os.path.join(DATA_DIR, "dem", "province")

os.makedirs(DATAV_DIR, exist_ok=True)

GUIZHOU_CITIES = [
    ("贵阳市", "520100"),
    ("六盘水市", "520200"),
    ("遵义市", "520300"),
    ("安顺市", "520400"),
    ("毕节市", "520500"),
    ("铜仁市", "520600"),
    ("黔西南布依族苗族自治州", "522300"),
    ("黔东南苗族侗族自治州", "522600"),
    ("黔南布依族苗族自治州", "522700"),
]

def download_json(url, target_path):
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = resp.read()
        with open(target_path, 'wb') as f:
            f.write(data)

def prepare_guizhou():
    print("=== 1. CHECKING & DOWNLOADING GUIZHOU BOUNDARIES ===")
    prov_file = os.path.join(DATAV_DIR, "520000_full.json")
    if not os.path.exists(prov_file):
        url = "https://geo.datav.aliyun.com/areas_v3/bound/520000_full.json"
        print(f"Downloading provincial boundary: {url} -> {prov_file}")
        try:
            download_json(url, prov_file)
            print("  ✓ Downloaded 520000_full.json")
        except Exception as e:
            print(f"  ✕ Error downloading provincial boundary: {e}")
    else:
        print(f"  ✓ Provincial boundary 520000_full.json exists ({os.path.getsize(prov_file)//1024} KB)")

    prov_gdf = None
    try:
        prov_gdf = gpd.read_file(prov_file)
    except Exception as e:
        print(f"  Warning: could not parse 520000_full.json with gpd: {e}")

    for name, code in GUIZHOU_CITIES:
        target_path = os.path.join(DATAV_DIR, f"{code}_full.json")
        target_single = os.path.join(DATAV_DIR, f"{code}.json")
        if not os.path.exists(target_path) and not os.path.exists(target_single):
            url = f"https://geo.datav.aliyun.com/areas_v3/bound/{code}_full.json"
            print(f"Downloading {name} ({code}): {url}")
            downloaded = False
            try:
                download_json(url, target_path)
                print(f"  ✓ Downloaded {name} ({code}_full.json) {os.path.getsize(target_path)//1024} KB")
                downloaded = True
            except Exception as e:
                url_single = f"https://geo.datav.aliyun.com/areas_v3/bound/{code}.json"
                try:
                    download_json(url_single, target_single)
                    print(f"  ✓ Downloaded {name} ({code}.json as fallback) {os.path.getsize(target_single)//1024} KB")
                    downloaded = True
                except Exception as e2:
                    print(f"  ✕ Failed {name} ({code}): {e2}")

            if not downloaded and prov_gdf is not None:
                match = prov_gdf[prov_gdf['adcode'].astype(str) == str(code)]
                if not match.empty:
                    match.to_file(target_single, driver='GeoJSON')
                    print(f"  ✓ Extracted {name} ({code}) from 520000_full.json")
        else:
            p = target_path if os.path.exists(target_path) else target_single
            print(f"  ✓ {name} ({code}) exists ({os.path.getsize(p)//1024} KB)")

    print("\n=== 2. EXTRACTING GUIZHOU NIGHTLIGHT DATA (1986-2024) ===")
    nl_excel = os.path.join(BASE_DIR, "中国省市数据", "夜间灯光数据-省、市、县（1986-2024年）", "夜间灯光数据-区县（1986-2024年）.xlsx")
    out_csv = os.path.join(DATA_DIR, "guizhou_nightlight_clean.csv")

    if os.path.exists(out_csv):
        print(f"  ✓ Guizhou cleaned nightlight data already exists at {out_csv} ({os.path.getsize(out_csv)//1024} KB)")
    else:
        print(f"  Reading nightlight data from {nl_excel}...")
        df_all = pd.read_excel(nl_excel)
        cols = ['year', 'prov_name', 'city_name', 'district_name', 'prov_code', 'city_code', 'district_code', 'sum', 'mean', 'min', 'max', 'std', 'count', 'extra']
        df_all.columns = cols[:len(df_all.columns)]
        df_gz = df_all[df_all['prov_code'].astype(str).str.startswith("52") | df_all['prov_name'].astype(str).str.contains('贵州')].copy()
        df_gz.to_csv(out_csv, index=False, encoding='utf-8')
        print(f"  ✓ Wrote {len(df_gz)} rows to {out_csv}")

    print("\n=== 3. VERIFYING GUIZHOU DEM ===")
    dem_file = os.path.join(DEM_DIR, "520000_z9.npz")
    if os.path.exists(dem_file):
        d = np.load(dem_file)
        print(f"  ✓ DEM 520000_z9.npz verified: shape {d['dem'].shape}, res={d['res']}m, elev range [{np.nanmin(d['dem']):.1f}, {np.nanmax(d['dem']):.1f}]")
    else:
        print(f"  ✕ DEM {dem_file} NOT found!")

    print("\n=== GUIZHOU DATA PREPARATION COMPLETE ===")

if __name__ == "__main__":
    prepare_guizhou()
