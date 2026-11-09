# -*- coding: utf-8 -*-
"""陕西省数据准备与前置环境校验脚本
1. 校验陕西省省界及 10 个分析单元（10 个地级市）的 DataV GeoJSON 边界数据
2. 从区县夜光数据表中提取陕西省（610000）1986—2024年夜光时序数据，生成 data/shaanxi_nightlight_clean.csv
3. 校验并确认陕西省 300m DEM 高程栅格缓存 (610000_z9.npz)
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

SHAANXI_CITIES = [
    ("西安市", "610100"),
    ("铜川市", "610200"),
    ("宝鸡市", "610300"),
    ("咸阳市", "610400"),
    ("渭南市", "610500"),
    ("延安市", "610600"),
    ("汉中市", "610700"),
    ("榆林市", "610800"),
    ("安康市", "610900"),
    ("商洛市", "611000"),
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

def prepare_shaanxi():
    print("=== 1. CHECKING & DOWNLOADING SHAANXI BOUNDARIES ===")
    prov_file = os.path.join(DATAV_DIR, "610000_full.json")
    if not os.path.exists(prov_file):
        url = "https://geo.datav.aliyun.com/areas_v3/bound/610000_full.json"
        print(f"Downloading provincial boundary: {url} -> {prov_file}")
        try:
            download_json(url, prov_file)
            print("  ✓ Downloaded 610000_full.json")
        except Exception as e:
            print(f"  ✕ Error downloading provincial boundary: {e}")
    else:
        print(f"  ✓ Provincial boundary 610000_full.json exists ({os.path.getsize(prov_file)//1024} KB)")

    prov_gdf = None
    try:
        prov_gdf = gpd.read_file(prov_file)
    except Exception as e:
        print(f"  Warning: could not parse 610000_full.json with gpd: {e}")

    for name, code in SHAANXI_CITIES:
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
                    print(f"  ✓ Extracted {name} ({code}) from 610000_full.json")
        else:
            p = target_path if os.path.exists(target_path) else target_single
            print(f"  ✓ {name} ({code}) exists ({os.path.getsize(p)//1024} KB)")

    print("\n=== 2. EXTRACTING SHAANXI NIGHTLIGHT DATA (1986-2024) ===")
    nl_excel = os.path.join(BASE_DIR, "中国省市数据", "夜间灯光数据-省、市、县（1986-2024年）", "夜间灯光数据-区县（1986-2024年）.xlsx")
    out_csv = os.path.join(DATA_DIR, "shaanxi_nightlight_clean.csv")

    if os.path.exists(out_csv):
        print(f"  ✓ Shaanxi cleaned nightlight data already exists at {out_csv} ({os.path.getsize(out_csv)//1024} KB)")
    else:
        print(f"  Reading nightlight data from {nl_excel}...")
        df_all = pd.read_excel(nl_excel)
        cols = ['year', 'prov_name', 'city_name', 'district_name', 'prov_code', 'city_code', 'district_code', 'sum', 'mean', 'min', 'max', 'std', 'count', 'extra']
        df_all.columns = cols[:len(df_all.columns)]
        df_sn = df_all[df_all['prov_code'].astype(str).str.startswith("61") | df_all['prov_name'].astype(str).str.contains('陕西')].copy()
        df_sn.to_csv(out_csv, index=False, encoding='utf-8')
        print(f"  ✓ Wrote {len(df_sn)} rows to {out_csv}")

    print("\n=== 3. VERIFYING SHAANXI DEM ===")
    dem_file = os.path.join(DEM_DIR, "610000_z9.npz")
    if os.path.exists(dem_file):
        d = np.load(dem_file)
        print(f"  ✓ DEM 610000_z9.npz verified: shape {d['dem'].shape}, res={d['res']}m, elev range [{np.nanmin(d['dem']):.1f}, {np.nanmax(d['dem']):.1f}]")
    else:
        print(f"  ✕ DEM {dem_file} NOT found!")

    print("\n=== SHAANXI DATA PREPARATION COMPLETE ===")

if __name__ == "__main__":
    prepare_shaanxi()
