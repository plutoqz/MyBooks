# -*- coding: utf-8 -*-
"""广东省（第 18 章）全要素完备性、图件引用与文字体量综合核验脚本
严格核验：
1. 23 个 Markdown 章节文件完整性与字数达标情况
2. 110 幅出版级地图在 figures/ 目录中物理存在性与正文 100% 引用解析
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
    ("18-00_广东省地理统揽与地缘格局.md", 6000),
    ("18-01_广州市.md", 5500),
    ("18-02_韶关市.md", 5000),
    ("18-03_深圳市.md", 5500),
    ("18-04_珠海市.md", 5000),
    ("18-05_汕头市.md", 5000),
    ("18-06_佛山市.md", 5000),
    ("18-07_江门市.md", 5000),
    ("18-08_湛江市.md", 5000),
    ("18-09_茂名市.md", 5000),
    ("18-10_肇庆市.md", 5000),
    ("18-11_惠州市.md", 5000),
    ("18-12_梅州市.md", 5000),
    ("18-13_汕尾市.md", 5000),
    ("18-14_河源市.md", 5000),
    ("18-15_阳江市.md", 5000),
    ("18-16_清远市.md", 5000),
    ("18-17_东莞市.md", 5000),
    ("18-18_中山市.md", 5000),
    ("18-19_潮州市.md", 5000),
    ("18-20_揭阳市.md", 5000),
    ("18-21_云浮市.md", 5000),
    ("18-22_广东省地理要素矩阵与省内之最.md", 5000)
]

def verify_guangdong():
    print("=================================================================")
    print("   广东省（第 18 章）全书稿与专题地图完备性自动化校验")
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

    # 2. 检查 figures 目录下 18 系列图片的生成总量
    print("\n--- 2. figures/ 目录下广东省专题地图物理统计 ---")
    fig_overview = [f for f in os.listdir(FIGURES_DIR) if f.startswith("fig18-00-")]
    fig_unit = [f for f in os.listdir(FIGURES_DIR) if re.match(r"^fig18-(0[1-9]|1[0-9]|2[0-1])-[1-5]_", f)]
    total_valid_figs = len(fig_overview) + len(fig_unit)
    print(f"  ✓ 实际生成广东省出版级地图共: {total_valid_figs} 幅 (预期: 110 幅: 5 幅省级大图 + 105 幅分析单元专题图)")
    if total_valid_figs < 110:
        print(f"  [WARN] 地图数量不足 110 幅！")
        all_passed = False

    # 3. 总体结论输出
    print("\n=================================================================")
    print("                     广东省（第 18 章）核验汇总")
    print("=================================================================")
    print(f"  * 专著章节总数: {len(EXPECTED_FILES)} 篇全部在册 (缺失: {len(missing_files)})")
    print(f"  * 正文总字数:   {total_chars:,} 字符 (目标: >= 150,000 字符)")
    print(f"  * 文中标注配图: {total_images_cited} 幅 (失效引用: {len(missing_images)})")
    print(f"  * 磁盘实体地图: {total_valid_figs} 幅 (覆盖率: {total_valid_figs/110*100:.1f}%)")
    print("-----------------------------------------------------------------")
    
    if all_passed and total_chars >= 150000 and total_valid_figs == 110 and len(missing_images) == 0:
        print("  >>> 【100% PERFECT PASS】广东省全章内容编撰与地图工程高质量达标！<<<")
    else:
        print("  >>> 【ATTENTION REQUIRED】核验未完全通过，请核对上述告警信息！<<<")
    print("=================================================================\n")

if __name__ == "__main__":
    verify_guangdong()
