# -*- coding: utf-8 -*-
"""并行预取省级 DEM 缓存（AWS Terrain Terrain-RGB），供分省地势图重跑使用。

用法：python prefetch_prov_dem.py [并行数]
仅下载缺失的缓存，已存在则跳过；单个省失败不影响其余省。
"""
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ADCODES = [
    "110000", "120000", "130000", "140000", "150000",
    "210000", "220000", "230000",
    "310000", "320000", "330000", "340000", "350000", "360000", "370000",
    "410000", "420000", "430000", "440000", "450000", "460000",
    "500000", "520000", "530000", "540000",
    "610000", "620000", "630000", "640000", "650000",
    "710000", "810000", "820000",
]

CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "data", "dem", "province")


def one(code):
    from prov_pipeline import prov_dem
    cache = os.path.join(CACHE, f"{code}_z9.npz")
    if os.path.exists(cache):
        return code, "skip"
    try:
        prov_dem(code, zoom=9, res=300.0)
        return code, "ok"
    except Exception as e:
        return code, f"fail: {type(e).__name__}: {str(e)[:60]}"


if __name__ == "__main__":
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    todo = [c for c in ADCODES if not os.path.exists(os.path.join(CACHE, f"{c}_z9.npz"))]
    print(f"待下载 {len(todo)} 个省，{workers} 路并行", flush=True)
    ok = skip = 0
    fails = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(one, c): c for c in todo}
        for f in as_completed(futs):
            code, st = f.result()
            if st.startswith("ok"):
                ok += 1
            elif st == "skip":
                skip += 1
            else:
                fails.append((code, st))
            print(f"  {code}: {st}", flush=True)
    print(f"\n完成 ok={ok} skip={skip} fail={len(fails)}")
    for c, e in fails:
        print("  ", c, e)
