# -*- coding: utf-8 -*-
import glob, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEC = os.path.join(ROOT, "sections")

fig13_refs = {}
for md in glob.glob(os.path.join(SEC, "*.md")):
    txt = open(md, encoding="utf-8").read()
    for m in re.findall(r'fig13-\d+_[^)\"\s]+', txt):
        fig13_refs.setdefault(m, []).append(os.path.basename(md))

print(f"Total distinct fig13 images referenced: {len(fig13_refs)}")
macro_refs = {k: v for k, v in fig13_refs.items() if any(not f.startswith("13-05-") for f in v)}
print("Figures referenced by macro sections (13-01 to 13-04):")
for k, v in sorted(macro_refs.items()):
    print(f"  {k} -> {v}")
