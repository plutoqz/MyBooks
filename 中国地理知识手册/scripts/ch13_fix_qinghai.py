# -*- coding: utf-8 -*-
"""修复 DataV 630000（青海）界线的无效几何并补齐 z9 DEM 缓存。"""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import setup, DATA
from prov_pipeline import prov_dem

SRC = os.path.join(DATA, "boundaries", "datav", "630000_full.json")
BAK = os.path.join(DATA, "boundaries", "datav", "630000_full.orig.json")

if __name__ == "__main__":
    setup()
    if not os.path.exists(BAK):
        shutil.copyfile(SRC, BAK)
        print("backup saved:", BAK)
    with open(BAK, encoding="utf-8") as f:
        gj = json.load(f)
    from shapely.geometry import shape, mapping
    from shapely.validation import make_valid
    n_fix = 0
    for feat in gj["features"]:
        geom = shape(feat["geometry"])
        if not geom.is_valid:
            fixed = make_valid(geom)
            # make_valid 可能产出 GeometryCollection，取其面要素
            if fixed.geom_type == "GeometryCollection":
                parts = [g for g in fixed.geoms
                         if g.geom_type in ("Polygon", "MultiPolygon")]
                fixed = parts[0]
                for g in parts[1:]:
                    fixed = fixed.union(g)
            feat["geometry"] = mapping(fixed)
            n_fix += 1
    with open(SRC, "w", encoding="utf-8") as f:
        json.dump(gj, f, ensure_ascii=False)
    print(f"fixed {n_fix} invalid geometries")
    dem, minx, maxy, res = prov_dem("630000", zoom=9, res=300.0)
    valid = (~__import__("numpy").isnan(dem)).sum()
    print(f"青海(630000): z9 done, {dem.shape[1]}x{dem.shape[0]}, "
          f"res={res}, valid_px={valid}")
    print("qinghai fix done")
