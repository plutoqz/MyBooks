# -*- coding: utf-8 -*-
"""广东省数据准备与前置环境校验脚本
1. 校验广东省省界及 21 个分析单元（地级市）的 DataV GeoJSON 边界数据
2. 从地级市夜光数据表中提取广东省（440000）1986—2024年全部 21 个地级市夜光时序数据，生成 data/guangdong_nightlight_clean.csv
3. 校验并确认广东省 300m DEM 高程栅格缓存 (440000_z9.npz)
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

GUANGDONG_CITIES = [
    ("广州市", "440100"),
    ("韶关市", "440200"),
    ("深圳市", "440300"),
    ("珠海市", "440400"),
    ("汕头市", "440500"),
    ("佛山市", "440600"),
    ("江门市", "440700"),
    ("湛江市", "440800"),
    ("茂名市", "440900"),
    ("肇庆市", "441200"),
    ("惠州市", "441300"),
    ("梅州市", "441400"),
    ("汕尾市", "441500"),
    ("河源市", "441600"),
    ("阳江市", "441700"),
    ("清远市", "441800"),
    ("东莞市", "441900"),
    ("中山市", "442000"),
    ("潮州市", "445100"),
    ("揭阳市", "445200"),
    ("云浮市", "445300"),
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

def prepare_guangdong():
    print("=== 1. CHECKING & DOWNLOADING GUANGDONG BOUNDARIES ===")
    prov_file = os.path.join(DATAV_DIR, "440000_full.json")
    if not os.path.exists(prov_file):
        url = "https://geo.datav.aliyun.com/areas_v3/bound/440000_full.json"
        print(f"Downloading provincial boundary: {url} -> {prov_file}")
        try:
            download_json(url, prov_file)
            print("  ✓ Downloaded 440000_full.json")
        except Exception as e:
            print(f"  ✕ Error downloading provincial boundary: {e}")
    else:
        print(f"  ✓ Provincial boundary 440000_full.json exists ({os.path.getsize(prov_file)//1024} KB)")

    for name, code in GUANGDONG_CITIES:
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

    print("\n=== 2. EXTRACTING GUANGDONG NIGHTLIGHT DATA (1986-2024) ===")
    nl_excel = os.path.join(BASE_DIR, "中国省市数据", "夜间灯光数据-省、市、县（1986-2024年）", "夜间灯光数据-地级市（1986-2024年）.xlsx")
    out_csv = os.path.join(DATA_DIR, "guangdong_nightlight_clean.csv")

    print(f"  Reading nightlight data from {nl_excel}...")
    df_all = pd.read_excel(nl_excel)
    cols = ['year', 'prov_name', 'city_name', 'prov_code', 'city_code', 'area_name', 'region_type', 'sum', 'mean', 'min', 'max', 'std', 'count', 'extra']
    df_all.columns = cols[:len(df_all.columns)]
    # 筛选广东省 (440000)
    df_gd = df_all[df_all['prov_code'].astype(str).str.startswith("44") | df_all['prov_name'].astype(str).str.contains('广东')].copy()
    df_gd.to_csv(out_csv, index=False, encoding='utf-8')
    print(f"  ✓ Successfully extracted Guangdong nightlight data: {len(df_gd)} records across {df_gd['city_code'].nunique()} cities -> {out_csv}")

    print("\n=== 3. CHECKING GUANGDONG DEM DATA ===")
    dem_path = os.path.join(DEM_DIR, "440000_z9.npz")
    if os.path.exists(dem_path):
        data = np.load(dem_path)
        print(f"  ✓ Guangdong DEM exists at {dem_path} ({os.path.getsize(dem_path)/(1024*1024):.2f} MB)")
        print(f"    - Resolution: {data['res']} m")
        print(f"    - Grid Shape: {data['dem'].shape}")
        print(f"    - Elev Min: {np.nanmin(data['dem']):.1f} m, Elev Max: {np.nanmax(data['dem']):.1f} m")
    else:
        print(f"  ✕ Guangdong DEM not found at {dem_path}!")

    print("\n=== GUANGDONG PREPARATION COMPLETE ===")

if __name__ == "__main__":
    prepare_guangdong()
