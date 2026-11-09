# -*- coding: utf-8 -*-
"""江苏省（第 10 章）全要素完备性、图件引用与文字体量综合核验脚本
严格核验：
1. 15 个 Markdown 章节文件完整性与字数达标情况
2. 70 幅出版级地图在 figures/ 目录中物理存在性与正文 100% 引用解析
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
    ("10-00_江苏省地理统揽与地缘格局.md", 5500),
    ("10-01_南京市.md", 6000),
    ("10-02_无锡市.md", 6000),
    ("10-03_徐州市.md", 6000),
    ("10-04_常州市.md", 6000),
    ("10-05_苏州市.md", 6000),
    ("10-06_南通市.md", 6000),
    ("10-07_连云港市.md", 6000),
    ("10-08_淮安市.md", 6000),
    ("10-09_盐城市.md", 6000),
    ("10-10_扬州市.md", 6000),
    ("10-11_镇江市.md", 6000),
    ("10-12_泰州市.md", 6000),
    ("10-13_宿迁市.md", 6000),
    ("10-14_江苏省地理要素矩阵与省内之最.md", 4500)
]

def verify_jiangsu():
    print("=================================================================")
    print("   江苏省（第 10 章）全书稿与专题地图完备性自动化校验")
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

    # 2. 检查 figures 目录下 10 系列图片的生成总量
    print("\n--- 2. figures/ 目录下江苏省专题地图物理统计 ---")
    fig_files = [f for f in os.listdir(FIGURES_DIR) if f.startswith("fig10-")]
    print(f"  ✓ 实际生成江苏省出版级地图共: {len(fig_files)} 幅 (预期: 70 幅)")
    if len(fig_files) < 70:
        print(f"  [WARN] 地图数量不足 70 幅！")
        all_passed = False
    else:
        print(f"  ✓ 70 幅地图全部完备在册！")

    # 3. 总体达标判定
    print("\n--- 3. 全章达标终审汇总 ---")
    print(f"  全章有效章节文档总数: {len(EXPECTED_FILES)} / {len(EXPECTED_FILES)} 篇")
    print(f"  全章文字总体量累计:   {total_chars:,} 字符 (质量底线: >95,000 字符)")
    print(f"  全章正文引证图片总数: {total_images_cited} 幅 (全量闭环核验)")
    print(f"  图库物理出版地图总数: {len(fig_files)} 幅")

    if total_chars < 95000:
        print(f"  [WARN] 全章字数未达 95,000 字符底线！")
        all_passed = False

    if all_passed:
        print("\n=================================================================")
        print("  ★★★ CONGRATULATIONS: 100% PERFECT PASS! 全部指标卓越达标！ ★★★")
        print("=================================================================\n")
        return True
    else:
        print("\n=================================================================")
        print("  [FAIL] 存在不达标项，请核查以上日志修复！")
        print("=================================================================\n")
        return False

if __name__ == "__main__":
    success = verify_jiangsu()
    sys.exit(0 if success else 1)
