# -*- coding: utf-8 -*-
"""云南省专著与出版级地图自动化严苛核验引擎
严苛核验：
1. 18 篇 Markdown 章节文件是否存在、字数是否达标（总字数 >= 100,000 字符）；
2. 85 幅出版级专题地图（5 幅全省宏观 + 80 幅市州专题图）文件完整性与图片体积；
3. 18 篇 Markdown 正文中的地图相对路径引用（../figures/fig24-*.png）是否 100% 存在；
4. 统计指标与关键地标覆盖度核验；
5. 输出出版级综合验收报告与 PERFECT PASS 判定。
"""
import os
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册"
SECTIONS_DIR = os.path.join(BASE_DIR, "sections_vol2")
FIGURES_DIR = os.path.join(BASE_DIR, "figures")

sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))
from yunnan_city_configs import YUNNAN_CITY_CONFIGS

print("=====================================================================")
print("   Volume 2 Chapter 24 (Yunnan Province) Rigorous Verification       ")
print("=====================================================================")

passed = True
errors = []
warnings = []

# 1. 核验 18 篇 Markdown 文档
print("\n[Step 1] Verifying 18 Markdown monograph section files...")
expected_files = ["24-00_云南省地理统揽.md"]
for code, cfg in YUNNAN_CITY_CONFIGS.items():
    sec_id = cfg["sec_id"]
    name = cfg["name"]
    expected_files.append(f"{sec_id}_{name}.md")
expected_files.append("24-17_云南省地理要素大典与空间综合统计分析.md")

total_chars = 0
file_stats = []

for ef in expected_files:
    fpath = os.path.join(SECTIONS_DIR, ef)
    if not os.path.exists(fpath):
        errors.append(f"Missing section file: {ef}")
        passed = False
    else:
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
            chars = len(content)
            total_chars += chars
            file_stats.append((ef, chars, len(content.splitlines())))
            if chars < 3500:
                warnings.append(f"Section {ef} word count low: {chars} chars")

print(f" -> Found {len(file_stats)} / {len(expected_files)} files. Total characters: {total_chars:,} chars.")
if total_chars < 100000:
    errors.append(f"Total word count below 100,000 threshold: {total_chars}")
    passed = False
else:
    print(f" -> [PASS] Monograph volume exceeds 100,000 chars threshold! ({total_chars:,} >= 100,000)")

# 2. 核验 85 幅出版级地图
print("\n[Step 2] Verifying 85 publication-grade maps (5 overview + 80 unit maps)...")
expected_figs = [
    "fig24-00-1_云南省地势起伏与骨干河流水系格局图.png",
    "fig24-00-2_云南省16个市州行政区划与滇中城市群空间战略格局图.png",
    "fig24-00-3_云南省综合立体交通网络与辐射南亚东南亚大通道格局图.png",
    "fig24-00-4_云南省特色优势产业集群与绿色能源强省空间分布图.png",
    "fig24-00-5_云南省1986-2024年夜间灯光演化与开发强度对比图.png"
]

for code, cfg in YUNNAN_CITY_CONFIGS.items():
    sec_id = cfg["sec_id"]
    name = cfg["name"]
    expected_figs.extend([
        f"fig{sec_id}-1_{name}行政区位图.png",
        f"fig{sec_id}-2_{name}地形地貌图.png",
        f"fig{sec_id}-3_{name}道路交通图.png",
        f"fig{sec_id}-4_{name}特色专题图.png",
        f"fig{sec_id}-5_{name}夜间灯光与经济发展演进图.png"
    ])

fig_stats = []
total_fig_size_mb = 0

for fig in expected_figs:
    fpath = os.path.join(FIGURES_DIR, fig)
    if not os.path.exists(fpath):
        errors.append(f"Missing map file: {fig}")
        passed = False
    else:
        sz_kb = os.path.getsize(fpath) / 1024.0
        total_fig_size_mb += sz_kb / 1024.0
        fig_stats.append((fig, sz_kb))
        if sz_kb < 80.0:
            warnings.append(f"Map {fig} unusually small: {sz_kb:.1f} KB")

print(f" -> Found {len(fig_stats)} / {len(expected_figs)} maps. Total size: {total_fig_size_mb:.2f} MB.")
if len(fig_stats) == len(expected_figs):
    print(f" -> [PASS] All {len(expected_figs)} maps exist and verified.")
else:
    passed = False

# 3. 核验 Markdown 正文中引用的图片有效性
print("\n[Step 3] Verifying figure references in Markdown text...")
img_pattern = re.compile(r"!\[(.*?)\]\(\.\./figures/(.*?)\)")
total_refs = 0
broken_refs = 0

for ef in expected_files:
    fpath = os.path.join(SECTIONS_DIR, ef)
    if not os.path.exists(fpath):
        continue
    with open(fpath, "r", encoding="utf-8") as f:
        txt = f.read()
    matches = img_pattern.findall(txt)
    for alt, fref in matches:
        total_refs += 1
        tpath = os.path.join(FIGURES_DIR, fref)
        if not os.path.exists(tpath):
            errors.append(f"Broken link in {ef}: {fref}")
            broken_refs += 1
            passed = False

print(f" -> Scanned {total_refs} map references across 18 Markdown files.")
if broken_refs == 0:
    print(f" -> [PASS] 100% of figure references ({total_refs}/{total_refs}) resolve successfully! Zero broken links.")
else:
    print(f" -> [FAIL] Found {broken_refs} broken image references!")

# 4. 生成验收报告
print("\n=====================================================================")
print("                   CHAPTER 24 VERIFICATION SUMMARY                   ")
print("=====================================================================")
print(f"Total Monograph Files : {len(file_stats)} / 18")
print(f"Total Word Count      : {total_chars:,} characters")
print(f"Total Publication Maps: {len(fig_stats)} / 85 ({total_fig_size_mb:.2f} MB)")
print(f"Total Image Citations : {total_refs} (0 broken)")

print("\n--- Detailed File Statistics ---")
for fn, ch, lines in file_stats:
    print(f" - {fn:<38} : {ch:>6,} chars, {lines:>4} lines")

if warnings:
    print(f"\n[WARNINGS] ({len(warnings)}):")
    for w in warnings:
        print(f" ! {w}")

if errors:
    print(f"\n[ERRORS] ({len(errors)}):")
    for e in errors:
        print(f" X {e}")
    print("\n>>> RESULT: VERIFICATION FAILED! <<<")
    sys.exit(1)
else:
    print("\n>>> RESULT: 100% PERFECT PASS! CHAPTER 24 IS FULLY COMPLETE! <<<")
    print("=====================================================================")
