# -*- coding: utf-8 -*-
"""海南省数据准备与前置环境校验脚本
1. 校验海南全省及 19 个分析单元（4 地级市 + 15 省直辖县级行政单位）的 DataV GeoJSON 边界数据
2. 从地级市与区县夜光数据表中提取海南全部 19 个单元 1986—2024年夜光时序数据，生成 data/hainan_nightlight_clean.csv
3. 校验并确认海南 300m DEM 高程栅格缓存 (460000_z9.npz)
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

HAINAN_UNITS = [
    ("海口市", "460100"),
    ("三亚市", "460200"),
    ("三沙市", "460300"),
    ("儋州市", "460400"),
    ("五指山市", "469001"),
    ("琼海市", "469002"),
    ("文昌市", "469005"),
    ("万宁市", "469006"),
    ("东方市", "469007"),
    ("定安县", "469021"),
    ("屯昌县", "469022"),
    ("澄迈县", "469023"),
    ("临高县", "469024"),
    ("白沙黎族自治县", "469025"),
    ("昌江黎族自治县", "469026"),
    ("乐东黎族自治县", "469027"),
    ("陵水黎族自治县", "469028"),
    ("保亭黎族苗族自治县", "469029"),
    ("琼中黎族苗族自治县", "469030"),
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

def prepare_hainan():
    print("=== 1. CHECKING & DOWNLOADING HAINAN BOUNDARIES ===")
    prov_file = os.path.join(DATAV_DIR, "460000_full.json")
    if not os.path.exists(prov_file):
        url = "https://geo.datav.aliyun.com/areas_v3/bound/460000_full.json"
        print(f"Downloading provincial boundary: {url} -> {prov_file}")
        try:
            download_json(url, prov_file)
            print("  ✓ Downloaded 460000_full.json")
        except Exception as e:
            print(f"  ✕ Error downloading provincial boundary: {e}")
    else:
        print(f"  ✓ Provincial boundary 460000_full.json exists ({os.path.getsize(prov_file)//1024} KB)")

    for name, code in HAINAN_UNITS:
        target_path = os.path.join(DATAV_DIR, f"{code}_full.json")
        if not os.path.exists(target_path):
            url = f"https://geo.datav.aliyun.com/areas_v3/bound/{code}_full.json"
            print(f"Downloading {name} ({code}): {url}")
            try:
                download_json(url, target_path)
                print(f"  ✓ Downloaded {name} ({code}_full.json) {os.path.getsize(target_path)//1024} KB")
            except Exception as e:
                # 尝试下载单一轮廓版
                url_single = f"https://geo.datav.aliyun.com/areas_v3/bound/{code}.json"
                try:
                    download_json(url_single, target_path)
                    print(f"  ✓ Downloaded {name} ({code}.json as fallback) {os.path.getsize(target_path)//1024} KB")
                except Exception as e2:
                    print(f"  ✕ Failed {name} ({code}): {e2}")
        else:
            print(f"  ✓ {name} ({code}_full.json) exists ({os.path.getsize(target_path)//1024} KB)")

    print("\n=== 2. EXTRACTING HAINAN NIGHTLIGHT DATA (1986-2024) ===")
    nl_city_excel = os.path.join(BASE_DIR, "中国省市数据", "夜间灯光数据-省、市、县（1986-2024年）", "夜间灯光数据-地级市（1986-2024年）.xlsx")
    nl_dist_excel = os.path.join(BASE_DIR, "中国省市数据", "夜间灯光数据-省、市、县（1986-2024年）", "夜间灯光数据-区县（1986-2024年）.xlsx")
    out_csv = os.path.join(DATA_DIR, "hainan_nightlight_clean.csv")

    # 1. 读取地级市表（海口、三亚、三沙、儋州）
    print("  Reading prefecture-level nightlight data...")
    df_city_all = pd.read_excel(nl_city_excel)
    cols_c = ['year', 'prov_name', 'city_name', 'prov_code', 'city_code', 'area_name', 'region_type', 'sum', 'mean', 'min', 'max', 'std', 'count', 'extra']
    df_city_all.columns = cols_c[:len(df_city_all.columns)]
    df_city_hn = df_city_all[df_city_all['prov_code'].astype(str).str.startswith("46") | df_city_all['prov_name'].astype(str).str.contains('海南')].copy()

    # 2. 读取区县表（省直辖各县市 469001-469030）
    print("  Reading county-level nightlight data...")
    df_dist_all = pd.read_excel(nl_dist_excel)
    cols_d = ['year', 'prov_name', 'city_name', 'district_name', 'prov_code', 'city_code', 'district_code', 'sum', 'mean', 'min', 'max', 'std', 'count', 'extra']
    df_dist_all.columns = cols_d[:len(df_dist_all.columns)]
    df_dist_hn = df_dist_all[df_dist_all['prov_code'].astype(str).str.startswith("46") | df_dist_all['prov_name'].astype(str).str.contains('海南')].copy()
    # 筛选省直辖县级单位 (district_code starts with 469)
    df_dist_hn_sub = df_dist_hn[df_dist_hn['district_code'].astype(str).str.startswith("469")].copy()
    
    # 统一格式合并
    # 对地级市：city_code 即为单元编码
    city_records = []
    for _, r in df_city_hn.iterrows():
        city_records.append({
            "year": r["year"],
            "unit_name": r["city_name"],
            "unit_code": str(int(float(r["city_code"]))),
            "sum": r["sum"],
            "mean": r["mean"],
            "max": r["max"]
        })
    # 对省辖县市：district_code 即为单元编码
    for _, r in df_dist_hn_sub.iterrows():
        city_records.append({
            "year": r["year"],
            "unit_name": r["district_name"],
            "unit_code": str(int(float(r["district_code"]))),
            "sum": r["sum"],
            "mean": r["mean"],
            "max": r["max"]
        })

    df_combined = pd.DataFrame(city_records)
    print(f"  Extracted total records: {len(df_combined)}")
    print(f"  Unique units ({len(df_combined['unit_code'].unique())}): {sorted(df_combined['unit_code'].unique())}")
    print(f"  Years range: {df_combined['year'].min()} - {df_combined['year'].max()}")
    
    df_combined.to_csv(out_csv, index=False, encoding='utf-8')
    print(f"  ✓ Saved clean Hainan nightlight data to: {out_csv}")

    print("\n=== 3. CHECKING HAINAN DEM DATA ===")
    dem_path = os.path.join(DEM_DIR, "460000_z9.npz")
    if os.path.exists(dem_path):
        size_mb = os.path.getsize(dem_path) / 1024 / 1024
        print(f"  ✓ DEM raster {dem_path} exists ({size_mb:.2f} MB)")
        npz = np.load(dem_path)
        dem = npz['dem']
        print(f"    Shape: {dem.shape}, Min: {np.nanmin(dem):.1f}m, Max: {np.nanmax(dem):.1f}m, Mean: {np.nanmean(dem):.1f}m")
    else:
        print(f"  ✕ DEM raster {dem_path} NOT FOUND! Need download or synthesis.")

if __name__ == "__main__":
    prepare_hainan()
