# -*- coding: utf-8 -*-
"""重建省级 DEM 缓存，并校验"海拔 0 m"异常块。

旧版 prov_dem 对下载失败的瓦片静默 continue，mosaic 该处保留 np.zeros 初值，
成图上就出现成片绿色矩形（宁夏中部、福建沿海都能看到）。
新版会 raise，本脚本负责逐个重试并把结果汇总。

用法：python rebuild_prov_dem.py [并行数]
"""
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "data", "dem", "province")


def zero_frac(code):
    import numpy as np
    fp = os.path.join(CACHE, f"{code}_z9.npz")
    if not os.path.exists(fp):
        return 1.0
    dem = np.load(fp)["dem"]
    fin = np.isfinite(dem)
    if fin.sum() == 0:
        return 1.0
    return float(((dem == 0) & fin).sum() / fin.sum())


def build(code, tries=3):
    from prov_pipeline import prov_dem
    fp = os.path.join(CACHE, f"{code}_z9.npz")
    if os.path.exists(fp):
        os.remove(fp)
    last = ""
    for k in range(tries):
        try:
            prov_dem(code, zoom=9, res=300.0)
            return code, "ok", zero_frac(code)
        except Exception as e:
            last = f"{type(e).__name__}: {str(e)[:70]}"
    return code, f"fail: {last}", 1.0


if __name__ == "__main__":
    from prefetch_prov_dem import ADCODES
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    print(f"重建 {len(ADCODES)} 个省，{workers} 路并行", flush=True)
    worst = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(build, c): c for c in ADCODES}
        for f in as_completed(futs):
            code, st, zf = f.result()
            print(f"  {code}: {st}  zero_frac={zf:.3f}", flush=True)
            if st != "ok" or zf > 0.05:
                worst.append((code, st, round(zf, 3)))
    print("\n仍异常：", worst)
