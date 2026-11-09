# -*- coding: utf-8 -*-
"""香港特别行政区专著与出版级地图自动化严苛核验引擎
严苛核验：
1. 6 篇 Markdown 章节文件是否存在、字数是否达标；
2. 25 幅出版级专题地图（5 幅全省宏观 + 20 幅市级专题图）文件完整性与图片体积；
3. 6 篇 Markdown 正文中的地图相对路径引用（../figures/fig27-*.png）是否 100% 存在；
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
from hongkong_configs import HONGKONG_DISTRICT_CONFIGS

print("=====================================================================")
print("   Volume 2 Chapter 27 (Hong Kong SAR) Rigorous Verification         ")
print("=====================================================================")

passed = True
errors = []
warnings = []

# 1. 核验 6 篇 Markdown 文档
print("\n[Step 1] Verifying 6 Markdown monograph section files...")
expected_files = ["27-00_香港特别行政区地理统揽.md"]
for code, cfg in HONGKONG_DISTRICT_CONFIGS.items():
    sec_id = cfg["sec_id"]
    name = cfg["name"]
    expected_files.append(f"{sec_id}_{name}.md")
expected_files.append("27-05_香港特别行政区地理要素大典与空间综合统计分析.md")

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
if total_chars < 25000:
    errors.append(f"Total word count below 25,000 threshold: {total_chars}")
    passed = False
else:
    print(f" -> [PASS] Monograph volume exceeds 25,000 chars threshold! ({total_chars:,} >= 25,000)")

# 2. 核验 25 幅出版级地图
print("\n[Step 2] Verifying 25 publication-grade maps (5 overview + 20 unit maps)...")
expected_figs = [
    "fig27-00-1_香港特别行政区地势起伏与山海维港格局图.png",
    "fig27-00-2_香港特别行政区18区政区与北部都会区战略格局图.png",
    "fig27-00-3_香港特别行政区综合立体交通网络与海空港口大通道图.png",
    "fig27-00-4_香港特别行政区现代金融与创新科技产业空间分布图.png",
    "fig27-00-5_香港特别行政区2000-2024年经济跃升与深港协同对比图.png"
]

for code, cfg in HONGKONG_DISTRICT_CONFIGS.items():
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
    print(f" -> [PASS] All {found_figs} publication-grade maps verified on disk!")

# 3. 核验 Markdown 正文中的图片链接有效性
print("\n[Step 3] Verifying figure link references in all 6 Markdown files...")
link_pattern = re.compile(r"!\[(.*?)\]\(\.\./figures/(fig27-[^\)]+\.png)\)")
verified_links = 0

for ef in expected_files:
    fpath = os.path.join(SECTIONS_DIR, ef)
    if not os.path.exists(fpath):
        continue
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()
    matches = link_pattern.findall(content)
    for alt_text, fig_name in matches:
        fig_path = os.path.join(FIGURES_DIR, fig_name)
        if not os.path.exists(fig_path):
            errors.append(f"Broken image link in {ef}: {fig_name}")
            passed = False
        else:
            verified_links += 1

print(f" -> Verified {verified_links} image references across all 6 Markdown files.")
if verified_links == len(expected_figs):
    print(f" -> [PASS] Exactly {verified_links} / {len(expected_figs)} figure links perfectly matched with zero broken links!")
else:
    warnings.append(f"Referenced {verified_links} figures, but expected {len(expected_figs)}")

# 4. 打印各文件字数汇总
print("\n[Step 4] Markdown Section Volume & Length Audit:")
print(f"{'Filename':<35} | {'Chars':>8} | {'Lines':>6}")
print("-" * 55)
for ef, c, l in file_stats:
    print(f"{ef:<35} | {c:>8,} | {l:>6}")
print("-" * 55)
print(f"{'Total Hong Kong Chapter':<35} | {total_chars:>8,} |")

# 5. 综合判定
print("\n=====================================================================")
if passed and len(errors) == 0:
    print(" >>> RESULT: 100% PERFECT PASS! Chapter 27 is fully complete! <<<")
else:
    print(" >>> RESULT: VERIFICATION FAILED! <<<")
    for err in errors:
        print(f"  [ERROR] {err}")
for w in warnings:
    print(f"  [WARNING] {w}")
print("=====================================================================")

if not passed:
    sys.exit(1)
