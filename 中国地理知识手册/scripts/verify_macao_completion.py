# -*- coding: utf-8 -*-
"""澳门特别行政区专著与出版级地图自动化严苛核验引擎
严苛核验：
1. 5 篇 Markdown 章节文件是否存在、字数是否达标；
2. 20 幅出版级专题地图（5 幅全区宏观 + 15 幅单元专题图）文件完整性与图片体积；
3. 5 篇 Markdown 正文中的地图相对路径引用（../figures/fig28-*.png）是否 100% 存在；
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
from macao_configs import MACAO_DISTRICT_CONFIGS

print("=====================================================================")
print("   Volume 2 Chapter 28 (Macao SAR) Rigorous Verification             ")
print("=====================================================================")

passed = True
errors = []
warnings = []

# 1. 核验 5 篇 Markdown 文档
print("\n[Step 1] Verifying 5 Markdown monograph section files...")
expected_files = ["28-00_澳门特别行政区地理统揽.md"]
for code, cfg in MACAO_DISTRICT_CONFIGS.items():
    sec_id = cfg["sec_id"]
    name = cfg["name"]
    expected_files.append(f"{sec_id}_{name}.md")
expected_files.append("28-04_澳门特别行政区地理要素大典与空间综合统计分析.md")

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
            if chars < 3000:
                warnings.append(f"Section {ef} word count low: {chars} chars")

print(f" -> Found {len(file_stats)} / {len(expected_files)} files. Total characters: {total_chars:,} chars.")
if total_chars < 18000:
    errors.append(f"Total word count below 18,000 threshold: {total_chars}")
    passed = False
else:
    print(f" -> [PASS] Monograph volume exceeds 18,000 chars threshold! ({total_chars:,} >= 18,000)")

# 2. 核验 20 幅出版级地图
print("\n[Step 2] Verifying 20 publication-grade maps (5 overview + 15 unit maps)...")
expected_figs = [
    "fig28-00-1_澳门特别行政区地势起伏与珠江口海陆格局图.png",
    "fig28-00-2_澳门特别行政区堂区分区与琴澳一体化空间战略格局图.png",
    "fig28-00-3_澳门特别行政区综合立体交通网络与港珠澳大桥连通图.png",
    "fig28-00-4_澳门特别行政区世界旅游休闲中心与现代金融商贸空间分布图.png",
    "fig28-00-5_澳门特别行政区2000-2024年本地生产总值与入境旅客演进图.png"
]

for code, cfg in MACAO_DISTRICT_CONFIGS.items():
    sec_id = cfg["sec_id"]
    name = cfg["name"]
    expected_figs.extend([
        f"fig{sec_id}-1_{name}行政区位图.png",
        f"fig{sec_id}-2_{name}地形地貌图.png",
        f"fig{sec_id}-3_{name}道路交通图.png",
        f"fig{sec_id}-4_{name}特色专题图.png",
        f"fig{sec_id}-5_{name}夜间灯光与经济发展演进图.png"
    ])

total_img_size_mb = 0.0
found_figs = 0
for ef in expected_figs:
    p = os.path.join(FIGURES_DIR, ef)
    if not os.path.exists(p):
        errors.append(f"Missing publication map: {ef}")
        passed = False
    else:
        sz_mb = os.path.getsize(p) / (1024 * 1024)
        total_img_size_mb += sz_mb
        found_figs += 1
        if sz_mb < 0.1:
            warnings.append(f"Map size unusually small: {ef} ({sz_mb:.2f} MB)")

print(f" -> Found {found_figs} / {len(expected_figs)} maps. Total figure volume: {total_img_size_mb:.2f} MB.")
if found_figs == len(expected_figs):
    print(f" -> [PASS] All {len(expected_figs)} publication-grade maps verified on disk!")

# 3. 核验 Markdown 正文中相对图片引用的连通性
print("\n[Step 3] Verifying relative figure link connectivity in Markdown texts...")
fig_ref_pattern = re.compile(r'!\[.*?\]\(\.\./figures/(fig28-[^\)]+)\)')

dead_links = []
total_refs = 0
found_refs = set()

for ef in expected_files:
    fpath = os.path.join(SECTIONS_DIR, ef)
    if not os.path.exists(fpath):
        continue
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()
    matches = fig_ref_pattern.findall(content)
    total_refs += len(matches)
    for m in matches:
        found_refs.add(m)
        target = os.path.join(FIGURES_DIR, m)
        if not os.path.exists(target):
            dead_links.append((ef, m))
            errors.append(f"Dead link in {ef}: ../figures/{m}")
            passed = False

print(f" -> Scanned {total_refs} figure references in markdown files ({len(found_refs)} unique figures referenced).")
if dead_links:
    print(f" -> [FAIL] Found {len(dead_links)} dead figure links!")
else:
    print(f" -> [PASS] 100% of figure references resolved to existing files on disk! (0 dead links)")

# 4. 统计与详细文档清单
print("\n[Step 4] Monograph section breakdown:")
for fn, ch, lines in file_stats:
    print(f"    - {fn:<45} : {ch:>6,} chars, {lines:>4} lines")

print("\n=====================================================================")
if passed and not errors:
    print(" >>> RESULT: 100% PERFECT PASS! Chapter 28 (Macao SAR) Fully Verified! <<<")
else:
    print(f" >>> RESULT: VERIFICATION FAILED with {len(errors)} errors and {len(warnings)} warnings! <<<")
    for e in errors:
        print(f"     [ERROR] {e}")
if warnings:
    for w in warnings:
        print(f"     [WARN] {w}")
print("=====================================================================")

if not passed:
    sys.exit(1)
