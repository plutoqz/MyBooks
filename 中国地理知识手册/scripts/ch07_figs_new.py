# -*- coding: utf-8 -*-
"""第 7 章 生态环境与自然灾害 —— 补充高水准专业图表。

fig7-4: 中国首批国家公园面积规模与旗舰物种对比
fig7-5: 全国主要地质灾害隐患类型构成与成功避险防治成效
"""
from volume1_layout import save_volume_figure
import os
import sys
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import FIGURES, DPI, setup

setup()


def make_fig7_4():
    """图7-4：中国首批五大国家公园面积规模与旗舰物种对比。"""
    fig, ax = plt.subplots(figsize=(10, 5.8))

    parks = [
        "武夷山国家公园\n(闽赣交界)",
        "海南热带雨林\n国家公园",
        "东北虎豹\n国家公园(吉黑)",
        "大熊猫国家公园\n(川陕甘)",
        "三江源国家公园\n(青海西藏)"
    ]
    # 面积 (万 km²)
    areas = [0.13, 0.43, 1.41, 2.20, 19.07]
    species = [
        "黄腹角雉 / 武夷角蟾",
        "海南长臂猿 (极危)",
        "野生东北虎 / 东北豹",
        "大熊猫 (国宝旗舰)",
        "雪豹 / 藏羚羊 / 野牦牛"
    ]

    y_pos = np.arange(len(parks))
    colors = ['#16a085', '#27ae60', '#2980b9', '#8e44ad', '#34495e']

    bars = ax.barh(y_pos, areas, color=colors, edgecolor='#2c3e50', height=0.55, zorder=3)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(parks, fontsize=10.5, fontweight='bold', color="#2c3e50")
    ax.set_xlabel("保护总面积（万平方公里）", fontsize=11, color="#2c3e50")
    ax.set_title("中国首批设立的五大国家公园面积与代表性旗舰物种\n（构建以国家公园为主体的自然保护地顶层架构，保护面积达23万平方公里）",
                 fontsize=12.5, fontweight='bold', color="#2c3e50", pad=14)
    ax.grid(True, axis='x', linestyle=':', alpha=0.6)
    ax.set_xlim(0, 22)
    ax.spines[["top", "right"]].set_visible(False)

    # 标注面积与代表物种
    for bar, sp, a in zip(bars, species, areas):
        w = bar.get_width()
        ax.text(w + 0.35, bar.get_y() + bar.get_height()/2,
                f"{a:.2f} 万km²\n{sp}",
                ha='left', va='center', fontsize=9.5, fontweight='bold', color="#2c3e50")

    fig.tight_layout()
    out_path = os.path.join(FIGURES, "fig7-4_中国首批国家公园面积规模与旗舰物种对比.png")
    save_volume_figure(fig, out_path, dpi=DPI)
    plt.close(fig)
    print(f"Saved {out_path}")


def make_fig7_5():
    """图7-5：全国主要地质灾害隐患类型构成与成功避险成效。"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 5.5))

    # 1. 左子图：自然资源部全国地质灾害风险普查隐患点类型构成 (环形图)
    labels = ['滑坡', '崩塌', '泥石流', '地面塌陷与沉降', '地裂缝']
    sizes = [68.5, 21.2, 6.8, 2.5, 1.0]
    colors = ['#e74c3c', '#e67e22', '#f39c12', '#3498db', '#95a5a6']
    explode = (0.03, 0.02, 0, 0, 0)

    wedges, texts, autotexts = ax1.pie(
        sizes, explode=explode, labels=labels, autopct='%1.1f%%',
        startangle=140, colors=colors, pctdistance=0.75,
        textprops=dict(color="#2c3e50", fontsize=10),
        wedgeprops=dict(width=0.45, edgecolor='white', linewidth=2)
    )
    for at in autotexts:
        at.set_fontsize(9.5)
        at.set_fontweight('bold')

    ax1.set_title("全国主要地质灾害隐患类型构成\n（全国查明隐患点逾30万处，滑坡崩塌占九成）",
                  fontsize=11.5, fontweight='bold', color="#2c3e50", pad=12)

    # 2. 右子图：2010—2023年全国地质灾害成功避险起数演变（条形图）
    years = [f"{y}" for y in range(2013, 2024)]
    success_cases = [376, 417, 452, 676, 896, 703, 904, 1146, 905, 545, 621]

    bars2 = ax2.bar(years, success_cases, color="#27ae60", edgecolor="#1e8449", width=0.6, zorder=3)
    ax2.plot(years, success_cases, color="#1e8449", marker='o', linewidth=1.8, markersize=5, zorder=4)

    for bar in bars2:
        h = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2, h + 15, f"{h}",
                 ha='center', va='bottom', fontsize=8.5, color="#2c3e50")

    ax2.set_title("2013—2023年全国地质灾害成功避险起数演变\n（“人防+技防”群测群防网络年均避免数万人伤亡）",
                  fontsize=11.5, fontweight='bold', color="#2c3e50", pad=12)
    ax2.set_xlabel("年份", fontsize=10.5, color="#2c3e50")
    ax2.set_ylabel("成功避险起数", fontsize=10.5, color="#2c3e50")
    ax2.grid(True, axis='y', linestyle='--', alpha=0.5)
    ax2.set_ylim(0, 1300)
    ax2.tick_params(axis='x', rotation=35)

    fig.tight_layout()
    out_path = os.path.join(FIGURES, "fig7-5_中国主要地质灾害隐患类型构成与综合防治.png")
    save_volume_figure(fig, out_path, dpi=DPI)
    plt.close(fig)
    print(f"Saved {out_path}")


if __name__ == "__main__":
    make_fig7_4()
    make_fig7_5()
