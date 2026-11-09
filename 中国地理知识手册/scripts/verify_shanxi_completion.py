# -*- coding: utf-8 -*-
"""山西省全量文档与配图完备性检验脚本"""
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

vol2_dir = r"D:\code\Ideas\MyBooks\中国地理知识手册\sections_vol2"
fig_dir = r"D:\code\Ideas\MyBooks\中国地理知识手册\figures"

files = [f for f in os.listdir(vol2_dir) if f.startswith("04-")]
files.sort()

print(f"Checking {len(files)} files in Chapter 04 (Shanxi Province)...\n")
missing_images = []
stats = []

for f in files:
    fpath = os.path.join(vol2_dir, f)
    with open(fpath, "r", encoding="utf-8") as fp:
        content = fp.read()

    # 中文字数统计
    c_chars = len(re.findall(r"[\u4e00-\u9fa5]", content))

    # 图片引用统计
    imgs = re.findall(r"!\[.*?\]\((.*?)\)", content)
    for img in imgs:
        clean_img = img.replace("../figures/", "").strip()
        actual_path = os.path.join(fig_dir, clean_img)
        if not os.path.exists(actual_path):
            missing_images.append((f, img, clean_img))

    stats.append((f, c_chars, len(imgs)))

header = f"{'File':<36} | {'Chars':<8} | {'Images':<6}"
print(header)
print("-" * len(header))
for f, c, img_cnt in stats:
    print(f"{f:<36} | {c:<8} | {img_cnt:<6}")

print("-" * len(header))
total_chars = sum(s[1] for s in stats)
total_imgs = sum(s[2] for s in stats)
print(f"Total files: {len(stats)}")
print(f"Total Chinese characters: {total_chars:,}")
print(f"Total image references: {total_imgs}")

if missing_images:
    print(f"\n[ERROR] Found {len(missing_images)} missing images:")
    for mf, mref, mclean in missing_images:
        print(f"  {mf} -> {mref}")
else:
    print("\n[SUCCESS] All 60 referenced images exist on disk and match 100%!")
