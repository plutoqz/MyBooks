# -*- coding: utf-8 -*-
"""生成第 3 章新扩充图表：
fig3-9 全国五种基本地形类型面积构成
fig3-10 中国主要山系现代冰川规模对比
"""
from volume1_layout import save_volume_figure
import os
import sys
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import C_CHINA, C_TEXT, DPI, FIGURES, setup

setup()
OUT = FIGURES
os.makedirs(OUT, exist_ok=True)

C_BAR = "#8fa8bf"
C_GRID = "#dde3e8"


def generate_fig3_9():
    """绘制全国五种基本地形类型面积构成与占比条形图"""
    types = ["山地", "高原", "盆地", "平原", "丘陵"]
    pcts = [33.3, 26.0, 18.8, 12.0, 9.9]
    areas = [320.0, 250.0, 180.0, 115.0, 95.0]  # 万 km² 估算值
    colors = ["#8e2b20", "#c0392b", "#d35400", "#27ae60", "#2980b9"]

    fig, ax = plt.subplots(figsize=(10.2, 5.6))
    bars = ax.barh(types[::-1], pcts[::-1], height=0.6, color=colors[::-1],
                   edgecolor="white", lw=1.2, zorder=3)

    for b, pct, area in zip(bars, pcts[::-1], areas[::-1]):
        ax.text(b.get_width() + 0.8, b.get_y() + b.get_height() / 2,
                f"{pct:.1f}%  (约 {area:.0f} 万 km²)",
                va="center", ha="left", fontsize=10.5, color=C_TEXT, fontweight="bold")

    ax.set_xlim(0, 42)
    ax.grid(axis="x", color=C_GRID, lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color("#999999")
    ax.spines["bottom"].set_color("#999999")
    ax.tick_params(axis="y", labelsize=11.5)
    ax.tick_params(axis="x", labelsize=9.5, colors="#666666")
    ax.set_xlabel("占全国陆地面积比例 (%)", fontsize=10, color="#555555")

    fig.text(0.03, 0.965, "中国五种基本地形类型面积构成与占比", fontsize=14.5, fontweight="bold", color=C_TEXT)
    fig.text(0.03, 0.922, "山地、高原与丘陵统称为山区，合计占全国陆地面积约 69.2%（广义山区面积超三分之二）",
             fontsize=9.3, color="#666666")
    fig.text(0.5, 0.015, "数据来源：中国自然地理区划与国土调查统计口径；山地与高原构成中国地形绝对主体。",
             ha="center", fontsize=8.2, color="#555555")

    fig.tight_layout(rect=(0, 0.04, 1, 0.90))
    save_volume_figure(fig, os.path.join(OUT, "fig3-9_全国五种基本地形类型面积构成.png"), dpi=DPI)
    plt.close(fig)
    print("Generated fig3-9_全国五种基本地形类型面积构成.png")


def generate_fig3_10():
    """绘制中国主要山系现代冰川面积与水塔规模对比图"""
    mountains = [
        "昆仑山脉", "念青唐古拉山", "天山山脉(中方)", "喜马拉雅山(中方)",
        "喀喇昆仑(中方)", "祁连山脉", "冈底斯山脉", "唐古拉山脉", "横断山脉"
    ]
    glacier_area = [12260, 7536, 7180, 6720, 5920, 1590, 1560, 1490, 1450]  # km²

    order = np.argsort(glacier_area)
    mountains = [mountains[i] for i in order]
    glacier_area = [glacier_area[i] for i in order]

    fig, ax = plt.subplots(figsize=(10.5, 6.2))
    bars = ax.barh(mountains, glacier_area, height=0.62, color="#5dade2", edgecolor="white", zorder=3)

    # 高亮前三大山系
    bars[-1].set_color(C_CHINA)
    bars[-2].set_color("#c0392b")
    bars[-3].set_color("#2980b9")

    for b in bars:
        ax.text(b.get_width() + 180, b.get_y() + b.get_height() / 2,
                f"{int(b.get_width()):,} km²",
                va="center", ha="left", fontsize=9.5, color=C_TEXT, fontweight="bold")

    ax.set_xlim(0, 14500)
    ax.grid(axis="x", color=C_GRID, lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color("#999999")
    ax.spines["bottom"].set_color("#999999")
    ax.tick_params(axis="y", labelsize=10.5)
    ax.tick_params(axis="x", labelsize=9.5, colors="#666666")
    ax.set_xlabel("现代冰川覆盖面积 (km²)", fontsize=10, color="#555555")

    fig.text(0.03, 0.965, "中国主要山系现代冰川分布面积对比", fontsize=14.5, fontweight="bold", color=C_TEXT)
    fig.text(0.03, 0.922, "“亚洲水塔”固体水库蓄水量与融水径流核心源区；中国境内发育现代冰川逾 4.8 万条、面积超 5.1 万 km²",
             fontsize=9.3, color="#666666")
    fig.text(0.5, 0.015, "数据来源：中国科学院青藏高原研究所、寒区旱区环境与工程研究所《中国第二次冰川编目》。",
             ha="center", fontsize=8.2, color="#555555")

    fig.tight_layout(rect=(0, 0.04, 1, 0.90))
    save_volume_figure(fig, os.path.join(OUT, "fig3-10_中国主要山系现代冰川规模对比.png"), dpi=DPI)
    plt.close(fig)
    print("Generated fig3-10_中国主要山系现代冰川规模对比.png")


if __name__ == "__main__":
    generate_fig3_9()
    generate_fig3_10()
