# -*- coding: utf-8 -*-
"""第 1 章 疆域与位置 —— 统计图表（世界视角）。

fig1-3 世界国土面积前十位国家
fig1-5 中国与 14 个陆上邻国的边界长度
fig1-6 世界陆地边界最长的国家
fig1-8 中国四大海域面积与平均深度
fig1-9 世界主要国家专属经济区面积
"""
import os
import sys

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import C_CHINA, C_TEXT, DPI, FIGURES, setup

OUT = FIGURES
os.makedirs(OUT, exist_ok=True)

C_BAR = "#a9b8c4"       # 一般条
C_GRID = "#dde3e8"


def _fmt(v, nd=1):
    s = f"{v:,.{nd}f}"
    return s.replace(",", " ")


def barh_chart(filename, labels, values, title, subtitle, xlabel,
               highlight_labels=(), highlight_hatch=None, footer=None,
               figsize=(9.5, 6.2), nd=1):
    """横向条形图：数据标签在条端，说明文字一律不进入绘图区。"""
    order = np.argsort(values)  # 升序，使最大值在顶部
    labels = [labels[i] for i in order]
    values = [values[i] for i in order]

    fig, ax = plt.subplots(figsize=figsize)
    bars = ax.barh(labels, values, height=0.62, zorder=3)
    for i, (lab, b) in enumerate(zip(labels, bars)):
        if lab in highlight_labels:
            b.set_color(C_CHINA)
            if highlight_hatch:
                b.set_hatch(highlight_hatch)
                b.set_edgecolor("#8e2b20")
            else:
                b.set_edgecolor("white")
        else:
            b.set_color(C_BAR)
            b.set_edgecolor("white")
        ax.text(b.get_width() + max(values) * 0.012, b.get_y() + b.get_height() / 2,
                _fmt(b.get_width(), nd), va="center", ha="left",
                fontsize=9, color=C_TEXT, zorder=4)

    ax.set_xlim(0, max(values) * 1.14)
    ax.grid(axis="x", color=C_GRID, lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color("#999999")
    ax.tick_params(axis="y", length=0, labelsize=10.5)
    ax.tick_params(axis="x", labelsize=9, colors="#666666")
    ax.set_xlabel(xlabel, fontsize=9.5, color="#666666")

    fig.text(0.02, 0.965, title, fontsize=14.5, fontweight="bold", color=C_TEXT)
    fig.text(0.02, 0.928, subtitle, fontsize=9.5, color="#666666")
    if footer:
        fig.text(0.02, 0.012, footer, fontsize=8.2, color="#555555")
    fig.tight_layout(rect=(0, 0.035 if footer else 0, 1, 0.905))
    fig.savefig(os.path.join(OUT, filename), dpi=DPI)
    plt.close(fig)


def barv_chart(filename, labels, values, title, subtitle, ylabel,
               highlight_labels=(), footer=None, nd=2, figsize=(8.2, 5.4)):
    fig, ax = plt.subplots(figsize=figsize)
    bars = ax.bar(labels, values, width=0.55, edgecolor="white",
                  linewidth=0.5, zorder=3)
    for lab, b in zip(labels, bars):
        if lab in highlight_labels:
            b.set_color(C_CHINA)
        else:
            b.set_color(C_BAR)
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + max(values) * 0.02,
                _fmt(b.get_height(), nd), ha="center", va="bottom",
                fontsize=10.5, color=C_TEXT, zorder=4)
    ax.set_ylim(0, max(values) * 1.15)
    ax.grid(axis="y", color=C_GRID, lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color("#999999")
    ax.spines["bottom"].set_color("#999999")
    ax.tick_params(axis="x", length=0, labelsize=11)
    ax.tick_params(axis="y", labelsize=9, colors="#666666")
    ax.set_ylabel(ylabel, fontsize=9.5, color="#666666")

    fig.text(0.03, 0.955, title, fontsize=14.5, fontweight="bold", color=C_TEXT)
    fig.text(0.03, 0.902, subtitle, fontsize=9.5, color="#666666")
    if footer:
        fig.text(0.03, 0.015, footer, fontsize=8.2, color="#555555")
    fig.tight_layout(rect=(0, 0.04 if footer else 0, 1, 0.88))
    fig.savefig(os.path.join(OUT, filename), dpi=DPI)
    plt.close(fig)


# ------------------------------------------------------------------ 数据
AREA_TOP10 = {  # 国土总面积，万 km²（CIA《世界概况》等公开口径）
    "俄罗斯": 1709.8, "加拿大": 998.5, "美国": 983.4, "中国": 959.7,
    "巴西": 851.6, "澳大利亚": 774.1, "印度": 328.7, "阿根廷": 278.0,
    "哈萨克斯坦": 272.5, "阿尔及利亚": 238.2,
}
CN_BORDERS = {  # 中国与陆上邻国边界长度，km（约数）
    "蒙古": 4700, "俄罗斯": 4300, "缅甸": 2185, "印度（未划定）": 2000,
    "哈萨克斯坦": 1780, "越南": 1450, "朝鲜": 1420, "尼泊尔": 1415,
    "吉尔吉斯斯坦": 1100, "巴基斯坦": 600, "老挝": 505, "不丹": 470,
    "塔吉克斯坦": 450, "阿富汗": 92,
}
WORLD_BORDERS = {  # 陆地边界总长，万 km（CIA《世界概况》）
    "中国": 2.28, "俄罗斯": 2.02, "巴西": 1.61, "印度": 1.39, "美国": 1.20,
}
SEAS = {  # 面积 万km²（均深 m）
    "南海（均深 1 212 m）": (350, 1), "东海（均深 370 m）": (77, 0),
    "黄海（均深 44 m）": (38, 0), "渤海（均深 18 m）": (7.7, 1),
}
EEZ = {  # 专属经济区面积，万 km²（Sea Around Us / VLIZ 估算）
    "美国": 1135, "法国": 1021, "澳大利亚": 851, "俄罗斯": 757,
    "英国": 681, "印度尼西亚": 610, "加拿大": 560, "日本": 448,
    "新西兰": 408, "巴西": 366, "中国（主张管辖海域）": 300,
}


def main():
    barh_chart(
        "fig1-3_世界国土面积对比.png", list(AREA_TOP10), list(AREA_TOP10.values()),
        "世界国土面积前十位的国家", "单位：万 km²（国土总面积，中国以约 960 万 km² 计）",
        "万 km²", highlight_labels=("中国",),
        footer="数据来源：CIA《世界概况》等公开口径。中国陆地面积居世界第三位。",
        figsize=(9.5, 6.6), nd=1)

    barh_chart(
        "fig1-5_中国陆地边界长度排序.png", list(CN_BORDERS), list(CN_BORDERS.values()),
        "中国与 14 个陆上邻国的边界长度", "单位：km（约数）；中蒙边界最长，中阿边界最短",
        "km", highlight_labels=("印度（未划定）",), highlight_hatch="///",
        footer="数据来源：中国外交部公开资料及通行教材数据。中印边界约 2 000 km，尚未正式划定。",
        figsize=(9.0, 7.2), nd=0)

    barv_chart(
        "fig1-6_世界陆地边界最长的国家.png", list(WORLD_BORDERS), list(WORLD_BORDERS.values()),
        "世界陆地边界最长的国家（前五位）", "单位：万 km",
        "万 km", highlight_labels=("中国",),
        footer="数据来源：CIA《世界概况》；中国为外交部口径约 2.28 万 km，居世界首位。",
        figsize=(8.2, 5.4), nd=2)

    sea_labels = list(SEAS)
    sea_values = [SEAS[k][0] for k in sea_labels]
    barh_chart(
        "fig1-8_四大海域面积对比.png", sea_labels, sea_values,
        "中国四大海域的面积与平均深度", "单位：万 km²",
        "万 km²", highlight_labels=(),
        footer="数据来源：通行教材与海洋部门公开数据。南海面积约 350 万 km²，为面积最大、最深的海区。",
        figsize=(9.0, 4.6), nd=1)

    barh_chart(
        "fig1-9_世界专属经济区面积对比.png", list(EEZ), list(EEZ.values()),
        "世界主要国家的专属经济区面积", "单位：万 km²；专属经济区自领海基线量起不超过 200 海里",
        "万 km²", highlight_labels=("中国（主张管辖海域）",), highlight_hatch="///",
        footer="数据来源：Sea Around Us / VLIZ 估算（2020 年前后口径）。中国约 300 万 km² 为主张管辖海域口径。",
        figsize=(9.5, 6.6), nd=0)


if __name__ == "__main__":
    setup()
    main()
    print("统计图已生成：", sorted(f for f in os.listdir(OUT) if f.startswith("fig1-")))
