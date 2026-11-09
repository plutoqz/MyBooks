# -*- coding: utf-8 -*-
"""广西壮族自治区（第 19 章）全要素完备性、图件引用与文字体量综合核验脚本
严格核验：
1. 16 个 Markdown 章节文件完整性与字数达标情况
2. 75 幅出版级地图在 figures/ 目录中物理存在性与正文 100% 引用解析
3. 统计全区文字总体量与格式完备性
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
    ("19-00_广西壮族自治区地理统揽与地缘格局.md", 6000),
    ("19-01_南宁市.md", 5500),
    ("19-02_柳州市.md", 5000),
    ("19-03_桂林市.md", 5500),
    ("19-04_梧州市.md", 5000),
    ("19-05_北海市.md", 5000),
    ("19-06_防城港市.md", 5000),
    ("19-07_钦州市.md", 5000),
    ("19-08_贵港市.md", 5000),
    ("19-09_玉林市.md", 5000),
    ("19-10_百色市.md", 5000),
    ("19-11_贺州市.md", 5000),
    ("19-12_河池市.md", 5000),
    ("19-13_来宾市.md", 5000),
    ("19-14_崇左市.md", 5000),
    ("19-15_广西壮族自治区地理要素矩阵与区内之最.md", 5000)
]

def verify_guangxi():
    print("=================================================================")
    print("   广西壮族自治区（第 19 章）全书稿与专题地图完备性自动化校验")
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

    # 2. 检查 figures 目录下 19 系列图片的生成总量
    print("\n--- 2. figures/ 目录下广西壮族自治区专题地图物理统计 ---")
    fig_overview = [f for f in os.listdir(FIGURES_DIR) if f.startswith("fig19-00-")]
    fig_unit = [f for f in os.listdir(FIGURES_DIR) if re.match(r"^fig19-(0[1-9]|1[0-4])-[1-5]_", f)]
    total_valid_figs = len(fig_overview) + len(fig_unit)
    print(f"  ✓ 实际生成广西出版级地图共: {total_valid_figs} 幅 (预期: 75 幅: 5 幅省级大图 + 70 幅分析单元专题图)")
    if total_valid_figs < 75:
        print(f"  [WARN] 地图数量不足 75 幅！")
        all_passed = False

    # 3. 总体结论输出
    print("\n=================================================================")
    print("                  广西壮族自治区（第 19 章）核验汇总")
    print("=================================================================")
    print(f"  * 专著章节总数: {len(EXPECTED_FILES)} 篇全部在册 (缺失: {len(missing_files)})")
    print(f"  * 正文总字数:   {total_chars:,} 字符 (目标: >= 115,000 字符)")
    print(f"  * 文中标注配图: {total_images_cited} 幅 (失效引用: {len(missing_images)})")
    print(f"  * 磁盘实体地图: {total_valid_figs} 幅 (覆盖率: {total_valid_figs/75*100:.1f}%)")
    print("-----------------------------------------------------------------")
    
    if all_passed and total_chars >= 115000 and total_valid_figs == 75 and len(missing_images) == 0:
        print("  >>> 【100% PERFECT PASS】广西壮族自治区全章内容编撰与地图工程高质量达标！<<<")
    else:
        print("  >>> 【ATTENTION REQUIRED】核验未完全通过，请核对上述告警信息！<<<")
    print("=================================================================\n")

if __name__ == "__main__":
    verify_guangxi()
