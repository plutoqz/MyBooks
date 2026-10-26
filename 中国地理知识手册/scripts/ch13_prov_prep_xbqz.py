# -*- coding: utf-8 -*-
"""西北与青藏六省区准备：DataV 界线下载 + 批量 z9 DEM 缓存。

内蒙古(150000) 甘肃(620000) 宁夏(640000) 新疆(650000) 青海(630000) 西藏(540000)
"""
import json
import os
import sys
from urllib.request import urlopen

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import setup, DATA
from prov_pipeline import prov_dem

PROVS = {
    "150000": "内蒙古", "540000": "西藏", "620000": "甘肃",
    "630000": "青海", "640000": "宁夏", "650000": "新疆",
}


def fetch_bound(ad, name):
    d = os.path.join(DATA, "boundaries", "datav")
    p = os.path.join(d, f"{ad}_full.json")
    if os.path.exists(p):
        print(f"{name}: bound exists")
        return
    url = f"https://geo.datav.aliyun.com/areas_v3/bound/{ad}_full.json"
    raw = urlopen(url, timeout=120).read()
    json.loads(raw)  # 校验
    with open(p, "wb") as f:
        f.write(raw)
    print(f"{name}: bound downloaded {len(raw)//1024} KB")


if __name__ == "__main__":
    setup()
    for ad, name in PROVS.items():
        try:
            fetch_bound(ad, name)
        except Exception as e:
            print(f"{name}: BOUND FAILED {e}")
            continue
        try:
            dem, minx, maxy, res = prov_dem(ad, zoom=9, res=300.0)
            valid = (~__import__("numpy").isnan(dem)).sum()
            print(f"{name}({ad}): z9 done, {dem.shape[1]}x{dem.shape[0]}, "
                  f"res={res}, valid_px={valid}")
        except Exception as e:
            print(f"{name}({ad}): DEM FAILED {e}")
    print("prep xbqz done")
