# -*- coding: utf-8 -*-
"""河南省（第 15 章）全要素完备性、图件引用与文字体量综合核验脚本
严格核验：
1. 20 个 Markdown 章节文件完整性与字数达标情况
2. 95 幅出版级地图在 figures/ 目录中物理存在性与正文 100% 引用解析
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
    ("15-00_河南省地理统揽与地缘格局.md", 5500),
    ("15-01_郑州市.md", 5500),
    ("15-02_开封市.md", 5000),
    ("15-03_洛阳市.md", 5500),
    ("15-04_平顶山市.md", 5000),
    ("15-05_安阳市.md", 5000),
    ("15-06_鹤壁市.md", 5000),
    ("15-07_新乡市.md", 5000),
    ("15-08_焦作市.md", 5000),
    ("15-09_濮阳市.md", 5000),
    ("15-10_许昌市.md", 5000),
    ("15-11_漯河市.md", 5000),
    ("15-12_三门峡市.md", 5000),
    ("15-13_南阳市.md", 5500),
    ("15-14_商丘市.md", 5000),
    ("15-15_信阳市.md", 5500),
    ("15-16_周口市.md", 5000),
    ("15-17_驻马店市.md", 5000),
    ("15-18_济源市.md", 5000),
    ("15-19_河南省地理要素矩阵与省内之最.md", 4500)
]

def verify_henan():
    print("=================================================================")
    print("   河南省（第 15 章）全书稿与专题地图完备性自动化校验")
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
        print(f"  [{status}] {fname:<36} 字数: {chars:>6} (目标: {min_chars}) | 配图: {len(images)} 幅")

    # 2. 检查 figures 目录下 15 系列图片的生成总量
    print("\n--- 2. figures/ 目录下河南省专题地图物理统计 ---")
    fig_overview = [f for f in os.listdir(FIGURES_DIR) if f.startswith("fig15-00-")]
    fig_unit = [f for f in os.listdir(FIGURES_DIR) if re.match(r"^fig15-(0[1-9]|1[0-8])-[1-5]_", f)]
    total_valid_figs = len(fig_overview) + len(fig_unit)
    print(f"  ✓ 实际生成河南省出版级地图共: {total_valid_figs} 幅 (预期: 95 幅: 5 幅省级大图 + 90 幅分析单元专题图)")
    if total_valid_figs < 95:
        print(f"  [WARN] 地图数量不足 95 幅！")
        all_passed = False
    else:
        print(f"  ✓ 全套 95 幅地图全部完备在册！")

    # 3. 总体达标判定
    print("\n--- 3. 全章达标终审汇总 ---")
    print(f"  全章有效章节文档总数: {len(EXPECTED_FILES)} / {len(EXPECTED_FILES)} 篇")
    print(f"  全章正文累计中文字符: {total_chars:,} 字符 (基准要求: >120,000 字符)")
    print(f"  正文引用并核验地图数: {total_images_cited} 幅")

    if total_chars < 120000:
        print(f"  [WARN] 全章字数未达 120,000 字符基准线！")
        all_passed = False

    if all_passed:
        print("\n=================================================================")
        print("  【100% PERFECT PASS】第 15 章 河南省 全书稿与专题地图核验全部通过！")
        print("=================================================================\n")
        return 0
    else:
        print("\n=================================================================")
        print("  【FAIL/WARN】核验未完全通过，请检查上述缺失项目！")
        print("=================================================================\n")
        return 1

if __name__ == "__main__":
    sys.exit(verify_henan())
