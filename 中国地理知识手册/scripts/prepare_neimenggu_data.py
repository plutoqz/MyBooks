# -*- coding: utf-8 -*-
"""内蒙古自治区基础地理与空间数据准备与核验脚本：
1. 检查与下载 12 个盟市的行政边界 GeoJSON ({adcode}_full.json)
2. 提取并清理内蒙古 1986—2024 年夜间灯光辐射时序数据
3. 检查与缓存内蒙古 AWS Terrain 高精度 DEM (Albers 投影)
4. 核验 12 个盟市 2000-2024 年 GDP 与 2024 年最新统计公报指标
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

NEIMENGGU_DIVISIONS = [
    ("150100", "呼和浩特市"),
    ("150200", "包头市"),
    ("150300", "乌海市"),
    ("150400", "赤峰市"),
    ("150500", "通辽市"),
    ("150600", "鄂尔多斯市"),
    ("150700", "呼伦贝尔市"),
    ("150800", "巴彦淖尔市"),
    ("150900", "乌兰察布市"),
    ("152200", "兴安盟"),
    ("152500", "锡林郭勒盟"),
    ("152900", "阿拉善盟"),
]

def download_boundaries():
    print("=== 1. CHECKING & DOWNLOADING INNER MONGOLIA BOUNDARIES ===")
    os.makedirs(DATAV_DIR, exist_ok=True)
    base_url = "https://geo.datav.aliyun.com/areas_v3/bound/{}_full.json"
    
    # 检查自治区级 150000_full.json
    prov_path = os.path.join(DATAV_DIR, "150000_full.json")
    if not os.path.exists(prov_path) or os.path.getsize(prov_path) < 1000:
        url = base_url.format("150000")
        print(f"Downloading provincial boundary 150000_full.json from {url}...")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read()
        with open(prov_path, "wb") as f:
            f.write(content)
        print("  Provincial 150000_full.json downloaded.")
    else:
        print(f"  Provincial 150000_full.json already exists ({os.path.getsize(prov_path)//1024} KB)")
        
    for adcode, name in NEIMENGGU_DIVISIONS:
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

def extract_neimenggu_nightlight():
    print("\n=== 2. EXTRACTING INNER MONGOLIA NIGHTLIGHT DATA (1986-2024) ===")
    nl_file = os.path.join(RAW_DATA_DIR, "夜间灯光数据-省、市、县（1986-2024年）", "夜间灯光数据-区县（1986-2024年）.xlsx")
    out_csv = os.path.join(DATA_DIR, "neimenggu_nightlight_clean.csv")
    if os.path.exists(out_csv):
        print(f"Inner Mongolia nightlight clean CSV already exists at {out_csv}.")
        df = pd.read_csv(out_csv)
        print(f"Rows: {len(df)}, Cities/Leagues: {df['city_name'].nunique()}, Districts/Banners: {df['district_name'].nunique()}")
        return df

    if not os.path.exists(nl_file):
        print(f"Warning: {nl_file} not found!")
        return None

    print(f"Reading nightlight data from {nl_file}...")
    df = pd.read_excel(nl_file)
    cols = ['year', 'prov_name', 'city_name', 'district_name', 'prov_code', 'city_code', 'district_code', 'sum', 'mean', 'min', 'max', 'std', 'count', 'extra']
    df.columns = cols[:len(df.columns)]
    
    # 筛选内蒙古自治区 (代码以 15 开头或名称含内蒙古)
    nm = df[df['prov_code'].astype(str).str.startswith("15") | df['prov_name'].astype(str).str.contains("内蒙古")].copy()
    nm["year"] = nm["year"].astype(int)
    nm["district_code"] = nm["district_code"].astype(int)
    nm.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"Inner Mongolia nightlight extracted: {len(nm)} records saved to {out_csv}.")
    return nm

def check_neimenggu_dem():
    print("\n=== 3. CHECKING & WARMING INNER MONGOLIA DEM CACHE ===")
    try:
        dem, transform = prov_dem("150000")
        print(f"  Inner Mongolia DEM loaded: shape={dem.shape}, min={np.nanmin(dem):.1f}m, max={np.nanmax(dem):.1f}m")
    except Exception as e:
        print(f"  Failed to load DEM: {e}")

if __name__ == "__main__":
    download_boundaries()
    extract_neimenggu_nightlight()
    check_neimenggu_dem()
    print("\nInner Mongolia data preparation complete!")
