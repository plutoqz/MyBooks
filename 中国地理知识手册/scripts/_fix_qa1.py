# -*- coding: utf-8 -*-
"""按 QA 结论修一批确定的机械问题（幂等，可重复运行）。"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEC = os.path.join(ROOT, "sections")

BOM_FILES = [
    "13-05-12_江苏省.md", "13-05-13_浙江省.md", "13-05-14_安徽省.md",
    "13-05-15_福建省.md", "13-05-16_江西省.md", "13-05-17_湖北省.md",
    "13-05-18_湖南省.md", "13-05-19_广东省.md", "13-05-20_广西壮族自治区.md",
    "13-05-22_重庆市.md", "13-05-27_香港特别行政区.md",
    "13-05-28_澳门特别行政区.md",
]

EDITS = {
    # 06-04：标题误写为 6.2，图号整体错位一位
    "06-04_森林水与矿产.md": [
        ("# 6.2 森林、水与矿产 [可选]", "# 6.4 森林、水与矿产 [可选]"),
        ("![图6-2 分省森林覆盖率]", "![图6-3 分省森林覆盖率]"),
        ("**图 6-2 分省森林覆盖率对比**", "**图 6-3 分省森林覆盖率对比**"),
        ("![图6-3 主要矿产品产量世界占比]", "![图6-4 主要矿产品产量世界占比]"),
        ("**图 6-3 主要矿产品产量中国占世界比重**", "**图 6-4 主要矿产品产量中国占世界比重**"),
    ],
    # 广西：正文用“全区”，标题统一为自治区口径
    "13-05-20_广西壮族自治区.md": [
        ("## 一、省情速览", "## 一、区情速览"),
    ],
    # 西藏：自治区应称“全区”
    "13-05-34_西藏自治区.md": [
        ("全省最低点就在大峡谷出口", "全区最低点就在大峡谷出口"),
    ],
}

# 先剥 BOM
for f in BOM_FILES:
    p = os.path.join(SEC, f)
    raw = open(p, "rb").read()
    if raw.startswith(b"\xef\xbb\xbf"):
        open(p, "wb").write(raw[3:])
        print("BOM stripped:", f)

# 再做文本替换
for f, pairs in EDITS.items():
    p = os.path.join(SEC, f)
    t = io.open(p, encoding="utf-8").read()
    changed = []
    for old, new in pairs:
        if old in t:
            t = t.replace(old, new)
            changed.append(old[:24])
        elif new not in t:
            print("  !! 未找到且目标也缺失:", f, old[:30])
    io.open(p, "w", encoding="utf-8", newline="\n").write(t)
    if changed:
        print("edited:", f, "->", len(changed), "处")
