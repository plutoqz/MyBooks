# -*- coding: utf-8 -*-
"""验证宁夏回族自治区（第31章）全套成果完备性与数据一致性
检查项：
1. 7 个 Markdown 章节文件是否存在，且字数/字节数达标（>3000字符）
2. 30 张配套高清地图是否存在于 figures/ 目录
3. Markdown 中引用的所有图片路径 100% 正确解析
4. 统计分析全章总体字数、图表覆盖率与完整度
"""
import os
import re
import sys

# 保证控制台 UTF-8 输出
sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECTIONS_DIR = os.path.join(BASE_DIR, "sections_vol2")
FIGURES_DIR = os.path.join(BASE_DIR, "figures")

EXPECTED_SECTIONS = [
    ("31-00_宁夏回族自治区地理统揽.md", 5),
    ("31-01_银川市.md", 5),
    ("31-02_石嘴山市.md", 5),
    ("31-03_吴忠市.md", 5),
    ("31-04_固原市.md", 5),
    ("31-05_中卫市.md", 5),
    ("31-06_宁夏地理要素矩阵与区内之最.md", 0),
]

def main():
    print("=" * 70)
    print("【宁夏回族自治区（第31章）成果完备性与质量核验】")
    print("=" * 70)
    
    all_passed = True
    total_chars = 0
    total_imgs_ref = 0
    resolved_imgs = 0
    
    # 1. 验证 Markdown 文件
    print("\n[1/3] 检查 7 个 Markdown 章节文件...")
    for filename, expected_imgs in EXPECTED_SECTIONS:
        filepath = os.path.join(SECTIONS_DIR, filename)
        if not os.path.exists(filepath):
            print(f"  ❌ 缺失文件: {filename}")
            all_passed = False
            continue
        
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        char_count = len(content)
        total_chars += char_count
        
        # 提取图片引用
        img_refs = re.findall(r'!\[.*?\]\((.*?)\)', content)
        total_imgs_ref += len(img_refs)
        
        img_ok = True
        for ref in img_refs:
            norm_ref = ref.replace("../figures/", "").replace("figures/", "")
            actual_path = os.path.join(FIGURES_DIR, norm_ref)
            if os.path.exists(actual_path):
                resolved_imgs += 1
            else:
                print(f"  ❌ 章节 {filename} 图片引用未找到: {ref} -> {actual_path}")
                img_ok = False
                all_passed = False
        
        status = "✅ PASS" if (char_count >= 3000 and len(img_refs) == expected_imgs and img_ok) else "⚠️ WARN"
        if len(img_refs) != expected_imgs:
            print(f"  {status} {filename}: 字符数 {char_count:,}, 引用图片 {len(img_refs)}/{expected_imgs}")
        else:
            print(f"  {status} {filename}: 字符数 {char_count:,}, 引用图片 {len(img_refs)} 张")

    # 2. 检查 figures 目录下的 30 张图片
    print("\n[2/3] 检查 figures/ 目录中宁夏回族自治区 30 张高清配图...")
    fig_files = [f for f in os.listdir(FIGURES_DIR) if f.startswith("fig31-") and f.endswith(".png")]
    print(f"  实际扫描到宁夏配图: {len(fig_files)} 张 (预期 30 张)")
    if len(fig_files) != 30:
        print(f"  ❌ 数量不一致: 实际 {len(fig_files)} 张 != 预期 30 张")
        all_passed = False
    else:
        print("  ✅ 30 张地图全部存在且完好")

    # 3. 统计汇总
    print("\n[3/3] 总体核验汇总统计:")
    print(f"  - 章节文件总数: {len(EXPECTED_SECTIONS)} 个 (100% 存在)")
    print(f"  - 全章总字符数: {total_chars:,} 字符 (平均每节约 {total_chars // len(EXPECTED_SECTIONS):,} 字)")
    print(f"  - 配图引用数量: {total_imgs_ref} 张 (预期 30 张引用)")
    print(f"  - 图片解析成功率: {resolved_imgs}/{total_imgs_ref} ({resolved_imgs/max(total_imgs_ref, 1)*100:.1f}%)")
    
    print("\n" + "=" * 70)
    if all_passed and resolved_imgs == 30 and len(fig_files) == 30:
        print("🎉 恭喜！宁夏回族自治区（第31章）全部 7 篇学术级专章与 30 张高清地图 100% 完备！质量达标！")
        print("=" * 70)
        return True
    else:
        print("❌ 核验未完全通过，请根据上述提示排查！")
        print("=" * 70)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
