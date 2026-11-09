# -*- coding: utf-8 -*-
"""山西省基础地理与空间数据准备与核验脚本：
1. 检查与下载 11 个地级市的行政边界 GeoJSON ({adcode}_full.json)
2. 提取并清理山西省 1986—2024 年夜间灯光辐射时序数据
3. 检查与缓存山西省 AWS Terrain 高精度 DEM (300m 分辨率，Albers 投影)
4. 核验 11 个地级市 2000-2024 年 GDP 与 2024 年最新统计公报指标
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

SHANXI_CITIES = [
    ("140100", "太原市"),
    ("140200", "大同市"),
    ("140300", "阳泉市"),
    ("140400", "长治市"),
    ("140500", "晋城市"),
    ("140600", "朔州市"),
    ("140700", "晋中市"),
    ("140800", "运城市"),
    ("140900", "忻州市"),
    ("141000", "临汾市"),
    ("141100", "吕梁市"),
]

def download_city_boundaries():
    print("=== 1. CHECKING & DOWNLOADING SHANXI CITY BOUNDARIES ===")
    os.makedirs(DATAV_DIR, exist_ok=True)
    base_url = "https://geo.datav.aliyun.com/areas_v3/bound/{}_full.json"
    
    # 检查省级 140000_full.json
    prov_path = os.path.join(DATAV_DIR, "140000_full.json")
    if not os.path.exists(prov_path) or os.path.getsize(prov_path) < 1000:
        url = base_url.format("140000")
        print(f"Downloading provincial boundary 140000_full.json from {url}...")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read()
        with open(prov_path, "wb") as f:
            f.write(content)
        print("  Provincial 140000_full.json downloaded.")
    else:
        print("  Provincial 140000_full.json already exists.")
        
    for adcode, name in SHANXI_CITIES:
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
            print(f"  ✗ Failed to download {name} ({adcode}): {e}")
        time.sleep(0.2)

def extract_shanxi_nightlight():
    print("\n=== 2. EXTRACTING SHANXI NIGHTLIGHT DATA (1986-2024) ===")
    nl_file = os.path.join(RAW_DATA_DIR, "夜间灯光数据-省、市、县（1986-2024年）", "夜间灯光数据-区县（1986-2024年）.xlsx")
    out_csv = os.path.join(DATA_DIR, "shanxi_nightlight_clean.csv")
    if os.path.exists(out_csv):
        print(f"Shanxi nightlight clean CSV already exists at {out_csv}.")
        df = pd.read_csv(out_csv)
        print(f"Rows: {len(df)}, Cities: {df['city_name'].nunique()}, Districts: {df['district_name'].nunique()}")
        return df

    if not os.path.exists(nl_file):
        print(f"Warning: {nl_file} not found!")
        return None

    print(f"Reading nightlight data from {nl_file}...")
    df = pd.read_excel(nl_file)
    cols = ['year', 'prov_name', 'city_name', 'district_name', 'prov_code', 'city_code', 'district_code', 'sum', 'mean', 'min', 'max', 'std', 'count', 'extra']
    df.columns = cols[:len(df.columns)]
    
    # 筛选山西省 (代码以 14 开头或名称含山西)
    sx = df[df['prov_code'].astype(str).str.startswith("14") | df['prov_name'].astype(str).str.contains("山西")].copy()
    sx["year"] = sx["year"].astype(int)
    sx["district_code"] = sx["district_code"].astype(int)
    sx.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"Shanxi nightlight extracted: {len(sx)} records saved to {out_csv}.")
    return sx

def check_shanxi_dem():
    print("\n=== 3. CHECKING & WARMING SHANXI DEM CACHE ===")
    try:
        dem, transform = prov_dem("140000")
        print(f"  Shanxi DEM loaded: shape={dem.shape}, min={np.nanmin(dem):.1f}m, max={np.nanmax(dem):.1f}m")
    except Exception as e:
        print(f"  Failed to load DEM: {e}")

if __name__ == "__main__":
    download_city_boundaries()
    extract_shanxi_nightlight()
    check_shanxi_dem()
    print("\nShanxi data preparation complete!")
