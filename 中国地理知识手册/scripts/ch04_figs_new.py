# -*- coding: utf-8 -*-
"""第 4 章 气候 —— 补充高质量专题统计图表。

fig4-9: 中国主要气象灾害直接经济损失构成与受灾面积演变
fig4-10: 全国代表城市气温年较差与年降水量分布矩阵（四象限水热图）
"""
from volume1_layout import save_volume_figure
import os
import sys
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import FIGURES, DPI, setup

setup()


def make_fig4_9():
    """图4-9：中国主要气象灾害直接经济损失构成与农作物受灾面积演变趋势。"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5.5))

    # 1. 左子图：损失构成（应急管理部与中国气象局 2010—2023 年统计均值）
    labels = ['暴雨洪涝', '干旱灾害', '台风风暴潮', '低温冷冻与雪灾', '风雹与沙尘雷电']
    sizes = [48.5, 21.8, 16.7, 7.6, 5.4]
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#9467bd', '#d62728']
    explode = (0.04, 0.02, 0.02, 0, 0)

    wedges, texts, autotexts = ax1.pie(
        sizes, explode=explode, labels=labels, autopct='%1.1f%%',
        startangle=140, colors=colors, pctdistance=0.75,
        textprops=dict(color="#2c3e50", fontsize=10.5),
        wedgeprops=dict(width=0.45, edgecolor='white', linewidth=2)
    )
    for at in autotexts:
        at.set_fontsize(9.5)
        at.set_fontweight('bold')

    ax1.set_title("中国主要气象灾害直接经济损失构成\n（2010—2023年多年均值）",
                  fontsize=12, fontweight='bold', color="#2c3e50", pad=12)

    # 2. 右子图：2000—2023 年农作物受灾面积与成灾面积演变（万公顷）
    years = np.arange(2000, 2024)
    # 基于《中国气象灾害年鉴》与统计年鉴的实际波动序列
    affected = np.array([
        5273, 5224, 4699, 5451, 3711, 3882, 4109, 4899, 3903, 4721,
        3743, 3248, 2496, 3135, 2489, 2177, 2622, 1848, 2081, 1926,
        1996, 1174, 1207, 1054
    ])
    damaged = np.array([
        2593, 2735, 2640, 3252, 2020, 2049, 2210, 2642, 2085, 2521,
        1856, 1612, 1238, 1544, 1262, 1045, 1281, 896, 1012, 915,
        898, 542, 584, 492
    ])

    ax2.plot(years, affected, marker='o', color='#e74c3c', linewidth=2,
             markersize=4.5, label='受灾面积（万公顷）')
    ax2.plot(years, damaged, marker='s', color='#2980b9', linewidth=2,
             markersize=4.5, label='成灾面积（万公顷）')
    ax2.fill_between(years, affected, color='#e74c3c', alpha=0.1)

    # 趋势辅助线
    z = np.polyfit(years, affected, 1)
    p = np.poly1d(z)
    ax2.plot(years, p(years), "--", color="#7f8c8d", linewidth=1.5, label='线性下降趋势线')

    ax2.set_title("2000—2023年中国气象灾害农作物受灾面积演变",
                  fontsize=12, fontweight='bold', color="#2c3e50", pad=12)
    ax2.set_xlabel("年份", fontsize=10.5, color="#2c3e50")
    ax2.set_ylabel("农作物面积（万公顷）", fontsize=10.5, color="#2c3e50")
    ax2.grid(True, linestyle="--", alpha=0.5)
    ax2.legend(loc='upper right', frameon=True, fontsize=9.5)
    ax2.set_xlim(1999, 2024)
    ax2.set_ylim(0, 6000)

    fig.tight_layout()
    out_path = os.path.join(FIGURES, "fig4-9_中国主要气象灾害直接经济损失构成与受灾演变.png")
    save_volume_figure(fig, out_path, dpi=DPI)
    plt.close(fig)
    print(f"Saved {out_path}")


def make_fig4_10():
    """图4-10：全国代表城市气温年较差与年降水量四象限分布图。"""
    fig, ax = plt.subplots(figsize=(11, 7))

    # 代表城市数据: (名称, 气温年较差℃, 年降水量mm, 气候类型, 点颜色, 标注偏移(dx, dy))
    cities_data = [
        # 湿润海洋/低纬 (热带/南亚热带)
        ("海口", 10.5, 1750, "热带季风", "#e74c3c", (5, 5)),
        ("广州", 15.2, 1920, "南亚热带季风", "#e74c3c", (5, 5)),
        ("台北", 14.1, 2350, "亚热带季风", "#e74c3c", (5, -15)),
        ("厦门", 15.8, 1380, "南亚热带季风", "#e74c3c", (5, 5)),
        # 亚热带季风区
        ("武汉", 25.2, 1260, "亚热带季风", "#2980b9", (5, 5)),
        ("上海", 24.1, 1180, "亚热带季风", "#2980b9", (5, -15)),
        ("重庆", 21.0, 1100, "亚热带季风(盆地)", "#2980b9", (-35, 5)),
        ("成都", 20.2, 920, "亚热带季风(盆地)", "#2980b9", (-35, -12)),
        ("昆明", 12.0, 1000, "高原亚热带季风", "#16a085", (5, 5)),
        # 暖温带季风区
        ("北京", 30.8, 590, "暖温带季风", "#f39c12", (5, 5)),
        ("西安", 26.8, 580, "暖温带季风", "#f39c12", (-35, 5)),
        ("郑州", 27.9, 640, "暖温带季风", "#f39c12", (5, 5)),
        # 中温带季风区
        ("哈尔滨", 41.5, 530, "中温带季风", "#8e44ad", (5, 5)),
        ("沈阳", 36.2, 700, "中温带季风", "#8e44ad", (5, 5)),
        ("漠河", 48.5, 460, "寒温带大陆性", "#8e44ad", (-40, -12)),
        # 西北温带干旱半干旱区
        ("呼和浩特", 34.2, 390, "中温带半干旱", "#d35400", (5, 5)),
        ("兰州", 27.5, 310, "温带半干旱", "#d35400", (5, 5)),
        ("乌鲁木齐", 38.0, 280, "温带大陆性干旱", "#d35400", (5, 5)),
        ("银川", 32.5, 180, "中温带干旱", "#d35400", (5, 5)),
        ("吐鲁番", 42.8, 16, "极端大陆性干旱", "#c0392b", (-45, 5)),
        # 青藏高寒区
        ("拉萨", 16.5, 450, "高原山地气候", "#27ae60", (5, 5)),
        ("西宁", 22.5, 370, "高原山地气候", "#27ae60", (5, 5)),
    ]

    # 绘制参考基准线与象限背景
    ax.axvline(25, color="#bdc3c7", linestyle="--", linewidth=1.2)
    ax.axhline(800, color="#bdc3c7", linestyle="--", linewidth=1.2)

    # 绘制散点
    for name, trange, prec, ctype, color, (dx, dy) in cities_data:
        ax.scatter(trange, prec, color=color, s=80, edgecolors="#2c3e50", linewidths=1.2, zorder=5)
        ax.annotate(name, (trange, prec), textcoords="offset points", xytext=(dx, dy),
                    fontsize=9.5, fontweight='bold', color="#2c3e50", zorder=6)

    # 分类图例
    type_colors = [
        ("热带/南亚热带季风", "#e74c3c"),
        ("中北亚热带季风", "#2980b9"),
        ("暖温带季风", "#f39c12"),
        ("中温带/寒温带季风", "#8e44ad"),
        ("温带大陆性干旱/半干旱", "#d35400"),
        ("高原山地气候", "#27ae60"),
    ]
    for label, col in type_colors:
        ax.scatter([], [], color=col, s=70, edgecolors="#2c3e50", label=label)

    ax.legend(loc="upper right", frameon=True, fontsize=9.5, title="气候带类型")

    ax.set_title("中国22个代表城市气温年较差与年降水量分布矩阵",
                 fontsize=14, fontweight='bold', color="#2c3e50", pad=15)
    ax.set_xlabel("气温年较差（最热月均温 − 最冷月均温，℃）", fontsize=11, color="#2c3e50")
    ax.set_ylabel("年平均降水量（mm）", fontsize=11, color="#2c3e50")
    ax.set_xlim(5, 52)
    ax.set_ylim(0, 2500)
    ax.grid(True, linestyle=":", alpha=0.6)

    fig.tight_layout()
    out_path = os.path.join(FIGURES, "fig4-10_全国代表城市气温年较差与年降水量分布矩阵.png")
    save_volume_figure(fig, out_path, dpi=DPI)
    plt.close(fig)
    print(f"Saved {out_path}")


if __name__ == "__main__":
    make_fig4_9()
    make_fig4_10()
