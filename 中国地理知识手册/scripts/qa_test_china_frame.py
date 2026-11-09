# -*- coding: utf-8 -*-
"""验证全国图骨架修复效果：国界线 + 省界 + 南海断续线。

不依赖 DEM/河流数据，仅用 DataV 全国界线，用于确认：
1. 国界线是否明显区别于省界；
2. 断续线是否由"虚线碎弧"变为连续线段；
3. 南海诸岛是否完整呈现。
"""
import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import geopandas as gpd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import ALBERS, C_SEA, C_TEXT, load_china, plot_china_frame, setup, china_borders

setup()
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "figures")

china = load_china().to_crs(ALBERS)
x0, y0, x1, y1 = china.total_bounds

fig, axes = plt.subplots(1, 2, figsize=(15, 8.2), dpi=110)
fig.patch.set_facecolor("white")

# 左：修复前（旧逻辑复现）
ax = axes[0]
ax.set_facecolor(C_SEA)
prov, dash = china_borders(china)
prov.plot(ax=ax, facecolor="#f2efe9", edgecolor="#c0392b", lw=0.35, zorder=3)
dash.plot(ax=ax, facecolor="none", edgecolor="#3b5872", lw=0.7, ls="--", zorder=4)
ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)
ax.set_aspect("equal"); ax.axis("off")
ax.set_title("修复前：仅省界（无国界）+ 断续线用虚线描边", fontsize=12, color="#922b21")

# 右：修复后
ax = axes[1]
ax.set_facecolor(C_SEA)
chrome = china.copy()
prov, dash = plot_china_frame(ax, chrome, z=3, facecolor="#f2efe9")
ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)
ax.set_aspect("equal"); ax.axis("off")
ax.set_title("修复后：国界（深）+ 省界（浅）+ 断续线（实线）", fontsize=12, color="#1e6b3a")

fig.suptitle("全国图骨架修复对照（DataV 全国界线，Albers 投影）", fontsize=13, color=C_TEXT)
fig.tight_layout(rect=(0, 0, 1, 0.96))
out = os.path.join(OUT, "_test_china_frame.png")
fig.savefig(out, dpi=110, facecolor="white")
print("saved:", out)
