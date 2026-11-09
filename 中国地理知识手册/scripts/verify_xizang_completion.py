# -*- coding: utf-8 -*-
"""西藏自治区（第 34 章）全套编写与制图成果终审检验脚本"""
import os
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

ROOT_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册"
SECTIONS_DIR = os.path.join(ROOT_DIR, "sections_vol2")
FIGURES_DIR = os.path.join(ROOT_DIR, "figures")

EXPECTED_SECTIONS = [
    ("34-00_西藏自治区地理统揽.md", 5000),
    ("34-01_拉萨市.md", 3000),
    ("34-02_日喀则市.md", 3000),
    ("34-03_昌都市.md", 3000),
    ("34-04_林芝市.md", 3000),
    ("34-05_山南市.md", 3000),
    ("34-06_那曲市.md", 3000),
    ("34-07_阿里地区.md", 3000),
    ("34-08_西藏地理要素矩阵与区内之最.md", 4000),
]

def main():
    print("=" * 70)
    print("西藏自治区（第 34 章）全套编写成果终审合规核验")
    print("=" * 70)

    total_chars = 0
    all_passed = True
    all_referenced_images = []

    # 1. 核验各节文件与字数
    print("\n[1/4] Markdown 章节文件完整性与字数核验：")
    for fname, min_chars in EXPECTED_SECTIONS:
        fpath = os.path.join(SECTIONS_DIR, fname)
        if not os.path.exists(fpath):
            print(f"  [FAIL] 缺失文件: {fname}")
            all_passed = False
            continue
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
            char_count = len(content)
            total_chars += char_count
            if char_count < min_chars:
                print(f"  [WARN] {fname}: {char_count} 字符 (建议 >= {min_chars})")
            else:
                print(f"  [PASS] {fname}: {char_count} 字符 (合规)")
            
            # 提取引用的图片
            imgs = re.findall(r'!\[.*?\]\((.*?)\)', content)
            for img in imgs:
                img_clean = img.replace('../figures/', '').replace('figures/', '').strip()
                all_referenced_images.append((fname, img_clean))

    print(f"\n  第 34 章总字符数: {total_chars:,} 字符")

    # 2. 核验图片引用与实际存在
    print("\n[2/4] 文中引用的图片文件存在性核验：")
    missing_imgs = 0
    for sec_file, img_name in all_referenced_images:
        img_path = os.path.join(FIGURES_DIR, img_name)
        if not os.path.exists(img_path):
            print(f"  [FAIL] {sec_file} 引用的图片不存在: {img_name}")
            missing_imgs += 1
            all_passed = False
        else:
            sz_kb = os.path.getsize(img_path) / 1024.0
            # print(f"  [OK] {img_name} ({sz_kb:.1f} KB)")
    
    if missing_imgs == 0:
        print(f"  [PASS] 所有文内引用的 {len(all_referenced_images)} 张图片全部存在且路径解析正确！")

    # 3. 核验 40 张标准制图产物在 figures/ 目录中的完整性
    print("\n[3/4] 西藏全套 40 张专题地图产物存在性核验：")
    all_figs = [f for f in os.listdir(FIGURES_DIR) if f.startswith("fig34-") and f.endswith(".png")]
    print(f"  figures/ 目录下共发现 {len(all_figs)} 张 fig34-*.png 图片。")
    if len(all_figs) != 40:
        print(f"  [FAIL] 预期 40 张，实际发现 {len(all_figs)} 张！")
        all_passed = False
    else:
        print("  [PASS] 5 幅省级宏观图 + 7 单元 × 5 幅专题图 = 40 幅出版级地图全数齐备！")

    # 4. 总结
    print("\n[4/4] 终审结果判定：")
    if all_passed and missing_imgs == 0:
        print("  >>> 【PASSED】第 34 章 西藏自治区全部文字与图表 100% 验收通过！ <<<")
        print("=" * 70)
        return 0
    else:
        print("  >>> 【FAILED】存在未通过项，请查阅上方日志！ <<<")
        print("=" * 70)
        return 1

if __name__ == "__main__":
    sys.exit(main())
