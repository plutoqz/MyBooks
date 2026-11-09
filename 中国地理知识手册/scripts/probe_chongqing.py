# -*- coding: utf-8 -*-
import os
import sys
import geopandas as gpd
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册"
DATA_DIR = os.path.join(BASE_DIR, "data")
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")

# 1. 检查 500000_full.json
json_file = os.path.join(DATAV_DIR, "500000_full.json")
gdf = gpd.read_file(json_file).sort_values("adcode")
print(f"Total features in 500000_full.json: {len(gdf)}")
districts = []
for idx, r in gdf.iterrows():
    districts.append((str(r['adcode']), r['name']))
print("Districts count:", len(districts))
for c, n in districts[:10]:
    print(f"  {c}: {n}")
print("  ...")
for c, n in districts[-5:]:
    print(f"  {c}: {n}")

# 2. 检查区县夜光表
nl_dist_excel = os.path.join(BASE_DIR, "中国省市数据", "夜间灯光数据-省、市、县（1986-2024年）", "夜间灯光数据-区县（1986-2024年）.xlsx")
print("\nReading nightlight district excel...")
df = pd.read_excel(nl_dist_excel)
cols = ['year', 'prov_name', 'city_name', 'district_name', 'prov_code', 'city_code', 'district_code', 'area_name', 'region_type', 'sum', 'mean', 'min', 'max', 'std', 'count', 'extra']
df.columns = cols[:len(df.columns)]
cq_nl = df[df['prov_code'].astype(str).str.startswith('50') | df['prov_name'].astype(str).str.contains('重庆')].copy()
print(f"Found {len(cq_nl)} rows for Chongqing in district nightlight table.")
print("Unique district_codes in nightlight:", cq_nl['district_code'].nunique())
print("Unique district_names in nightlight:", cq_nl['district_name'].unique().tolist()[:10])

# 3. 检查 DEM
dem_file = os.path.join(DATA_DIR, "dem", "province", "500000_z9.npz")
if os.path.exists(dem_file):
    import numpy as np
    d = np.load(dem_file)
    print("\nDEM exists. Shape:", d['dem'].shape, "minx:", d['minx'], "maxy:", d['maxy'], "res:", d['res'], "min/max:", np.nanmin(d['dem']), np.nanmax(d['dem']))
