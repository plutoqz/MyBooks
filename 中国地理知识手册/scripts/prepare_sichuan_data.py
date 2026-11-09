# -*- coding: utf-8 -*-
"""四川省数据准备与前置环境校验脚本
1. 校验四川省省界及 21 个分析单元（18个地级市 + 3个自治州）的 DataV GeoJSON 边界数据
2. 从区县夜光数据表中提取四川省（510000）1986—2024年夜光时序数据，生成 data/sichuan_nightlight_clean.csv
3. 校验并确认四川省 300m DEM 高程栅格缓存 (510000_z9.npz)
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

SICHUAN_CITIES = [
    ("成都市", "510100"),
    ("自贡市", "510300"),
    ("攀枝花市", "510400"),
    ("泸州市", "510500"),
    ("德阳市", "510600"),
    ("绵阳市", "510700"),
    ("广元市", "510800"),
    ("遂宁市", "510900"),
    ("内江市", "511000"),
    ("乐山市", "511100"),
    ("南充市", "511300"),
    ("眉山市", "511400"),
    ("宜宾市", "511500"),
    ("广安市", "511600"),
    ("达州市", "511700"),
    ("雅安市", "511800"),
    ("巴中市", "511900"),
    ("资阳市", "512000"),
    ("阿坝藏族羌族自治州", "513200"),
    ("甘孜藏族自治州", "513300"),
    ("凉山彝族自治州", "513400"),
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

def prepare_sichuan():
    print("=== 1. CHECKING & DOWNLOADING SICHUAN BOUNDARIES ===")
    prov_file = os.path.join(DATAV_DIR, "510000_full.json")
    if not os.path.exists(prov_file):
        url = "https://geo.datav.aliyun.com/areas_v3/bound/510000_full.json"
        print(f"Downloading provincial boundary: {url} -> {prov_file}")
        try:
            download_json(url, prov_file)
            print("  ✓ Downloaded 510000_full.json")
        except Exception as e:
            print(f"  ✕ Error downloading provincial boundary: {e}")
    else:
        print(f"  ✓ Provincial boundary 510000_full.json exists ({os.path.getsize(prov_file)//1024} KB)")

    # 尝试从 510000_full.json 读取备用轮廓
    prov_gdf = None
    try:
        prov_gdf = gpd.read_file(prov_file)
    except Exception as e:
        print(f"  Warning: could not parse 510000_full.json with gpd: {e}")

    for name, code in SICHUAN_CITIES:
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
                # 尝试下载单一轮廓版
                url_single = f"https://geo.datav.aliyun.com/areas_v3/bound/{code}.json"
                try:
                    download_json(url_single, target_single)
                    print(f"  ✓ Downloaded {name} ({code}.json as fallback) {os.path.getsize(target_single)//1024} KB")
                    downloaded = True
                except Exception as e2:
                    print(f"  ✕ Failed {name} ({code}): {e2}")

            if not downloaded and prov_gdf is not None:
                # 从省界提取
                match = prov_gdf[prov_gdf['adcode'].astype(str) == str(code)]
                if not match.empty:
                    match.to_file(target_single, driver='GeoJSON')
                    print(f"  ✓ Extracted {name} ({code}) from 510000_full.json")
        else:
            p = target_path if os.path.exists(target_path) else target_single
            print(f"  ✓ {name} ({code}) exists ({os.path.getsize(p)//1024} KB)")

    print("\n=== 2. EXTRACTING SICHUAN NIGHTLIGHT DATA (1986-2024) ===")
    nl_excel = os.path.join(BASE_DIR, "中国省市数据", "夜间灯光数据-省、市、县（1986-2024年）", "夜间灯光数据-区县（1986-2024年）.xlsx")
    out_csv = os.path.join(DATA_DIR, "sichuan_nightlight_clean.csv")

    if os.path.exists(out_csv):
        print(f"  ✓ Sichuan cleaned nightlight data already exists at {out_csv} ({os.path.getsize(out_csv)//1024} KB)")
    else:
        print(f"  Reading nightlight data from {nl_excel}...")
        df_all = pd.read_excel(nl_excel)
        cols = ['year', 'prov_name', 'city_name', 'district_name', 'prov_code', 'city_code', 'district_code', 'sum', 'mean', 'min', 'max', 'std', 'count', 'extra']
        df_all.columns = cols[:len(df_all.columns)]
        # 筛选四川省 (510000)
        df_sc = df_all[df_all['prov_code'].astype(str).str.startswith("51") | df_all['prov_name'].astype(str).str.contains('四川')].copy()
        df_sc.to_csv(out_csv, index=False, encoding='utf-8')
        print(f"  ✓ Wrote {len(df_sc)} rows to {out_csv}")

    print("\n=== 3. VERIFYING SICHUAN DEM ===")
    dem_file = os.path.join(DEM_DIR, "510000_z9.npz")
    if os.path.exists(dem_file):
        d = np.load(dem_file)
        print(f"  ✓ DEM 510000_z9.npz verified: shape {d['dem'].shape}, res={d['res']}m, elev range [{np.nanmin(d['dem']):.1f}, {np.nanmax(d['dem']):.1f}]")
    else:
        print(f"  ✕ DEM {dem_file} NOT found!")

    print("\n=== SICHUAN DATA PREPARATION COMPLETE ===")

if __name__ == "__main__":
    prepare_sichuan()
