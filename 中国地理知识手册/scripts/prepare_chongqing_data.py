# -*- coding: utf-8 -*-
"""重庆市数据准备与前置环境校验脚本
1. 校验并下载重庆市 38 个区县的 DataV GeoJSON 矢量边界数据
2. 从区县夜光数据表中提取清洗重庆市全部区县 1986—2024年夜光时序数据，生成 data/chongqing_nightlight_clean.csv
3. 校验并确认重庆市 300m DEM 高程栅格 (500000_z9.npz)
"""
import os
import sys
import json
import urllib.request
import pandas as pd
import numpy as np
import geopandas as gpd

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册"
DATA_DIR = os.path.join(BASE_DIR, "data")
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")
DEM_DIR = os.path.join(DATA_DIR, "dem", "province")

os.makedirs(DATAV_DIR, exist_ok=True)

# 38 个区县标准列表
CQ_DISTRICTS = [
    ("万州区", "500101"),
    ("涪陵区", "500102"),
    ("渝中区", "500103"),
    ("大渡口区", "500104"),
    ("江北区", "500105"),
    ("沙坪坝区", "500106"),
    ("九龙坡区", "500107"),
    ("南岸区", "500108"),
    ("北碚区", "500109"),
    ("綦江区", "500110"),
    ("大足区", "500111"),
    ("渝北区", "500112"),
    ("巴南区", "500113"),
    ("黔江区", "500114"),
    ("长寿区", "500115"),
    ("江津区", "500116"),
    ("合川区", "500117"),
    ("永川区", "500118"),
    ("南川区", "500119"),
    ("璧山区", "500120"),
    ("铜梁区", "500151"),
    ("潼南区", "500152"),
    ("荣昌区", "500153"),
    ("开州区", "500154"),
    ("梁平区", "500155"),
    ("武隆区", "500156"),
    ("城口县", "500229"),
    ("丰都县", "500230"),
    ("垫江县", "500231"),
    ("忠县", "500232"),
    ("云阳县", "500235"),
    ("奉节县", "500236"),
    ("巫山县", "500237"),
    ("巫溪县", "500238"),
    ("石柱土家族自治县", "500240"),
    ("秀山土家族苗族自治县", "500241"),
    ("酉阳土家族苗族自治县", "500242"),
    ("彭水苗族土家族自治县", "500243")
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

def main():
    print("=== 1. CHECKING & DOWNLOADING CHONGQING DISTRICT BOUNDARIES ===")
    prov_file = os.path.join(DATAV_DIR, "500000_full.json")
    if not os.path.exists(prov_file):
        url = "https://geo.datav.aliyun.com/areas_v3/bound/500000_full.json"
        print(f"Downloading provincial boundary: {url} -> {prov_file}")
        try:
            download_json(url, prov_file)
            print("  ✓ Downloaded 500000_full.json")
        except Exception as e:
            print(f"  ✕ Error: {e}")
    else:
        print(f"  ✓ 500000_full.json exists ({os.path.getsize(prov_file)//1024} KB)")

    # 从 500000_full.json 中分解或单独下载各区县
    cq_gdf = gpd.read_file(prov_file)
    for name, code in CQ_DISTRICTS:
        target_path = os.path.join(DATAV_DIR, f"{code}_full.json")
        target_single = os.path.join(DATAV_DIR, f"{code}.json")
        if not os.path.exists(target_path) and not os.path.exists(target_single):
            # 优先从 500000_full.json 提取保存为单独 json
            match = cq_gdf[cq_gdf['adcode'].astype(str) == str(code)]
            if not match.empty:
                match.to_file(target_path, driver='GeoJSON')
                print(f"  ✓ Extracted {name} ({code}) from 500000_full.json ({os.path.getsize(target_path)//1024} KB)")
            else:
                # 尝试从 DataV 下载
                url = f"https://geo.datav.aliyun.com/areas_v3/bound/{code}.json"
                try:
                    download_json(url, target_single)
                    print(f"  ✓ Downloaded {name} ({code}.json) {os.path.getsize(target_single)//1024} KB")
                except Exception as e:
                    print(f"  ✕ Failed {name} ({code}): {e}")
        else:
            p = target_path if os.path.exists(target_path) else target_single
            print(f"  ✓ {name} ({code}) exists ({os.path.getsize(p)//1024} KB)")

    print("\n=== 2. EXTRACTING CHONGQING NIGHTLIGHT DATA (1986-2024) ===")
    nl_dist_excel = os.path.join(BASE_DIR, "中国省市数据", "夜间灯光数据-省、市、县（1986-2024年）", "夜间灯光数据-区县（1986-2024年）.xlsx")
    out_csv = os.path.join(DATA_DIR, "chongqing_nightlight_clean.csv")

    df_dist_all = pd.read_excel(nl_dist_excel)
    cols_d = ['year', 'prov_name', 'city_name', 'district_name', 'prov_code', 'city_code', 'district_code', 'sum', 'mean', 'min', 'max', 'std', 'count', 'extra']
    df_dist_all.columns = cols_d[:len(df_dist_all.columns)]
    df_cq = df_dist_all[df_dist_all['prov_code'].astype(str).str.startswith("50") | df_dist_all['prov_name'].astype(str).str.contains('重庆')].copy()

    clean_records = []
    # 建立名称匹配字典
    name_to_code = {n: c for n, c in CQ_DISTRICTS}
    # 简化名称映射（如“万州” -> “万州区”）
    for n, c in CQ_DISTRICTS:
        short = n.replace("土家族自治县", "").replace("苗族自治县", "").replace("自治县", "").replace("区", "").replace("县", "")
        name_to_code[short] = c

    for idx, row in df_cq.iterrows():
        d_name = str(row['district_name']).strip()
        d_code = str(row['district_code']).strip()
        yr = row['year']
        val_sum = row['sum']
        val_mean = row['mean']
        val_max = row['max']

        matched_code = d_code
        matched_name = d_name

        if d_code not in [c for _, c in CQ_DISTRICTS]:
            for kn, kc in name_to_code.items():
                if kn in d_name or d_name in kn:
                    matched_code = kc
                    matched_name = [n for n, c in CQ_DISTRICTS if c == kc][0]
                    break

        clean_records.append({
            'year': int(yr),
            'unit_name': matched_name,
            'unit_code': matched_code,
            'sum': val_sum,
            'mean': val_mean,
            'max': val_max
        })

    df_clean = pd.DataFrame(clean_records).drop_duplicates(subset=['year', 'unit_code'])
    df_clean.sort_values(by=['unit_code', 'year'], inplace=True)
    df_clean.to_csv(out_csv, index=False, encoding='utf-8')
    print(f"  ✓ Cleaned nightlight data written to {out_csv} ({len(df_clean)} rows, {df_clean['unit_code'].nunique()} districts)")

    print("\n=== 3. VERIFYING CHONGQING DEM ===")
    dem_file = os.path.join(DEM_DIR, "500000_z9.npz")
    if os.path.exists(dem_file):
        d = np.load(dem_file)
        print(f"  ✓ DEM 500000_z9.npz verified: shape {d['dem'].shape}, res={d['res']}m, elev range [{np.nanmin(d['dem']):.1f}, {np.nanmax(d['dem']):.1f}]")
    else:
        print(f"  ✕ DEM {dem_file} NOT found!")

    print("\n=== CHONGQING DATA PREPARATION COMPLETE ===")

if __name__ == "__main__":
    main()
