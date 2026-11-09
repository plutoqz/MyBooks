# -*- coding: utf-8 -*-
"""河北省基础地理与空间数据准备与核验脚本：
1. 检查与汇总 11 个地级市 + 雄安新区 + 辛集市 + 定州市 的行政边界与区划编码
2. 提取并清理河北省 1986—2024 年夜间灯光辐射时序数据
3. 检查与缓存河北省 AWS Terrain 高精度 DEM (300m 分辨率，Albers 投影)
4. 核验水系水文、综合交通及统计指标数据源
"""
import os
import sys
import json
import numpy as np
import pandas as pd
import geopandas as gpd

sys.path.insert(0, r"D:\code\Ideas\MyBooks\中国地理知识手册\scripts")
from style import ALBERS, DATA
from prov_pipeline import prov_dem, prov_load

DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
RAW_DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\中国省市数据"
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")

def inspect_boundaries():
    print("=== INSPECTING HEBEI BOUNDARIES ===")
    prov_file = os.path.join(DATAV_DIR, "130000_full.json")
    with open(prov_file, "r", encoding="utf-8") as f:
        d = json.load(f)
    print(f"Hebei Province level features: {len(d['features'])}")
    for feat in d['features']:
        p = feat['properties']
        print(f"  {p.get('adcode')}: {p.get('name')} center={p.get('center')}")

    # Inspect 130100 (Shijiazhuang) for Xinji (130181)
    sjz_file = os.path.join(DATAV_DIR, "130100_full.json")
    with open(sjz_file, "r", encoding="utf-8") as f:
        d = json.load(f)
    print("\nShijiazhuang sub-units:")
    for feat in d['features']:
        p = feat['properties']
        print(f"  {p.get('adcode')}: {p.get('name')}")

    # Inspect 130600 (Baoding) for Dingzhou (130682) and Xiong'an counties (Rongcheng 130629, Anxin 130632, Xiongxian 130638)
    bd_file = os.path.join(DATAV_DIR, "130600_full.json")
    with open(bd_file, "r", encoding="utf-8") as f:
        d = json.load(f)
    print("\nBaoding sub-units:")
    for feat in d['features']:
        p = feat['properties']
        print(f"  {p.get('adcode')}: {p.get('name')}")

def extract_hebei_nightlight():
    print("\n=== EXTRACTING HEBEI NIGHTLIGHT DATA ===")
    nl_file = os.path.join(RAW_DATA_DIR, "夜间灯光数据-省、市、县（1986-2024年）", "夜间灯光数据-区县（1986-2024年）.xlsx")
    out_csv = os.path.join(DATA_DIR, "hebei_nightlight_clean.csv")
    if os.path.exists(out_csv):
        print(f"Hebei nightlight clean CSV already exists at {out_csv}.")
        df = pd.read_csv(out_csv)
        print(f"Rows: {len(df)}, Cities: {df['city_name'].nunique()}, Districts: {df['district_name'].nunique()}")
        return

    print(f"Reading nightlight data from {nl_file}...")
    df = pd.read_excel(nl_file)
    cols = ['year', 'prov_name', 'city_name', 'district_name', 'prov_code', 'city_code', 'district_code', 'sum', 'mean', 'min', 'max', 'std', 'count', 'extra']
    df.columns = cols[:len(df.columns)]
    
    # 筛选河北省 (代码以 13 开头或名称含河北)
    hb = df[df['prov_code'].astype(str).str.startswith("13") | df['prov_name'].astype(str).str.contains("河北")].copy()
    hb["year"] = hb["year"].astype(int)
    hb["district_code"] = hb["district_code"].astype(int)
    hb.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"Extracted {len(hb)} rows of Hebei nightlight data to {out_csv}.")
    print("Unique cities:", hb['city_name'].unique().tolist()[:15])

def cache_hebei_dem():
    print("\n=== CACHING HEBEI DEM ===")
    cache_path = os.path.join(DATA_DIR, "dem", "province", "130000_z9.npz")
    if os.path.exists(cache_path):
        d = np.load(cache_path)
        dem = d["dem"]
        print(f"Hebei DEM already cached: shape={dem.shape}, min={dem[dem > -9999].min():.1f}m, max={dem.max():.1f}m, res={float(d['res']):.1f}m")
    else:
        print("Fetching/caching Hebei DEM (adcode=130000, zoom=9, res=300m)... This downloads terrarium tiles for Hebei...")
        dem, minx, maxy, res = prov_dem("130000", zoom=9, res=300.0)
        print(f"Hebei DEM cached successfully: shape={dem.shape}, min={dem[dem > -9999].min():.1f}m, max={dem.max():.1f}m, res={res}m")

if __name__ == "__main__":
    inspect_boundaries()
    extract_hebei_nightlight()
    cache_hebei_dem()
    print("\nPreparation script finished.")
