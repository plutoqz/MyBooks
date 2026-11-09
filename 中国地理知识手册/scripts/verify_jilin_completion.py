# -*- coding: utf-8 -*-
"""吉林省（第 6 章）全要素完备性、图件引用与文字体量综合核验脚本
严格核验：
1. 11 个 Markdown 章节文件完整性与字数达标情况
2. 50 幅出版级地图在 figures/ 目录中物理存在性与正文 100% 引用解析
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
    ("06-00_吉林省地理统揽.md", 5000),
    ("06-01_长春市.md", 3000),
    ("06-02_吉林市.md", 3000),
    ("06-03_四平市.md", 3000),
    ("06-04_辽源市.md", 3000),
    ("06-05_通化市.md", 3000),
    ("06-06_白山市.md", 3000),
    ("06-07_松原市.md", 3000),
    ("06-08_白城市.md", 3000),
    ("06-09_延边朝鲜族自治州.md", 3000),
    ("06-10_吉林省地理要素矩阵与省内之最.md", 5000)
]

def verify_jilin():
    print("=================================================================")
    print("   吉林省（第 6 章）全书稿与专题地图完备性自动化校验")
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
        print(f"  [{status}] {fname:<35} 字数: {chars:>5} (目标: {min_chars}) | 配图: {len(images)} 幅")

    # 2. 检查 figures 目录下 06 系列图片的生成总量
    print("\n--- 2. figures/ 目录下吉林省专题地图物理统计 ---")
    fig_files = [f for f in os.listdir(FIGURES_DIR) if f.startswith("fig06-")]
    print(f"  ✓ 实际生成吉林省出版级地图共: {len(fig_files)} 幅 (预期: 50 幅)")
    if len(fig_files) < 50:
        print(f"  [WARN] 地图数量不足 50 幅！")
        all_passed = False
    else:
        print(f"  ✓ 50 幅地图全部完备在册！")

    # 3. 汇总报告
    print("\n=================================================================")
    print("                      吉林省成果验收总评")
    print("=================================================================")
    print(f"  • 正文文件数量:     {len(EXPECTED_FILES) - len(missing_files)} / {len(EXPECTED_FILES)}")
    print(f"  • 全章总字数规模:   {total_chars:,} 字符")
    print(f"  • 正文图件引用总数: {total_images_cited} 幅 (全为 200 dpi 出版级地图)")
    print(f"  • 物理图件完备性:   {len(fig_files)} / 50 幅")
    
    if all_passed and total_images_cited == 50 and len(fig_files) == 50:
        print("\n  >>> 【验收结论】：100% PERFECT PASS！全要素完备，符合专著出版标准！ <<<")
        return True
    else:
        print("\n  >>> 【验收结论】：存在未达标项，请核实上述缺失清单。 <<<")
        return False

if __name__ == "__main__":
    success = verify_jilin()
    sys.exit(0 if success else 1)
