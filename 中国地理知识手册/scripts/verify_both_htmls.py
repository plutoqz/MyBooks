# -*- coding: utf-8 -*-
import os
import re

out_dir = r"D:\code\Ideas\MyBooks\中国地理知识手册\output"

f1 = os.path.join(out_dir, "中国地理知识手册_全书合卷.html")
f2 = os.path.join(out_dir, "中国地理知识手册_全书合卷_自包含单文件.html")

print("File 1 exists:", os.path.exists(f1), "Size:", os.path.getsize(f1) / 1024 / 1024, "MB")
print("File 2 exists:", os.path.exists(f2), "Size:", os.path.getsize(f2) / 1024 / 1024, "MB")

txt1 = open(f1, encoding="utf-8").read()
imgs1 = re.findall(r'<img\s+[^>]*src="([^"]+)"', txt1)
print("File 1 total <img> tags:", len(imgs1))

missing1 = 0
for src in imgs1:
    if src.startswith("../figures/"):
        real = os.path.join(out_dir, src)
        if not os.path.exists(real):
            missing1 += 1
print("File 1 missing images on disk:", missing1)

# Check File 2
txt2_head = open(f2, encoding="utf-8").read(500000)
has_b64 = "data:image/png;base64," in txt2_head
print("File 2 has base64 data URIs:", has_b64)

# Count sections
chaps1 = re.findall(r'<section class="chapter"', txt1)
h2s = re.findall(r'<h2 id="([^"]+)">([^<]+)</h2>', txt1)
print("Total chapters:", len(chaps1))
print("Total h2 sections:", len(h2s))
