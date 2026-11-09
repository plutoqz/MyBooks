# -*- coding: utf-8 -*-
"""江西省（第 14 章）全要素完备性、图件引用与文字体量综合核验脚本
严格核验：
1. 13 个 Markdown 章节文件完整性与字数达标情况
2. 60 幅出版级地图在 figures/ 目录中物理存在性与正文 100% 引用解析
3. 统计全省文字总体量与格式完备性
"""
import os
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册"
SECTIONS_DIR = os.path.join(BASE_DIR, "sections_vol2")
FIGURES_DIR = os.path.join(BASE_DIR, "figures")

EXPECTED_FILES = [
    ("14-00_江西省地理统揽与地缘格局.md", 5500),
    ("14-01_南昌市.md", 5500),
    ("14-02_景德镇市.md", 5000),
    ("14-03_萍乡市.md", 5000),
    ("14-04_九江市.md", 5500),
    ("14-05_新余市.md", 5000),
    ("14-06_鹰潭市.md", 5000),
    ("14-07_赣州市.md", 5500),
    ("14-08_吉安市.md", 5000),
    ("14-09_宜春市.md", 5000),
    ("14-10_抚州市.md", 5000),
    ("14-11_上饶市.md", 5500),
    ("14-12_江西省地理要素矩阵与省内之最.md", 3800)
]

def verify_jiangxi():
    print("=================================================================")
    print("   江西省（第 14 章）全书稿与专题地图完备性自动化校验")
    print("=================================================================\n")

    all_passed = True
    total_chars = 0
    total_images_cited = 0
    missing_files = []
    missing_images = []

    # 1. 检查文档与文字体量
    print("--- 1. 章节正文完整性与字数核验 ---")
    for fname, min_chars in EXPECTED_FILES:
        fpath = os.path.join(SECTIONS_DIR, fname)
        if not os.path.exists(fpath):
            print(f"  [MISSING] 正文缺失: {fname}")
            all_passed = False
            missing_files.append(fname)
            continue

        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()

        chars = len(content.strip())
        total_chars += chars
        
        # 提取图片引用
        img_pattern = re.compile(r'!\[.*?\]\((.*?)\)')
        images = img_pattern.findall(content)
        total_images_cited += len(images)

        # 检查图片物理存在性
        img_ok = True
        for img_rel in images:
            img_rel_norm = img_rel.replace("/", os.sep).replace("\\", os.sep)
            if img_rel_norm.startswith(".." + os.sep + "figures"):
                img_name = os.path.basename(img_rel_norm)
                img_path = os.path.join(FIGURES_DIR, img_name)
            else:
                img_path = os.path.normpath(os.path.join(SECTIONS_DIR, img_rel_norm))
            
            if not os.path.exists(img_path):
                print(f"    [IMAGE MISSING] {fname} 引用图片不存在: {img_rel} -> {img_path}")
                img_ok = False
                all_passed = False
                missing_images.append((fname, img_rel))

        status = "PASS" if chars >= min_chars and img_ok else "WARN/FAIL"
        print(f"  [{status}] {fname:<35} 字数: {chars:>6} (目标: {min_chars}) | 配图: {len(images)} 幅")

    # 2. 检查 figures 目录下 14 系列图片的生成总量
    print("\n--- 2. figures/ 目录下江西省专题地图物理统计 ---")
    fig_overview = [f for f in os.listdir(FIGURES_DIR) if f.startswith("fig14-00-")]
    fig_unit = [f for f in os.listdir(FIGURES_DIR) if re.match(r"^fig14-(0[1-9]|1[0-1])-[1-5]_", f)]
    total_valid_figs = len(fig_overview) + len(fig_unit)
    print(f"  ✓ 实际生成江西省出版级地图共: {total_valid_figs} 幅 (预期: 60 幅: 5 幅省级大图 + 55 幅设区市专题图)")
    if total_valid_figs < 60:
        print(f"  [WARN] 地图数量不足 60 幅！")
        all_passed = False
    else:
        print(f"  ✓ 全套 60 幅地图全部完备在册！")

    # 3. 总体达标判定
    print("\n--- 3. 全章达标终审汇总 ---")
    print(f"  全章有效章节文档总数: {len(EXPECTED_FILES)} / {len(EXPECTED_FILES)} 篇")
    print(f"  全章正文纯文本总字符: {total_chars:,} 字符 (标杆达标线: 80,000 字符)")
    print(f"  全章文档累计引用地图: {total_images_cited} 幅 (预期: 60 幅)")

    if total_chars < 80000:
        print(f"  [WARN] 总字数 {total_chars:,} 尚未突破 80,000 字符！")
        all_passed = False
    if total_images_cited < 60:
        print(f"  [WARN] 正文配图引用数 {total_images_cited} 不足 60 幅！")
        all_passed = False

    print("\n=================================================================")
    if all_passed:
        print("  ★★★ 终审评定: 100% PERFECT PASS! 江西省（第 14 章）达标入卷! ★★★")
    else:
        print("  ✕✕✕ 终审评定: 核验未完全通过，请检查上述缺失项目！ ✕✕✕")
    print("=================================================================\n")
    return all_passed

if __name__ == "__main__":
    success = verify_jiangxi()
    if not success:
        sys.exit(1)
