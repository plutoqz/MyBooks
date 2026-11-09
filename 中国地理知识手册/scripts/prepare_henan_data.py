# -*- coding: utf-8 -*-
"""河南省数据准备与前置环境校验脚本
1. 校验河南省省界及 17 个地级市 + 1 个省直辖县级市（济源市）的 DataV GeoJSON 边界数据
2. 从区县夜光数据表中提取河南省（410000）1986—2024年夜光时序数据，生成 data/henan_nightlight_clean.csv
3. 校验并确认河南省 300m DEM 高程栅格缓存 (410000_z9.npz)
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

HENAN_CITIES = [
    ("郑州市", "410100"),
    ("开封市", "410200"),
    ("洛阳市", "410300"),
    ("平顶山市", "410400"),
    ("安阳市", "410500"),
    ("鹤壁市", "410600"),
    ("新乡市", "410700"),
    ("焦作市", "410800"),
    ("濮阳市", "410900"),
    ("许昌市", "411000"),
    ("漯河市", "411100"),
    ("三门峡市", "411200"),
    ("南阳市", "411300"),
    ("商丘市", "411400"),
    ("信阳市", "411500"),
    ("周口市", "411600"),
    ("驻马店市", "411700"),
    ("济源市", "419001"),
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

def prepare_henan():
    print("=== 1. CHECKING & DOWNLOADING HENAN BOUNDARIES ===")
    prov_file = os.path.join(DATAV_DIR, "410000_full.json")
    if not os.path.exists(prov_file):
        url = "https://geo.datav.aliyun.com/areas_v3/bound/410000_full.json"
        print(f"Downloading provincial boundary: {url} -> {prov_file}")
        try:
            download_json(url, prov_file)
            print("  ✓ Downloaded 410000_full.json")
        except Exception as e:
            print(f"  ✕ Error downloading provincial boundary: {e}")
    else:
        print(f"  ✓ Provincial boundary 410000_full.json exists ({os.path.getsize(prov_file)//1024} KB)")

    for name, code in HENAN_CITIES:
        target_path = os.path.join(DATAV_DIR, f"{code}_full.json")
        if not os.path.exists(target_path):
            url = f"https://geo.datav.aliyun.com/areas_v3/bound/{code}_full.json"
            print(f"Downloading {name} ({code}): {url}")
            try:
                download_json(url, target_path)
                print(f"  ✓ Downloaded {name} ({code}_full.json) {os.path.getsize(target_path)//1024} KB")
            except Exception as e:
                # 济源市是省直管县级市，可能需要下载非 _full 版
                url_single = f"https://geo.datav.aliyun.com/areas_v3/bound/{code}.json"
                try:
                    download_json(url_single, target_path)
                    print(f"  ✓ Downloaded {name} ({code}.json as fallback) {os.path.getsize(target_path)//1024} KB")
                except Exception as e2:
                    print(f"  ✕ Failed {name} ({code}): {e2}")
        else:
            print(f"  ✓ {name} ({code}_full.json) exists ({os.path.getsize(target_path)//1024} KB)")

    print("\n=== 2. EXTRACTING HENAN NIGHTLIGHT DATA (1986-2024) ===")
    nl_excel = os.path.join(BASE_DIR, "中国省市数据", "夜间灯光数据-省、市、县（1986-2024年）", "夜间灯光数据-区县（1986-2024年）.xlsx")
    out_csv = os.path.join(DATA_DIR, "henan_nightlight_clean.csv")

    if os.path.exists(out_csv):
        print(f"  ✓ Henan cleaned nightlight data already exists at {out_csv} ({os.path.getsize(out_csv)//1024} KB)")
    else:
        print(f"  Reading nightlight data from {nl_excel}...")
        df_all = pd.read_excel(nl_excel)
        cols = ['year', 'prov_name', 'city_name', 'district_name', 'prov_code', 'city_code', 'district_code', 'sum', 'mean', 'min', 'max', 'std', 'count', 'extra']
        df_all.columns = cols[:len(df_all.columns)]
        # 筛选河南省 (410000)
        df_hn = df_all[df_all['prov_code'].astype(str).str.startswith("41") | df_all['prov_name'].astype(str).str.contains('河南')].copy()
        print(f"  Filtered {len(df_hn)} Henan records from {df_hn['year'].min()} to {df_hn['year'].max()}.")
        df_hn.to_csv(out_csv, index=False, encoding='utf-8')
        print(f"  ✓ Saved cleaned Henan nightlight data to {out_csv}.")

    print("\n=== 3. CHECKING DEM CACHE ===")
    dem_file = os.path.join(DEM_DIR, "410000_z9.npz")
    if os.path.exists(dem_file):
        size_mb = os.path.getsize(dem_file) / (1024 * 1024)
        print(f"  ✓ Henan DEM 410000_z9.npz exists: {size_mb:.2f} MB")
        dem_data = np.load(dem_file)
        print(f"    Keys: {list(dem_data.keys())}, DEM shape: {dem_data['dem'].shape}, res: {dem_data['res']}m")
    else:
        print(f"  ✕ Henan DEM 410000_z9.npz NOT found!")

if __name__ == "__main__":
    prepare_henan()
