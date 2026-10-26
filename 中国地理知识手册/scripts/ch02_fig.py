# -*- coding: utf-8 -*-
"""第 2 章 行政区划 —— 2.1 节图表。

fig2-1 行政区划层级结构示意图（自绘）
fig2-2 各级政区数量与县级构成（民政部公报数据）
"""
import os
import sys

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import C_TEXT, DPI, FIGURES, setup

OUT = FIGURES
os.makedirs(OUT, exist_ok=True)

C_MAIN = "#eaf1f7"
C_MAIN_E = "#4a6274"
C_SUB = "#f6f5f1"
C_SUB_E = "#a8a29a"
C_TOP = "#c0392b"


def _box(ax, x, y, w, h, text, fc, ec, fontsize=10, dashed=False, bold=True):
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2",
                       fc=fc, ec=ec, lw=1.0, ls="--" if dashed else "-",
                       mutation_scale=1, zorder=3)
    ax.add_patch(p)
    weight = "bold" if bold else "normal"
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fontsize, color=C_TEXT, fontweight=weight,
            linespacing=1.35, zorder=4)


def fig2_1_hierarchy():
    fig, ax = plt.subplots(figsize=(11.5, 8.8))
    ax.set_xlim(0, 100)
    ax.set_ylim(9, 100)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)

    # 主干层级框（左侧列）
    main_x, main_w = 5, 26
    levels = [
        ("中华人民共和国", 84.5, 6.5, C_TOP, "#8e2b20", False),
        ("省级行政区\n34 个", 72.5, 9, C_MAIN, C_MAIN_E, False),
        ("地级行政区\n333 个", 58, 9, C_MAIN, C_MAIN_E, False),
        ("县级行政区\n2 846 个", 43.5, 9, C_MAIN, C_MAIN_E, False),
        ("乡级行政区\n38 712 个", 29, 9, C_MAIN, C_MAIN_E, False),
        ("村（居）民委员会\n基层群众性自治组织", 14, 9, C_SUB, C_SUB_E, True),
    ]
    centers = {}
    for text, y, h, fc, ec, dashed in levels:
        _box(ax, main_x, y, main_w, h, text, fc, ec,
             fontsize=11 if not dashed else 9.5, dashed=dashed)
        centers[text] = (main_x + main_w, y + h / 2, y)

    # 主干箭头
    arrows = [(84.5, 81.5), (72.5, 67), (58, 52.5), (43.5, 38), (29, 23)]
    for y_from, y_to in arrows:
        ax.annotate("", xy=(main_x + main_w / 2, y_to), xytext=(main_x + main_w / 2, y_from),
                    arrowprops=dict(arrowstyle="-|>", color=C_MAIN_E, lw=1.6))

    # 各层级右侧的类型框
    rows = [
        (77, ["省\n23", "自治区\n5", "直辖市\n4", "特别行政区\n2"]),
        (62.5, ["地级市\n293", "自治州\n30", "地区\n7", "盟\n3"]),
        (48, ["市辖区\n977", "县\n1 299", "县级市\n397", "自治县\n117",
              "旗\n49", "自治旗\n3", "特区\n1", "林区\n1"]),
        (33.5, ["街道办事处", "镇", "乡", "民族乡", "苏木", "民族苏木", "县辖区"]),
    ]
    sub_x0, sub_x1 = 40, 99
    for cy, subs in rows:
        n = len(subs)
        gap = 1.6 if n <= 4 else 1.1
        w = (sub_x1 - sub_x0 - (n - 1) * gap) / n
        h = 7 if n <= 4 else 8
        # 连接干道：主干框右缘 -> 子框行
        ax.plot([main_x + main_w, sub_x0 - 1.5], [cy, cy], color=C_SUB_E, lw=1.0, zorder=1)
        ax.plot([main_x + main_w, main_x + main_w], [cy, cy], color=C_SUB_E, lw=0)  # 占位
        for i, s in enumerate(subs):
            x = sub_x0 + i * (w + gap)
            _box(ax, x, cy - h / 2, w, h, s, C_SUB, C_SUB_E,
                 fontsize=9.5 if n <= 4 else 8.2, bold=False)
        # 主干连接点
        ax.plot([main_x + main_w - 0.0], [cy], marker="o", ms=3, color=C_SUB_E, zorder=2)

    ax.text(0.5, 0.975, "中国行政区划的层级结构", transform=ax.transAxes,
            ha="center", va="top", fontsize=15.5, fontweight="bold", color=C_TEXT)
    ax.text(0.5, 0.935, "宪法规定省、县、乡三级；地级为事实层级，村（居）民委员会为自治组织而非一级政府",
            transform=ax.transAxes, ha="center", va="top", fontsize=10, color="#666666")

    fig.text(0.5, 0.012,
             "数量：民政部《2024年民政事业发展统计公报》（截至2024年底）；县级分项为2023年末口径。\n"
             "地级行政区划中的地区行政公署、乡级行政区划中的街道办事处分别为上级政府的派出机关。",
             ha="center", va="bottom", fontsize=8.2, color="#555555")
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(os.path.join(OUT, "fig2-1_行政区划层级结构.png"), dpi=DPI)
    plt.close(fig)


def fig2_2_counts():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.5, 5.6),
                                   gridspec_kw=dict(width_ratios=[1, 1.15]))

    # (a) 各级总量（对数刻度）
    lv = ["乡级", "县级", "地级", "省级"]
    vals = [38712, 2846, 333, 34]
    colors = ["#a9b8c4", "#a9b8c4", "#a9b8c4", C_TEXT]
    bars = ax1.barh(lv, vals, color=colors, height=0.58, zorder=3)
    for b, v in zip(bars, vals):
        ax1.text(v * 1.12, b.get_y() + b.get_height() / 2, f"{v:,}".replace(",", " "),
                 va="center", ha="left", fontsize=10, color=C_TEXT, zorder=4)
    ax1.set_xscale("log")
    ax1.set_xlim(10, 300000)
    ax1.grid(axis="x", color="#dde3e8", lw=0.7, zorder=0)
    ax1.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax1.spines[s].set_visible(False)
    ax1.spines["bottom"].set_color("#999999")
    ax1.tick_params(axis="y", length=0, labelsize=10.5)
    ax1.tick_params(axis="x", labelsize=8.5, colors="#666666")
    ax1.set_xlabel("单位：个（对数刻度）", fontsize=9, color="#666666")
    ax1.set_title("各级政区数量（截至2024年底）", loc="left", fontsize=12.5,
                  fontweight="bold", color=C_TEXT, pad=10)

    # (b) 县级构成（2023年末）
    kv = ["林区", "特区", "自治旗", "旗", "自治县", "县级市", "市辖区", "县"]
    kvals = [1, 1, 3, 49, 117, 397, 977, 1299]
    bars2 = ax2.barh(kv, kvals, color="#a9b8c4", height=0.58, zorder=3)
    for b, v in zip(bars2, kvals):
        ax2.text(v + 1299 * 0.015, b.get_y() + b.get_height() / 2, str(v),
                 va="center", ha="left", fontsize=9.5, color=C_TEXT, zorder=4)
    ax2.set_xlim(0, 1450)
    ax2.grid(axis="x", color="#dde3e8", lw=0.7, zorder=0)
    ax2.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax2.spines[s].set_visible(False)
    ax2.spines["bottom"].set_color("#999999")
    ax2.tick_params(axis="y", length=0, labelsize=9.5)
    ax2.tick_params(axis="x", labelsize=8.5, colors="#666666")
    ax2.set_xlabel("单位：个", fontsize=9, color="#666666")
    ax2.set_title("县级行政区的类型构成（2023年末）", loc="left", fontsize=12.5,
                  fontweight="bold", color=C_TEXT, pad=10)

    fig.text(0.02, 0.015,
             "数据来源：民政部《2024年民政事业发展统计公报》《2023年民政事业发展统计公报》。",
             fontsize=8.2, color="#555555")
    fig.tight_layout(rect=(0, 0.045, 1, 1))
    fig.savefig(os.path.join(OUT, "fig2-2_政区数量与县级构成.png"), dpi=DPI)
    plt.close(fig)


if __name__ == "__main__":
    setup()
    fig2_1_hierarchy()
    fig2_2_counts()
    print("已生成：", sorted(f for f in os.listdir(OUT) if f.startswith("fig2-")))
