# -*- coding: utf-8 -*-
"""港澳台（香港、澳门、台湾）数据准备与前置环境校验脚本
1. 校验香港 (810000)、澳门 (820000)、台湾 (710000) 的边界 GeoJSON 数据
2. 检查并提取港澳台夜光时序数据或统计公报经济指标
3. 校验并确认 DEM 高程栅格缓存 (810000_z11, 820000_z9, 710000_z9)
"""
import os
import sys
import json
import numpy as np
import pandas as pd
import geopandas as gpd

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册"
DATA_DIR = os.path.join(BASE_DIR, "data")
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")
DEM_DIR = os.path.join(DATA_DIR, "dem", "province")

print("=== 1. CHECKING BOUNDARIES ===")
for name, code, ftype in [("香港特别行政区", "810000", "810000_full.json"), 
                         ("澳门特别行政区", "820000", "820000_full.json"), 
                         ("台湾省", "710000", "710000.json")]:
    p = os.path.join(DATAV_DIR, ftype)
    if os.path.exists(p):
        gdf = gpd.read_file(p)
        print(f"✓ {name} ({code}): {len(gdf)} features, file size={os.path.getsize(p)//1024} KB")
        if 'name' in gdf.columns:
            print(f"  Names: {gdf['name'].tolist()}")
    else:
        print(f"✕ Missing boundary: {p}")

print("\n=== 2. CHECKING DEM NPZ ===")
for name, code in [("香港特别行政区 z11", "810000_z11.npz"), 
                   ("香港特别行政区 z9", "810000_z9.npz"), 
                   ("澳门特别行政区 z9", "820000_z9.npz"), 
                   ("台湾省 z9", "710000_z9.npz")]:
    p = os.path.join(DEM_DIR, code)
    if os.path.exists(p):
        d = np.load(p)
        print(f"✓ {name}: keys={d.files}")
        for k in d.files:
            arr = d[k]
            if hasattr(arr, 'shape'):
                print(f"    {k}: shape={arr.shape}")
        if 'dem' in d.files:
            dem = d['dem']
            valid = dem[~np.isnan(dem)]
            if len(valid) > 0:
                print(f"    dem valid: min={valid.min():.1f}m, max={valid.max():.1f}m")
    else:
        print(f"✕ Missing DEM: {p}")

print("\n=== 3. CHECKING NIGHTLIGHT DATA ===")
excel_folder = os.path.join(BASE_DIR, "中国省市数据", "夜间灯光数据-省、市、县（1986-2024年）")
for ef in os.listdir(excel_folder):
    if ef.endswith(".xlsx"):
        p = os.path.join(excel_folder, ef)
        try:
            df = pd.read_excel(p)
            first_col = df.columns[0]
            matched = df[df[first_col].astype(str).str.contains("香港|澳门|台湾|81|82|71", na=False)]
            print(f"{ef}: total rows={len(df)}, matched HK/MO/TW rows={len(matched)}")
            if len(matched) > 0:
                print(f"  Sample matching entries: {matched.iloc[:3, :4]}")
        except Exception as e:
            print(f"{ef}: error reading {e}")
