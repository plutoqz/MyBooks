# -*- coding: utf-8 -*-
"""分省数字自洽检查：用绘图脚本里的原始字典 + DataV 界线面积，
反算面积/人口/密度/GDP 的“之最”，与正文“六、之最”表对照。
"""
import importlib
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEC = os.path.join(ROOT, "sections")
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

import geopandas as gpd  # noqa: E402
from style import ALBERS  # noqa: E402

ADCODE = {
    1: "110000", 2: "120000", 3: "130000", 4: "140000", 5: "210000",
    6: "220000", 7: "230000", 8: "370000", 9: "410000", 10: "610000",
    11: "310000", 12: "320000", 13: "330000", 14: "340000", 15: "350000",
    16: "360000", 17: "420000", 18: "430000", 19: "440000", 20: "450000",
    21: "460000", 22: "500000", 23: "510000", 24: "520000", 25: "530000",
    26: "710000", 27: "810000", 28: "820000", 29: "150000", 30: "620000",
    31: "640000", 32: "650000", 33: "630000", 34: "540000",
}

mods = {}
for fn in os.listdir(SCRIPTS):
    if not (fn.startswith("ch13_prov_") and fn.endswith(".py")):
        continue
    txt = open(os.path.join(SCRIPTS, fn), encoding="utf-8").read()
    m = re.search(r'^ADCODE\s*=\s*"(\d+)"', txt, re.M)
    if not m:
        continue
    name = fn[:-3]
    try:
        mods[m.group(1)] = (name, importlib.import_module(name))
    except Exception as e:  # noqa: BLE001
        print(f"  导入失败 {name}: {e}")

AREAS_CACHE = {}


def areas_of(adcode):
    if adcode in AREAS_CACHE:
        return AREAS_CACHE[adcode]
    p = os.path.join(ROOT, "data", "boundaries", "datav", f"{adcode}_full.json")
    if not os.path.exists(p):
        p = os.path.join(ROOT, "data", "boundaries", "datav", f"{adcode}.json")
    g = gpd.read_file(p).to_crs(ALBERS)
    g["geometry"] = g.geometry.buffer(0)
    AREAS_CACHE[adcode] = {n: float(a) / 1e6 for n, a in zip(g["name"], g.geometry.area)}
    return AREAS_CACHE[adcode]


RE_BIG = re.compile(r"面积最大\s*/\s*最小的市[^|]*\|\s*([^|/]+?)\s*([\d\s,]+)\s*km²\s*/\s*([^|/]+?)\s*([\d\s,]+)")
RE_POP = re.compile(r"人口最多\s*/\s*最少的市[^|]*\|\s*([^|/]+?)\s*([\d\s.,]+)\s*万\s*/\s*([^|/]+?)\s*([\d\s.,]+)")
RE_DEN = re.compile(r"人口密度最高\s*/\s*最低[^|]*\|\s*([^|/]+?)\s*约?\s*([\d\s,]+)\s*人/km²\s*/\s*([^|/]+?)\s*约?\s*([\d\s,]+)")
RE_GDP = re.compile(r"GDP 首位市\s*\|\s*([^（|]+?)\s*([\d\s.,]*)")


def num(s):
    s = re.sub(r"[\s,\u3000\u00a0]", "", s)
    return float(s) if s else 0.0


def norm(n):
    for w in ("市", "自治州", "地区", "盟", "州"):
        n = n.replace(w, "")
    return n.strip()


flagged = []
print(f"可用脚本模块 {len(mods)} 个\n")
for n in range(1, 35):
    ad = ADCODE[n]
    fs = [f for f in os.listdir(SEC) if f.startswith(f"13-05-{n:02d}_")]
    if not fs:
        continue
    f = fs[0]
    t = open(os.path.join(SEC, f), encoding="utf-8").read()
    if ad not in mods:
        continue
    _, mod = mods[ad]
    areas = areas_of(ad)
    pops = getattr(mod, "POP7", None)
    probs = []

    if areas:
        kmax, kmin = max(areas, key=areas.get), min(areas, key=areas.get)
        mb = RE_BIG.search(t)
        if mb:
            tmax, vmax, tmin, vmin = mb.groups()
            if norm(kmax) not in norm(tmax):
                probs.append(f"面积最大写“{tmax}”，量算实为 {kmax} {areas[kmax]:.0f}")
            elif abs(num(vmax) - areas[kmax]) / areas[kmax] > 0.015:
                probs.append(f"面积最大数值 {vmax} vs 量算 {areas[kmax]:.0f}")
            if norm(kmin) not in norm(tmin):
                probs.append(f"面积最小写“{tmin}”，量算实为 {kmin} {areas[kmin]:.0f}")
            elif abs(num(vmin) - areas[kmin]) / areas[kmin] > 0.015:
                probs.append(f"面积最小数值 {vmin} vs 量算 {areas[kmin]:.0f}")

    if pops:
        unit = 1 if sum(pops.values()) > 100000 else 1e4   # 人 或 万人
        popw = {k: v / unit for k, v in pops.items()}
        if unit == 1:
            popw = {k: v / 1e4 for k, v in pops.items()}
        pmax, pmin = max(popw, key=popw.get), min(popw, key=popw.get)
        mp = RE_POP.search(t)
        if mp:
            tmax, vmax, tmin, vmin = mp.groups()
            if norm(pmax) not in norm(tmax):
                probs.append(f"人口最多写“{tmax}”，实为 {pmax} {popw[pmax]:.1f}万")
            elif abs(num(vmax) - popw[pmax]) > 0.15:
                probs.append(f"人口最多数值 {vmax} vs {popw[pmax]:.1f}")
            if norm(pmin) not in norm(tmin):
                probs.append(f"人口最少写“{tmin}”，实为 {pmin} {popw[pmin]:.1f}万")
            elif abs(num(vmin) - popw[pmin]) > 0.15:
                probs.append(f"人口最少数值 {vmin} vs {popw[pmin]:.1f}")
        if areas:
            dens = {k: popw[k] * 1e4 / areas[k] for k in popw if k in areas and areas[k] > 0}
            if dens:
                dmax, dmin = max(dens, key=dens.get), min(dens, key=dens.get)
                md = RE_DEN.search(t)
                if md:
                    tmax, vmax, tmin, vmin = md.groups()
                    if norm(dmax) not in norm(tmax):
                        probs.append(f"密度最高写“{tmax}”，实为 {dmax} {dens[dmax]:.0f}")
                    elif abs(num(vmax) - dens[dmax]) / dens[dmax] > 0.03:
                        probs.append(f"密度最高值 {vmax} vs {dens[dmax]:.0f}")
                    if norm(dmin) not in norm(tmin):
                        probs.append(f"密度最低写“{tmin}”，实为 {dmin} {dens[dmin]:.0f}")
                    elif abs(num(vmin) - dens[dmin]) / max(dens[dmin], 1) > 0.05:
                        probs.append(f"密度最低值 {vmin} vs {dens[dmin]:.0f}")

    gdp = None
    for k in ("GDP24", "GDP25", "GDP"):
        if hasattr(mod, k) and isinstance(getattr(mod, k), dict):
            gdp = getattr(mod, k)
            break
    if gdp and len(gdp) >= 5 and any("市" in k or "州" in k for k in gdp):
        gmax = max(gdp, key=gdp.get)
        mg = RE_GDP.search(t)
        if mg and norm(gmax) not in norm(mg.group(1)):
            probs.append(f"GDP 首位写“{mg.group(1).strip()}”，数据首位为 {gmax}")
        tot = sum(gdp.values())
        m2 = re.search(r"地区生产总值 \| [^|]*?([\d\s]+(?:\.\d+)?)\s*亿元（20\d\d", t)
        if m2 and abs(num(m2.group(1)) - tot) / tot > 0.02:
            probs.append(f"分市州 GDP 合计 {tot:,.0f} 与省表 {num(m2.group(1)):,.0f} 差 {num(m2.group(1))-tot:+,.0f}")

    if probs:
        flagged.append(f)
        print(f"[{f}]")
        for p in probs:
            print("   -", p)

print(f"\n有问题省数：{len(flagged)}")
