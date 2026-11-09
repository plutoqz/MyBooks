# -*- coding: utf-8 -*-
"""广西壮族自治区数据准备与前置环境校验脚本
1. 校验广西区界及 14 个分析单元（地级市）的 DataV GeoJSON 边界数据
2. 从地级市夜光数据表中提取广西（450000）1986—2024年全部 14 个地级市夜光时序数据，生成 data/guangxi_nightlight_clean.csv
3. 校验并确认广西 300m DEM 高程栅格缓存 (450000_z9.npz)
"""
import os
import sys
import json
import urllib.request
import pandas as pd
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册"
DATA_DIR = os.path.join(BASE_DIR, "data")
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")
DEM_DIR = os.path.join(DATA_DIR, "dem", "province")

os.makedirs(DATAV_DIR, exist_ok=True)

GUANGXI_CITIES = [
    ("南宁市", "450100"),
    ("柳州市", "450200"),
    ("桂林市", "450300"),
    ("梧州市", "450400"),
    ("北海市", "450500"),
    ("防城港市", "450600"),
    ("钦州市", "450700"),
    ("贵港市", "450800"),
    ("玉林市", "450900"),
    ("百色市", "451000"),
    ("贺州市", "451100"),
    ("河池市", "451200"),
    ("来宾市", "451300"),
    ("崇左市", "451400"),
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

def prepare_guangxi():
    print("=== 1. CHECKING & DOWNLOADING GUANGXI BOUNDARIES ===")
    prov_file = os.path.join(DATAV_DIR, "450000_full.json")
    if not os.path.exists(prov_file):
        url = "https://geo.datav.aliyun.com/areas_v3/bound/450000_full.json"
        print(f"Downloading provincial boundary: {url} -> {prov_file}")
        try:
            download_json(url, prov_file)
            print("  ✓ Downloaded 450000_full.json")
        except Exception as e:
            print(f"  ✕ Error downloading provincial boundary: {e}")
    else:
        print(f"  ✓ Provincial boundary 450000_full.json exists ({os.path.getsize(prov_file)//1024} KB)")

    for name, code in GUANGXI_CITIES:
        target_path = os.path.join(DATAV_DIR, f"{code}_full.json")
        if not os.path.exists(target_path):
            url = f"https://geo.datav.aliyun.com/areas_v3/bound/{code}_full.json"
            print(f"Downloading {name} ({code}): {url}")
            try:
                download_json(url, target_path)
                print(f"  ✓ Downloaded {name} ({code}_full.json) {os.path.getsize(target_path)//1024} KB")
            except Exception as e:
                # 尝试下载单一轮廓版
                url_single = f"https://geo.datav.aliyun.com/areas_v3/bound/{code}.json"
                try:
                    download_json(url_single, target_path)
                    print(f"  ✓ Downloaded {name} ({code}.json as fallback) {os.path.getsize(target_path)//1024} KB")
                except Exception as e2:
                    print(f"  ✕ Failed {name} ({code}): {e2}")
        else:
            print(f"  ✓ {name} ({code}_full.json) exists ({os.path.getsize(target_path)//1024} KB)")

    print("\n=== 2. EXTRACTING GUANGXI NIGHTLIGHT DATA (1986-2024) ===")
    nl_excel = os.path.join(BASE_DIR, "中国省市数据", "夜间灯光数据-省、市、县（1986-2024年）", "夜间灯光数据-地级市（1986-2024年）.xlsx")
    out_csv = os.path.join(DATA_DIR, "guangxi_nightlight_clean.csv")

    print(f"  Reading nightlight data from {nl_excel}...")
    df_all = pd.read_excel(nl_excel)
    cols = ['year', 'prov_name', 'city_name', 'prov_code', 'city_code', 'area_name', 'region_type', 'sum', 'mean', 'min', 'max', 'std', 'count', 'extra']
    df_all.columns = cols[:len(df_all.columns)]
    # 筛选广西 (450000)
    df_gx = df_all[df_all['prov_code'].astype(str).str.startswith("45") | df_all['prov_name'].astype(str).str.contains('广西')].copy()
    
    print(f"  Found {len(df_gx)} rows for Guangxi.")
    print(f"  Unique cities ({len(df_gx['city_code'].unique())}): {list(df_gx['city_name'].unique())}")
    print(f"  Years range: {df_gx['year'].min()} - {df_gx['year'].max()}")
    
    df_gx.to_csv(out_csv, index=False, encoding='utf-8')
    print(f"  ✓ Saved clean Guangxi nightlight data to: {out_csv}")

    print("\n=== 3. CHECKING GUANGXI DEM DATA ===")
    dem_path = os.path.join(DEM_DIR, "450000_z9.npz")
    if os.path.exists(dem_path):
        size_mb = os.path.getsize(dem_path) / 1024 / 1024
        print(f"  ✓ DEM raster {dem_path} exists ({size_mb:.2f} MB)")
        npz = np.load(dem_path)
        dem = npz['dem']
        print(f"    Shape: {dem.shape}, Min: {np.nanmin(dem):.1f}m, Max: {np.nanmax(dem):.1f}m, Mean: {np.nanmean(dem):.1f}m")
    else:
        print(f"  ✕ DEM raster {dem_path} NOT FOUND! Need download or synthesis.")

if __name__ == "__main__":
    prepare_guangxi()
