# -*- coding: utf-8 -*-
"""第 2 章 行政区划 —— 2.3 节图表。

fig2-7 省级行政区数量变化（1949—2025）
fig2-8 地区与地级市的此消彼长
fig2-9 重大建制变更时间轴（1947—2025）
"""
import os
import sys

import matplotlib.pyplot as plt
from matplotlib.patches import Patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import C_CHINA, C_TEXT, DPI, FIGURES, setup

OUT = FIGURES
os.makedirs(OUT, exist_ok=True)

C_BLUE = "#8fa8bf"
C_TAN = "#c2a878"
C_GRID = "#dde3e8"


# ---------------------------------------------------------------- fig 2-7
def fig2_7_province_count():
    pts = [(1949, 50), (1954, 31), (1958, 29), (1967, 30),
           (1988, 31), (1997, 33), (1999, 34), (2025, 34)]
    xs, ys = zip(*pts)

    fig, ax = plt.subplots(figsize=(10.5, 5.8))
    ax.step(xs, ys, where="post", color=C_CHINA, lw=2.2, zorder=3)
    ax.plot(xs, ys, "o", color=C_CHINA, ms=6, mec="white", mew=1.0, zorder=4)
    for x, y in pts:
        ax.annotate(f"{y}", xy=(x, y), xytext=(0, 9), textcoords="offset points",
                    ha="center", fontsize=9.5, color=C_TEXT, zorder=5)

    notes = [
        (1949, 50, "新中国成立：50 个省级单位\n（30 省、12 直辖市、5 行署区等）", (1951.5, 46.5)),
        (1954, 31, "1954 年撤销六大行政区\n并省精简", (1956.5, 37.5)),
        (1958, 29, "桂、宁自治区成立\n天津暂并入河北", (1960.5, 24.5)),
        (1967, 30, "天津恢复直辖市", (1969.5, 33.5)),
        (1988, 31, "海南建省", (1989.5, 27.5)),
        (1997, 33, "重庆直辖\n香港回归", (1993.5, 36.5)),
        (1999, 34, "澳门回归", (2001.5, 30.5)),
    ]
    for x, y, text, (tx, ty) in notes:
        ax.annotate(text, xy=(x, y), xytext=(tx, ty), fontsize=9, color="#444444",
                    ha="center", va="center", zorder=5,
                    arrowprops=dict(arrowstyle="-", color="#999999", lw=0.7,
                                    shrinkA=2, shrinkB=4))

    ax.set_xlim(1946, 2028)
    ax.set_ylim(20, 56)
    ax.grid(axis="y", color=C_GRID, lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color("#999999")
    ax.spines["bottom"].set_color("#999999")
    ax.tick_params(labelsize=9.5)
    ax.set_ylabel("省级行政单位数（个）", fontsize=9.5, color="#666666")
    ax.set_xticks(list(range(1950, 2030, 10)))

    fig.text(0.03, 0.965, "省级行政区数量变化（1949—2025）",
             fontsize=14.5, fontweight="bold", color=C_TEXT)
    fig.text(0.03, 0.922, "省级单位含省、直辖市、行署区、自治区、地方、地区、特别行政区等各形态，按当年年末建制计",
             fontsize=9.3, color="#666666")
    fig.text(0.03, 0.015,
             "数据来源：据百度百科《中华人民共和国行政区划》、中共党史网等公开资料整理；1954 年含昌都地区。",
             fontsize=8.2, color="#555555")
    fig.tight_layout(rect=(0, 0.04, 1, 0.9))
    fig.savefig(os.path.join(OUT, "fig2-7_省级行政区数量变化.png"), dpi=DPI)
    plt.close(fig)


# ---------------------------------------------------------------- fig 2-8
def fig2_8_prefecture():
    years = ["1949", "1982", "2024"]
    region = [170, 170, 7]      # 地区（行署）
    city = [54, 112, 293]       # 地级市

    x = range(len(years))
    w = 0.36
    fig, ax = plt.subplots(figsize=(9.2, 5.4))
    b1 = ax.bar([i - w / 2 for i in x], region, w, color=C_TAN, zorder=3,
                label="地区（行政公署）")
    b2 = ax.bar([i + w / 2 for i in x], city, w, color=C_BLUE, zorder=3,
                label="地级市")
    for bars in (b1, b2):
        for b in bars:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 4,
                    f"{int(b.get_height())}", ha="center", va="bottom",
                    fontsize=10.5, color=C_TEXT, zorder=4)

    ax.set_xticks(list(x))
    ax.set_xticklabels(years, fontsize=11)
    ax.set_ylim(0, 330)
    ax.grid(axis="y", color=C_GRID, lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color("#999999")
    ax.spines["bottom"].set_color("#999999")
    ax.tick_params(axis="y", labelsize=9, colors="#666666")
    ax.set_ylabel("单位：个", fontsize=9.5, color="#666666")
    ax.legend(fontsize=9.5, framealpha=0.92, edgecolor="#cccccc")

    fig.text(0.03, 0.955, "“地区”的消亡与“地级市”的扩张",
             fontsize=14.5, fontweight="bold", color=C_TEXT)
    fig.text(0.03, 0.905, "1983 年起推行“市管县”体制，地级市取代地区成为地级层的主体；2024 年仅存 7 个地区与 3 个盟",
             fontsize=9.3, color="#666666")
    fig.text(0.03, 0.015,
             "数据来源：1949、1982 年据百度百科《地级市》；2024 年据民政部《2024 年民政事业发展统计公报》。"
             "1983 年地区行署为 138 个（周天勇，人民网）。",
             fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.04, 1, 0.885))
    fig.savefig(os.path.join(OUT, "fig2-8_地区与地级市此消彼长.png"), dpi=DPI)
    plt.close(fig)


# ---------------------------------------------------------------- fig 2-9
def fig2_9_timeline():
    events = [  # (年份, 位置上下(+/-), 文本)
        (1947.5, +1, "内蒙古自治区成立\n（第一个省级民族自治区）"),
        (1949.8, -1, "新中国成立\n50 个省级单位、六大行政区"),
        (1952.5, +1, "撤并行署区\n平原、察哈尔等省"),
        (1954.5, -1, "撤销六大行政区\n松江、辽东辽西、绥远等调整"),
        (1955.5, +1, "热河、西康撤销\n新疆维吾尔自治区成立"),
        (1958.5, -1, "广西、宁夏自治区成立\n天津并入河北"),
        (1965.5, +1, "西藏自治区成立"),
        (1967.2, -1, "天津恢复直辖市"),
        (1988.4, +1, "海南省设立"),
        (1997.5, -1, "重庆直辖\n香港回归"),
        (1999.9, +1, "澳门回归"),
        (2012.5, -1, "三沙市设立（地级）"),
        (2019.2, +1, "莱芜并入济南\n（近年唯一地级市整体撤并）"),
    ]
    fig, ax = plt.subplots(figsize=(11.8, 5.8))
    ax.axhline(0, color=C_TEXT, lw=1.6, zorder=2)

    # 同侧事件按出现顺序轮流三档高度，避免密集时段文字重叠
    tier = {+1: 0, -1: 0}
    tiers = [1.2, 2.45, 3.7]
    for year, side, text in events:
        k = tier[side] % 3
        tier[side] += 1
        h = side * tiers[k]
        ax.plot([year, year], [0, h], color="#999999", lw=0.9, zorder=3)
        ax.plot(year, 0, "o", color=C_CHINA, ms=6, mec="white", mew=0.8, zorder=4)
        ax.text(year, h + side * 0.12, text, ha="center",
                va="bottom" if side > 0 else "top", fontsize=8.6,
                color=C_TEXT, linespacing=1.3, zorder=5)

    ax.set_xlim(1944, 2026)
    ax.set_ylim(-5.6, 5.6)
    ax.set_yticks([])
    ax.set_xticks(list(range(1950, 2030, 10)))
    ax.tick_params(axis="x", labelsize=9.5, colors="#666666")
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#999999")

    fig.text(0.03, 0.955, "新中国成立以来重大建制变更时间轴（1947—2025）",
             fontsize=14.5, fontweight="bold", color=C_TEXT)
    fig.text(0.03, 0.905, "自 1950 年代“撤并精简”转入改革开放后“增量设市”，1999 年起省级建置保持 34 个不变",
             fontsize=9.3, color="#666666")
    fig.text(0.03, 0.015,
             "据中共党史网、民政部及各地政府公开资料整理。",
             fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.04, 1, 0.88))
    fig.savefig(os.path.join(OUT, "fig2-9_建制变更时间轴.png"), dpi=DPI)
    plt.close(fig)


if __name__ == "__main__":
    setup()
    fig2_7_province_count()
    fig2_8_prefecture()
    fig2_9_timeline()
    print("已生成：", sorted(f for f in os.listdir(OUT) if f.startswith("fig2-")))
