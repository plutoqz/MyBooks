# -*- coding: utf-8 -*-
"""生成第 2 章新扩充图表：
fig2-12 港澳台与内地代表省市经济与人口密度对比
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

C_GRID = "#dde3e8"


def generate_fig2_12():
    """绘制港澳台与内地代表省市经济与人口密度对比图"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 5.8))

    regions = ["澳门", "香港", "上海", "北京", "江苏", "广东", "台湾", "浙江", "全国平均"]
    # 人口密度 (人/km²)
    densities = [20697, 6733, 3923, 1332, 795, 707, 651, 628, 150]
    # 人均 GDP (万元人民币，2023/2024 口径估算)
    gdp_pc = [48.5, 38.2, 19.1, 20.0, 15.1, 10.8, 23.6, 12.5, 8.9]

    colors = [C_CHINA if r in ["澳门", "香港", "台湾"] else "#8fa8bf" for r in regions]

    # 子图 1: 人口密度 (对数刻度)
    ax1.scatter(densities[::-1], regions[::-1], color=colors[::-1], s=50, zorder=3)
    ax1.set_xscale("log")
    ax1.set_xlim(50, 60000)
    ax1.grid(axis="x", color=C_GRID, lw=0.7, ls="--", zorder=0)
    for y, val in enumerate(densities[::-1]):
        ax1.text(val * 1.15, y, f"{val:,}",
                 va="center", ha="left", fontsize=9, color=C_TEXT, fontweight="bold")
    ax1.set_xlabel("人口密度 (人/km²，对数刻度)", fontsize=9.5, color="#555555")
    ax1.set_title("人口密度对比（极端集聚特征）", fontsize=11, fontweight="bold", color=C_TEXT, pad=10)
    for s in ("top", "right"):
        ax1.spines[s].set_visible(False)
    ax1.tick_params(labelsize=9.5)

    # 子图 2: 人均 GDP
    bars2 = ax2.barh(regions[::-1], gdp_pc[::-1], color=colors[::-1], height=0.62, edgecolor="white", zorder=3)
    ax2.set_xlim(0, 56)
    ax2.grid(axis="x", color=C_GRID, lw=0.7, zorder=0)
    for b, val in zip(bars2, gdp_pc[::-1]):
        ax2.text(val + 0.8, b.get_y() + b.get_height() / 2, f"{val:.1f} 万",
                 va="center", ha="left", fontsize=9, color=C_TEXT, fontweight="bold")
    ax2.set_xlabel("人均 GDP (万元人民币)", fontsize=9.5, color="#555555")
    ax2.set_title("人均经济体量对比", fontsize=11, fontweight="bold", color=C_TEXT, pad=10)
    for s in ("top", "right"):
        ax2.spines[s].set_visible(False)
    ax2.tick_params(labelsize=9.5)

    fig.text(0.03, 0.965, "港澳台与内地代表省市规模与密度对比", fontsize=14.5, fontweight="bold", color=C_TEXT)
    fig.text(0.03, 0.922, "红色代表港澳台；数据取自 2023/2024 年各地官方统计公报，港澳台按同期汇率折算为人民币口径",
             fontsize=9.2, color="#666666")
    fig.text(0.5, 0.015, "数据来源：国家统计局、香港特区统计处、澳门统计暨普查局、台湾有关方面统计公报。",
             ha="center", fontsize=8.2, color="#555555")

    fig.tight_layout(rect=(0, 0.04, 1, 0.90))
    save_volume_figure(fig, os.path.join(OUT, "fig2-12_港澳台与内地代表省市经济与人口密度对比.png"), dpi=DPI)
    plt.close(fig)
    print("Generated fig2-12_港澳台与内地代表省市经济与人口密度对比.png")


if __name__ == "__main__":
    generate_fig2_12()
