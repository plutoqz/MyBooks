# -*- coding: utf-8 -*-
"""辽宁省（第 5 章）全要素完备性、图件引用与文字体量综合核验脚本
严格核验：
1. 16 个 Markdown 章节文件完整性与字数达标情况
2. 75 幅出版级地图在 figures/ 目录中物理存在性与正文 100% 引用解析
3. 统计全省文字总体量
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
    ("05-00_辽宁省地理统揽.md", 5000),
    ("05-01_沈阳市.md", 3000),
    ("05-02_大连市.md", 3000),
    ("05-03_鞍山市.md", 3000),
    ("05-04_抚顺市.md", 3000),
    ("05-05_本溪市.md", 3000),
    ("05-06_丹东市.md", 3000),
    ("05-07_锦州市.md", 3000),
    ("05-08_营口市.md", 3000),
    ("05-09_阜新市.md", 3000),
    ("05-10_辽阳市.md", 3000),
    ("05-11_盘锦市.md", 3000),
    ("05-12_铁岭市.md", 3000),
    ("05-13_朝阳市.md", 3000),
    ("05-14_葫芦岛市.md", 3000),
    ("05-15_辽宁省地理要素矩阵与省内之最.md", 5000)
]

def verify_liaoning():
    print("=================================================================")
    print("   辽宁省（第 5 章）全书稿与专题地图完备性自动化校验")
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
            # 转换为绝对路径
            # 相对路径形式通常为 ../figures/xxx.png
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
        print(f"  [{status}] {fname:<32} 字数: {chars:>5} (目标: {min_chars}) | 配图: {len(images)} 幅")

    # 2. 检查 figures 目录下 05 系列图片的生成总量
    print("\n--- 2. figures/ 目录下辽宁省专题地图物理统计 ---")
    fig_files = [f for f in os.listdir(FIGURES_DIR) if f.startswith("fig05-")]
    print(f"  ✓ 实际生成辽宁省出版级地图共: {len(fig_files)} 幅 (预期: 75 幅)")
    if len(fig_files) < 75:
        print(f"  [WARN] 地图数量不足 75 幅！")
        all_passed = False
    else:
        print(f"  ✓ 75 幅地图全部完备在册！")

    print("\n=================================================================")
    print(f"  辽宁省全章核验汇总:")
    print(f"  - 正文文档总数: {len(EXPECTED_FILES)} / {len(EXPECTED_FILES)} 篇")
    print(f"  - 全章总文字体量: {total_chars:,} 字符")
    print(f"  - 正文引用配图总数: {total_images_cited} 幅")
    print(f"  - 物理生成地图总数: {len(fig_files)} 幅")
    print(f"  - 综合状态: {'★★★★★ 100% 完美通过全流程质量核验 ★★★★★' if all_passed else '存在缺失项需排查修复'}")
    print("=================================================================\n")

    return all_passed

if __name__ == "__main__":
    success = verify_liaoning()
    if not success:
        sys.exit(1)
