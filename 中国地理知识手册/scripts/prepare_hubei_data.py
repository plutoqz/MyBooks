# -*- coding: utf-8 -*-
"""湖北省数据准备与前置环境校验脚本
1. 校验湖北省省界及 17 个分析单元（12个地级市 + 1个自治州 + 3个省直管市 + 1个林区）的 DataV GeoJSON 边界数据
2. 从区县夜光数据表中提取湖北省（420000）1986—2024年夜光时序数据，生成 data/hubei_nightlight_clean.csv
3. 校验并确认湖北省 300m DEM 高程栅格缓存 (420000_z9.npz)
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

HUBEI_CITIES = [
    ("武汉市", "420100"),
    ("黄石市", "420200"),
    ("十堰市", "420300"),
    ("宜昌市", "420500"),
    ("襄阳市", "420600"),
    ("鄂州市", "420700"),
    ("荆门市", "420800"),
    ("孝感市", "420900"),
    ("荆州市", "421000"),
    ("黄冈市", "421100"),
    ("咸宁市", "421200"),
    ("随州市", "421300"),
    ("恩施土家族苗族自治州", "422800"),
    ("仙桃市", "429004"),
    ("潜江市", "429005"),
    ("天门市", "429006"),
    ("神农架林区", "429021"),
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

def prepare_hubei():
    print("=== 1. CHECKING & DOWNLOADING HUBEI BOUNDARIES ===")
    prov_file = os.path.join(DATAV_DIR, "420000_full.json")
    if not os.path.exists(prov_file):
        url = "https://geo.datav.aliyun.com/areas_v3/bound/420000_full.json"
        print(f"Downloading provincial boundary: {url} -> {prov_file}")
        try:
            download_json(url, prov_file)
            print("  ✓ Downloaded 420000_full.json")
        except Exception as e:
            print(f"  ✕ Error downloading provincial boundary: {e}")
    else:
        print(f"  ✓ Provincial boundary 420000_full.json exists ({os.path.getsize(prov_file)//1024} KB)")

    for name, code in HUBEI_CITIES:
        target_path = os.path.join(DATAV_DIR, f"{code}_full.json")
        if not os.path.exists(target_path):
            url = f"https://geo.datav.aliyun.com/areas_v3/bound/{code}_full.json"
            print(f"Downloading {name} ({code}): {url}")
            try:
                download_json(url, target_path)
                print(f"  ✓ Downloaded {name} ({code}_full.json) {os.path.getsize(target_path)//1024} KB")
            except Exception as e:
                # 县级市或林区可能无 _full 版，尝试下载单一轮廓版
                url_single = f"https://geo.datav.aliyun.com/areas_v3/bound/{code}.json"
                try:
                    download_json(url_single, target_path)
                    print(f"  ✓ Downloaded {name} ({code}.json as fallback) {os.path.getsize(target_path)//1024} KB")
                except Exception as e2:
                    print(f"  ✕ Failed {name} ({code}): {e2}")
        else:
            print(f"  ✓ {name} ({code}_full.json) exists ({os.path.getsize(target_path)//1024} KB)")

    print("\n=== 2. EXTRACTING HUBEI NIGHTLIGHT DATA (1986-2024) ===")
    nl_excel = os.path.join(BASE_DIR, "中国省市数据", "夜间灯光数据-省、市、县（1986-2024年）", "夜间灯光数据-区县（1986-2024年）.xlsx")
    out_csv = os.path.join(DATA_DIR, "hubei_nightlight_clean.csv")

    if os.path.exists(out_csv):
        print(f"  ✓ Hubei cleaned nightlight data already exists at {out_csv} ({os.path.getsize(out_csv)//1024} KB)")
    else:
        print(f"  Reading nightlight data from {nl_excel}...")
        df_all = pd.read_excel(nl_excel)
        cols = ['year', 'prov_name', 'city_name', 'district_name', 'prov_code', 'city_code', 'district_code', 'sum', 'mean', 'min', 'max', 'std', 'count', 'extra']
        df_all.columns = cols[:len(df_all.columns)]
        # 筛选湖北省 (420000)
        df_hb = df_all[df_all['prov_code'].astype(str).str.startswith("42") | df_all['prov_name'].astype(str).str.contains('湖北')].copy()
        df_hb.to_csv(out_csv, index=False, encoding='utf-8')
        print(f"  ✓ Successfully extracted Hubei nightlight data: {len(df_hb)} records -> {out_csv}")

    print("\n=== 3. CHECKING HUBEI DEM DATA ===")
    dem_path = os.path.join(DEM_DIR, "420000_z9.npz")
    if os.path.exists(dem_path):
        data = np.load(dem_path)
        print(f"  ✓ Hubei DEM exists at {dem_path} ({os.path.getsize(dem_path)/(1024*1024):.2f} MB)")
        print(f"    - Resolution: {data['res']} m")
        print(f"    - Grid Shape: {data['dem'].shape}")
        print(f"    - Elev Min: {np.nanmin(data['dem']):.1f} m, Elev Max: {np.nanmax(data['dem']):.1f} m")
    else:
        print(f"  ✕ Hubei DEM not found at {dem_path}!")

    print("\n=== HUBEI PREPARATION COMPLETE ===")

if __name__ == "__main__":
    prepare_hubei()
