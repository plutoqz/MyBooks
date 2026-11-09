# -*- coding: utf-8 -*-
import os
import re

html_path = r"D:\code\Ideas\MyBooks\中国地理知识手册\output\中国地理知识手册_全书合卷.html"
text = open(html_path, encoding="utf-8").read()

chapters = re.findall(r'<section class="chapter"', text)
print("Total chapter sections:", len(chapters))

toc_links = re.findall(r'href="#([^"]+)"', text)
print("Total TOC links:", len(toc_links))

imgs = re.findall(r'src="([^"]+)"', text)
print("Total img tags:", len(imgs))

missing = 0
for src in imgs:
    if src.startswith("../figures/"):
        full = os.path.join(r"D:\code\Ideas\MyBooks\中国地理知识手册\output", src)
        if not os.path.exists(full):
            missing += 1

print("Missing images on disk relative to output/:", missing)
