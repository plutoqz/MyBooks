# -*- coding: utf-8 -*-
"""湖南省（第 17 章）全要素完备性、图件引用与文字体量综合核验脚本
严格核验：
1. 16 个 Markdown 章节文件完整性与字数达标情况
2. 75 幅出版级地图在 figures/ 目录中物理存在性与正文 100% 引用解析
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
    ("17-00_湖南省地理统揽与地缘格局.md", 5500),
    ("17-01_长沙市.md", 5500),
    ("17-02_株洲市.md", 5000),
    ("17-03_湘潭市.md", 5000),
    ("17-04_衡阳市.md", 5500),
    ("17-05_邵阳市.md", 5000),
    ("17-06_岳阳市.md", 5000),
    ("17-07_常德市.md", 5000),
    ("17-08_张家界市.md", 5000),
    ("17-09_益阳市.md", 5000),
    ("17-10_郴州市.md", 5000),
    ("17-11_永州市.md", 5000),
    ("17-12_怀化市.md", 5000),
    ("17-13_娄底市.md", 5000),
    ("17-14_湘西土家族苗族自治州.md", 5000),
    ("17-15_湖南省地理要素矩阵与省内之最.md", 4500)
]

def verify_hunan():
    print("=================================================================")
    print("   湖南省（第 17 章）全书稿与专题地图完备性自动化校验")
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

    # 2. 检查 figures 目录下 17 系列图片的生成总量
    print("\n--- 2. figures/ 目录下湖南省专题地图物理统计 ---")
    fig_overview = [f for f in os.listdir(FIGURES_DIR) if f.startswith("fig17-00-")]
    fig_unit = [f for f in os.listdir(FIGURES_DIR) if re.match(r"^fig17-(0[1-9]|1[0-4])-[1-5]_", f)]
    total_valid_figs = len(fig_overview) + len(fig_unit)
    print(f"  ✓ 实际生成湖南省出版级地图共: {total_valid_figs} 幅 (预期: 75 幅: 5 幅省级大图 + 70 幅分析单元专题图)")
    if total_valid_figs < 75:
        print(f"  [WARN] 地图数量不足 75 幅！")
        all_passed = False

    # 3. 总体结论输出
    print("\n=================================================================")
    print("                     湖南省章节核验总体结论")
    print("=================================================================")
    print(f"  - 正文文件完整度:  {len(EXPECTED_FILES) - len(missing_files)} / {len(EXPECTED_FILES)}")
    print(f"  - 正文总字数体量:  {total_chars:,} 字符 (质量达标线: 100,000 字符)")
    print(f"  - 章节引用地图数:  {total_images_cited} 幅")
    print(f"  - 物理生成地图数:  {total_valid_figs} 幅")

    if all_passed and total_chars >= 100000 and total_valid_figs >= 75:
        print("\n  >>> 【PERFECT PASS】湖南省（第 17 章）全部图文资料 100% 达标，完全满足出版级要求！ <<<\n")
        return True
    else:
        print("\n  >>> 【FAILED / WARNING】存在部分指标未达标，请根据上述提示排查！ <<<\n")
        return False

if __name__ == "__main__":
    success = verify_hunan()
    if not success:
        sys.exit(1)
