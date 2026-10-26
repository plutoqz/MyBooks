# -*- coding: utf-8 -*-
"""临时审计脚本：核对 md / html / figures 三者的一致性。"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEC = os.path.join(ROOT, "sections")
HTML = os.path.join(ROOT, "html")
FIG = os.path.join(ROOT, "figures")

mds = sorted(f for f in os.listdir(SEC) if f.endswith(".md"))
htmls = {f for f in os.listdir(HTML) if f.endswith(".html")}
figs = set(os.listdir(FIG))

print(f"md={len(mds)}  html={len(htmls)}  figures={len(figs)}")
print("\n== md 无 html / html 过期 ==")
for m in mds:
    stem = m[:-3]
    h = stem + ".html"
    if h not in htmls:
        print(f"MISSING HTML  {m}")
        continue
    if os.path.getmtime(os.path.join(SEC, m)) > os.path.getmtime(os.path.join(HTML, h)) + 1:
        print(f"STALE HTML    {m}")

print("\n== md 引用的图缺失 ==")
used = {}
for m in mds:
    with open(os.path.join(SEC, m), encoding="utf-8") as f:
        t = f.read()
    for alt, p in re.findall(r"!\[([^\]]*)\]\(([^)]+)\)", t):
        name = os.path.basename(p)
        used.setdefault(name, []).append(m)
        if name not in figs:
            print(f"MISSING FIG   {m} -> {p}")

print("\n== figures 未被任何 md 引用 ==")
for f in sorted(figs):
    if f not in used:
        print(f"UNUSED FIG    {f}")

print("\n== 每节引用的图数 ==")
for m in mds:
    with open(os.path.join(SEC, m), encoding="utf-8") as f:
        t = f.read()
    n = len(re.findall(r"!\[([^\]]*)\]\(([^)]+)\)", t))
    chars = len(re.sub(r"\s", "", t))
    print(f"{m:44s} figs={n}  chars={chars}")
