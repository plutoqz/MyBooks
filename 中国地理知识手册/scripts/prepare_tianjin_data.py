# -*- coding: utf-8 -*-
"""天津市基础地理与空间数据准备脚本：
1. 提取天津市 16 区 1986—2024 年夜间灯光辐射总量与均值时序数据
2. 缓存天津市 AWS Terrain 高精度 DEM (300m 分辨率，Albers 投影)
3. 验证 16 区 DataV 边界与属性
"""
import os
import sys
import pandas as pd
import geopandas as gpd

sys.path.insert(0, r"D:\code\Ideas\MyBooks\中国地理知识手册\scripts")
from style import ALBERS, DATA
from prov_pipeline import prov_dem

DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
RAW_DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\中国省市数据"

def extract_tianjin_nightlight():
    nl_file = os.path.join(RAW_DATA_DIR, "夜间灯光数据-省、市、县（1986-2024年）", "夜间灯光数据-区县（1986-2024年）.xlsx")
    out_csv = os.path.join(DATA_DIR, "tianjin_nightlight_clean.csv")
    print(f"Reading nightlight data from {nl_file}...")
    df = pd.read_excel(nl_file)
    cols = ['year', 'prov_name', 'city_name', 'district_name', 'prov_code', 'city_code', 'district_code', 'sum', 'mean', 'min', 'max', 'std', 'count', 'extra']
    df.columns = cols[:len(df.columns)]
    
    # 筛选天津市 (代码以 12 开头或名称含天津)
    tj = df[df['prov_code'].astype(str).str.startswith("12") | df['prov_name'].astype(str).str.contains("天津")].copy()
    
    name_map = {
        120101: "和平区",
        120102: "河东区",
        120103: "河西区",
        120104: "南开区",
        120105: "河北区",
        120106: "红桥区",
        120110: "东丽区",
        120111: "西青区",
        120112: "津南区",
        120113: "北辰区",
        120114: "武清区",
        120115: "宝坻区",
        120116: "滨海新区",
        120117: "宁河区",
        120118: "静海区",
        120119: "蓟州区"
    }
    
    tj["district_code"] = tj["district_code"].astype(int)
    tj["district_name"] = tj["district_code"].map(name_map).fillna(tj["district_name"])
    tj["year"] = tj["year"].astype(int)
    tj["prov_name"] = "天津市"
    tj["city_name"] = "天津市"
    
    tj.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"Extracted {len(tj)} rows of Tianjin nightlight data to {out_csv}.")
    print("Tianjin districts present:", tj['district_name'].unique().tolist())

def cache_tianjin_dem():
    print("Fetching/caching Tianjin DEM (adcode=120000, zoom=9, res=300m)...")
    dem, minx, maxy, res = prov_dem("120000", zoom=9, res=300.0)
    print(f"Tianjin DEM cached: shape={dem.shape}, min={dem[dem > -9999].min():.1f}m, max={dem.max():.1f}m, res={res}m")

def verify_boundaries():
    json_path = os.path.join(DATA_DIR, "boundaries", "datav", "120000_full.json")
    gdf = gpd.read_file(json_path)
    print(f"Tianjin 120000_full.json features count: {len(gdf)}")
    for _, row in gdf.iterrows():
        print(f"  {row.get('adcode')}: {row.get('name')} (center: {row.get('center')})")

if __name__ == "__main__":
    extract_tianjin_nightlight()
    verify_boundaries()
    cache_tianjin_dem()
    print("Tianjin spatial base preparation complete!")
