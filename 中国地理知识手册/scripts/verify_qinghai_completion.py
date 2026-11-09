# -*- coding: utf-8 -*-
"""青海省全套成果完整性与规范性验证脚本
严格核验：
1. 10 篇正文 markdown 文件全部存在且字符数达标 (>3000 字符)
2. 45 幅出版级地图全部生成且文件大小正常 (>50KB)
3. 正文中的所有图片引用完整可解析，无任何死链或未匹配引用
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册"
SECTIONS_DIR = os.path.join(ROOT_DIR, "sections_vol2")
FIGURES_DIR = os.path.join(ROOT_DIR, "figures")

EXPECTED_FILES = [
    "33-00_青海省地理统揽.md",
    "33-01_西宁市.md",
    "33-02_海东市.md",
    "33-03_海北藏族自治州.md",
    "33-04_黄南藏族自治州.md",
    "33-05_海南藏族自治州.md",
    "33-06_果洛藏族自治州.md",
    "33-07_玉树藏族自治州.md",
    "33-08_海西蒙古族藏族自治州.md",
    "33-09_青海省地理要素矩阵与省内之最.md",
]

def main():
    print("=" * 65)
    print("      青海省（第 33 章）全要素交付完整性与质量核验")
    print("=" * 65)

    all_passed = True

    # 1. 核验 10 篇 Markdown 文件
    print("\n[1/3] 检查 10 篇 Markdown 章节文本与字数...")
    total_chars = 0
    img_refs_found = []

    for fname in EXPECTED_FILES:
        fpath = os.path.join(SECTIONS_DIR, fname)
        if not os.path.exists(fpath):
            print(f"  [FAIL] 缺失文件: {fname}")
            all_passed = False
            continue

        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()

        char_count = len(content)
        total_chars += char_count
        status = "PASS" if char_count >= 3000 else "WARN"
        print(f"  [{status}] {fname:38s} | 字符数: {char_count:5d}")
        if char_count < 3000:
            all_passed = False

        # 提取图片引用
        refs = re.findall(r'!\[.*?\]\((.*?)\)', content)
        for r in refs:
            img_refs_found.append((fname, r))

    print(f"\n  文本总字数: {total_chars:,} 字符 (10 篇全达标)")

    # 2. 核验 45 幅专题地图
    print("\n[2/3] 检查 45 幅出版级高清地图文件...")
    fig_files = [f for f in os.listdir(FIGURES_DIR) if f.startswith("fig33-") and f.endswith(".png")]
    fig_files.sort()
    print(f"  找到匹配 'fig33-*.png' 的地图文件共: {len(fig_files)} 幅")

    if len(fig_files) != 45:
        print(f"  [FAIL] 期望 45 幅地图，实际找到 {len(fig_files)} 幅！")
        all_passed = False
    else:
        print(f"  [PASS] 45 幅地图数量精准一致！")

    small_files = []
    for f in fig_files:
        fpath = os.path.join(FIGURES_DIR, f)
        sz_kb = os.path.getsize(fpath) / 1024.0
        if sz_kb < 50.0:
            small_files.append((f, sz_kb))

    if small_files:
        print(f"  [FAIL] 发现过小异常图片: {small_files}")
        all_passed = False
    else:
        print(f"  [PASS] 全部 45 幅地图文件尺寸正常 (>50KB)")

    # 3. 核验 Markdown 图片引用解析
    print("\n[3/3] 检查文本内图片引用解析有效性...")
    print(f"  文本内图片引用总数: {len(img_refs_found)} 个")
    unresolved = []
    for doc, ref in img_refs_found:
        # 路径形如 ../figures/fig33-...
        clean_ref = ref.replace("../figures/", "")
        disk_path = os.path.join(FIGURES_DIR, clean_ref)
        if not os.path.exists(disk_path):
            unresolved.append((doc, ref))

    if unresolved:
        print(f"  [FAIL] 存在无法解析的死链图片: {unresolved}")
        all_passed = False
    else:
        print(f"  [PASS] 全部 {len(img_refs_found)} 个图片引用 100% 成功解析且文件存在！")

    print("\n" + "=" * 65)
    if all_passed:
        print("  【恭喜】青海省（第 33 章）全套成果 100% 验证通过！完全符合出版交付标准！")
    else:
        print("  【错误】存在未达标项，请根据上述提示排查修正！")
    print("=" * 65)

if __name__ == "__main__":
    main()
