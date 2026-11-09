# -*- coding: utf-8 -*-
"""江苏省基础地理与空间数据准备与核验脚本：
1. 检查并下载江苏省 (320000) 及 13 个地级市的行政边界 GeoJSON ({adcode}_full.json)
2. 提取并清理江苏省 1986—2024 年夜间灯光辐射时序数据 (data/jiangsu_nightlight_clean.csv)
3. 校验江苏省 Albers DEM 缓存 (data/dem/province/320000_z9.npz)
"""
import os
import sys
import json
import time
import urllib.request
import pandas as pd
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
RAW_DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\中国省市数据"
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")

JIANGSU_DIVISIONS = [
    ("320100", "南京市"),
    ("320200", "无锡市"),
    ("320300", "徐州市"),
    ("320400", "常州市"),
    ("320500", "苏州市"),
    ("320600", "南通市"),
    ("320700", "连云港市"),
    ("320800", "淮安市"),
    ("320900", "盐城市"),
    ("321000", "扬州市"),
    ("321100", "镇江市"),
    ("321200", "泰州市"),
    ("321300", "宿迁市"),
]

def download_boundaries():
    print("=== 1. CHECKING & DOWNLOADING JIANGSU BOUNDARIES ===")
    os.makedirs(DATAV_DIR, exist_ok=True)
    base_url = "https://geo.datav.aliyun.com/areas_v3/bound/{}_full.json"
    alt_base = "https://geo.datav.aliyun.com/areas_v3/bound/{}.json"
    
    prov_path = os.path.join(DATAV_DIR, "320000_full.json")
    if os.path.exists(prov_path) and os.path.getsize(prov_path) > 1000:
        print(f"  ✓ Provincial boundary 320000_full.json exists ({os.path.getsize(prov_path)//1024} KB)")
    else:
        print("  Downloading provincial boundary 320000_full.json...")
        req = urllib.request.Request(base_url.format("320000"), headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read()
        with open(prov_path, "wb") as f:
            f.write(content)
        print(f"  ✓ Downloaded 320000_full.json ({len(content)//1024} KB)")

    for adcode, name in JIANGSU_DIVISIONS:
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
        except Exception as e:
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

def extract_jiangsu_nightlight():
    print("\n=== 2. EXTRACTING JIANGSU NIGHTLIGHT DATA (1986-2024) ===")
    out_csv = os.path.join(DATA_DIR, "jiangsu_nightlight_clean.csv")
    if os.path.exists(out_csv):
        print(f"  ✓ Jiangsu nightlight clean CSV already exists at {out_csv}.")
        df = pd.read_csv(out_csv)
        print(f"    Rows: {len(df)}, Cities: {df['city_name'].nunique()}, Districts/Counties: {df['district_name'].nunique()}")
        return df

    nl_file = os.path.join(RAW_DATA_DIR, "夜间灯光数据-省、市、县（1986-2024年）", "夜间灯光数据-区县（1986-2024年）.xlsx")
    if not os.path.exists(nl_file):
        print(f"  ✗ Warning: {nl_file} not found!")
        return None

    print(f"  Reading nightlight data from {nl_file}...")
    df = pd.read_excel(nl_file)
    cols = ['year', 'prov_name', 'city_name', 'district_name', 'prov_code', 'city_code', 'district_code', 'sum', 'mean', 'min', 'max', 'std', 'count', 'extra']
    df.columns = cols[:len(df.columns)]
    
    # 筛选江苏省 (代码以 32 开头或名称含江苏)
    js = df[df['prov_code'].astype(str).str.startswith("32") | df['prov_name'].astype(str).str.contains("江苏")].copy()
    print(f"  Filtered {len(js)} Jiangsu records from {df['year'].min()} to {df['year'].max()}.")
    js.to_csv(out_csv, index=False, encoding='utf-8-sig')
    print(f"  ✓ Saved cleaned Jiangsu nightlight data to {out_csv}.")
    return js

def check_resources():
    print("\n=== 3. CHECKING DEM CACHE ===")
    dem_npz = os.path.join(DATA_DIR, "dem", "province", "320000_z9.npz")
    if os.path.exists(dem_npz):
        fsize_mb = os.path.getsize(dem_npz) / (1024 * 1024)
        print(f"  ✓ Jiangsu DEM 320000_z9.npz exists: {fsize_mb:.2f} MB")
        d = np.load(dem_npz)
        print(f"    Keys: {list(d.keys())}, DEM shape: {d['dem'].shape}, res: {d.get('res', 'unknown')}m")
    else:
        print(f"  ✗ Jiangsu DEM {dem_npz} missing!")

if __name__ == "__main__":
    download_boundaries()
    extract_jiangsu_nightlight()
    check_resources()
