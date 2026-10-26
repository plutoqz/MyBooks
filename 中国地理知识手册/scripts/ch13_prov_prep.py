# -*- coding: utf-8 -*-
"""批量生成分省 DEM 缓存（天津/河北/山西/辽宁/吉林/黑龙江/山东/河南/陕西）。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import setup
from prov_pipeline import prov_dem

PROVS = {
    "120000": "天津", "130000": "河北", "140000": "山西",
    "210000": "辽宁", "220000": "吉林", "230000": "黑龙江",
    "370000": "山东", "410000": "河南", "610000": "陕西",
}

if __name__ == "__main__":
    setup()
    for ad, name in PROVS.items():
        try:
            dem, minx, maxy, res = prov_dem(ad, zoom=9, res=300.0)
            valid = (~__import__("numpy").isnan(dem)).sum()
            print(f"{name}({ad}): z9 done, {dem.shape[1]}x{dem.shape[0]}, "
                  f"res={res}, valid_px={valid}")
        except Exception as e:
            print(f"{name}({ad}): FAILED {e}")
    print("prep done")
