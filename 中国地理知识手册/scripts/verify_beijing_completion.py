# -*- coding: utf-8 -*-
"""验证北京市全部章节与图表产出"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEC_DIR = os.path.join(ROOT, "sections_vol2")
HTML_DIR = os.path.join(ROOT, "html")
FIG_DIR = os.path.join(ROOT, "figures")

secs = sorted([f for f in os.listdir(SEC_DIR) if f.startswith("01-") and f.endswith(".md")])
print(f"=== SECTIONS_VOL2: {len(secs)} files ===")
total_chars = 0
for f in secs:
    p = os.path.join(SEC_DIR, f)
    text = open(p, encoding="utf-8").read()
    chars = len(text)
    total_chars += chars
    html_name = f.replace(".md", ".html")
    html_exists = os.path.exists(os.path.join(HTML_DIR, html_name))
    print(f"{f:40s} | {chars:5d} 字 | HTML: {'OK' if html_exists else 'MISSING'}")

print(f"\nTOTAL TEXT VOLUME: {total_chars:,} 汉字/字符")
figs = [f for f in os.listdir(FIG_DIR) if f.startswith("fig01-")]
print(f"=== CARTOGRAPHIC FIGURES: {len(figs)} files ===")
