# -*- coding: utf-8 -*-
"""补齐省级政区边界：从阿里云 DataV GeoAtlas 下载 {adcode}_full.json。

仅下载 data/boundaries/datav/ 中缺失的文件，已存在则跳过。
"""
import json
import os
import time
import urllib.request

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "data", "boundaries", "datav")
BASE = "https://geo.datav.aliyun.com/areas_v3/bound/{}.json"

ADCODES = [
    "110000", "120000", "130000", "140000", "150000",
    "210000", "220000", "230000",
    "310000", "320000", "330000", "340000", "350000", "360000", "370000",
    "410000", "420000", "430000", "440000", "450000", "460000",
    "500000", "510000", "520000", "530000", "540000",
    "610000", "620000", "630000", "640000", "650000",
    "710000", "810000", "820000",
]

os.makedirs(DATA, exist_ok=True)
ok, skip, fail = 0, 0, []
for code in ADCODES:
    fn = f"{code}_full.json"
    p = os.path.join(DATA, fn)
    if os.path.exists(p) and os.path.getsize(p) > 1000:
        skip += 1
        continue
    url = BASE.format(fn[:-5])
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            raw = r.read()
        json.loads(raw)          # 校验
        with open(p, "wb") as f:
            f.write(raw)
        ok += 1
        print(f"  ✓ {fn}  {len(raw)//1024} KB")
    except Exception as e:
        fail.append((code, str(e)[:80]))
        print(f"  ✗ {fn}  {type(e).__name__}: {str(e)[:80]}")
    time.sleep(0.15)

print(f"\n完成：新下载 {ok}，已存在 {skip}，失败 {len(fail)}")
for c, e in fail:
    print("   失败:", c, e)
