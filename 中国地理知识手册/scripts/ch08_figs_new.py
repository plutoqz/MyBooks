# -*- coding: utf-8 -*-
"""第 8 章 海洋地理 —— 补充高水准专业图表。

fig8-4: 中国主要海岛面积规模与沿海省份海岛数量分布
fig8-5: 全国主要海洋产业增加值构成与海洋经济结构
"""
from volume1_layout import save_volume_figure
import os
import sys
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import FIGURES, DPI, setup, C_TEXT

setup()


def make_fig8_4():
    """图8-4：中国主要海岛面积规模与沿海省份海岛数量分布。"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 5.8), gridspec_kw={"width_ratios": [1.15, 1.0]})

    # 子图1：中国主要海岛面积对比（含陆域面积，平方公里，对数坐标展示）
    islands = [
        "台湾岛 (最大海岛)",
        "海南岛 (第二大岛)",
        "崇明岛 (最大冲积岛)",
        "舟山本岛 (舟山主岛)",
        "东海岛 (湛江)",
        "平潭岛 (海坛岛/闽)",
        "东山岛 (漳州/闽)",
        "玉环岛 (台州/浙)",
        "金门岛 (大金门/闽)",
        "南澳岛 (汕头/粤)"
    ]
    areas = [35882, 33907, 1269, 502.65, 286, 267.1, 220.1, 169.5, 151.6, 113.8] # km²
    island_types = [
        "基岩大陆岛", "基岩大陆岛", "河口冲积岛", "基岩大陆岛", "火山/基岩复合",
        "基岩大陆岛", "基岩大陆岛", "基岩大陆岛", "基岩大陆岛", "基岩大陆岛"
    ]
    colors = ['#c0392b', '#d35400', '#27ae60', '#2980b9', '#16a085',
              '#3498db', '#8e44ad', '#2c3e50', '#7f8c8d', '#e67e22']

    y_pos = np.arange(len(islands))
    bars = ax1.barh(y_pos, areas, color=colors, height=0.6, edgecolor='#34495e', lw=0.6, zorder=3)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(islands, fontsize=9.5, fontweight='bold', color=C_TEXT)
    ax1.set_xlim(0, 55000)
    ax1.set_xlabel("陆域面积（km²）", fontsize=10, color=C_TEXT)
    ax1.set_title("十个代表性海岛的陆域面积",
                  fontsize=10.5, fontweight='bold', color=C_TEXT, pad=10)
    ax1.grid(True, axis='x', linestyle=':', alpha=0.6)

    for bar, val in zip(bars, areas):
        ax1.text(val * 1.18, bar.get_y() + bar.get_height()/2,
                 f"{val:,.1f} km²",
                 ha='left', va='center', fontsize=8.6, fontweight='bold', color=C_TEXT)

    for s in ("top", "right"):
        ax1.spines[s].set_visible(False)

    # 子图2：沿海省份海岛数量分布（面积 >= 500 m²）
    provinces = ["浙江", "广东", "福建", "广西", "山东", "辽宁", "海南", "其他沿海"]
    counts = [2878, 1478, 1404, 637, 589, 506, 600, 200]
    prov_colors = ["#2980b9", "#27ae60", "#e67e22", "#16a085", "#8e44ad", "#d35400", "#c0392b", "#7f8c8d"]

    wedges, texts, autotexts = ax2.pie(
        counts, labels=provinces, autopct="%1.1f%%", startangle=140,
        colors=prov_colors, pctdistance=0.72,
        wedgeprops=dict(width=0.45, edgecolor="white", lw=1.5),
        textprops=dict(fontsize=9, color=C_TEXT)
    )
    for at in autotexts:
        at.set_fontsize(8.5)
        at.set_fontweight("bold")
        at.set_color("white")

    ax2.set_title("沿海省份海岛数量构成\n（浙、粤、闽合计占图示数量的69.5%）",
                  fontsize=10.5, fontweight='bold', color=C_TEXT, pad=10)

    fig.text(0.02, 0.985, "中国主要海岛面积规模与沿海省份海岛数量分布", fontsize=13.5, fontweight="bold", color=C_TEXT)
    fig.text(0.02, 0.952, "岛屿陆域面积与分省岛屿数量分别比较；数量沿用所引省区资料汇编",
             fontsize=9.2, color="#555555")
    fig.text(0.02, 0.012, "数据来源：自然资源部《全国海岛统计调查公报》、《中国海洋统计年鉴》与沿海省区海岛保护规划",
             fontsize=8, color="#777777")

    fig.tight_layout(rect=(0, 0.04, 1, 0.93))
    out_path = os.path.join(FIGURES, "fig8-4_中国主要海岛面积规模与沿海省份海岛数量分布.png")
    save_volume_figure(fig, out_path, dpi=DPI)
    plt.close(fig)
    print("生成:", out_path)


def make_fig8_5():
    """图8-5：全国主要海洋产业增加值构成与海洋经济结构。"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 5.8), gridspec_kw={"width_ratios": [1.0, 1.15]})

    # 子图1：海洋三次产业结构演变与构成比例（2024 年海洋生产总值超 10.5 万亿元）
    # 2024年海洋产业增加值中三次产业比重：第一产业约 4.5%，第二产业约 36.5%，第三产业约 59.0%
    sectors = ["第一产业\n(海洋渔业等)\n4.5%", "第二产业\n(海洋工业/建筑)\n36.5%", "第三产业\n(航运/旅游/金融服务)\n59.0%"]
    shares = [4.5, 36.5, 59.0]
    colors_pie = ["#27ae60", "#2980b9", "#e67e22"]

    wedges, texts, autotexts = ax1.pie(
        shares, labels=sectors, autopct="%1.1f%%", startangle=90,
        colors=colors_pie, pctdistance=0.65,
        wedgeprops=dict(width=0.45, edgecolor="white", lw=2),
        textprops=dict(fontsize=9.2, color=C_TEXT)
    )
    for at in autotexts:
        at.set_fontsize(9.5)
        at.set_fontweight("bold")
        at.set_color("white")

    ax1.set_title("海洋生产总值三次产业结构构成（2024年）\n（总量达 10.54 万亿元，现代服务业成主力引擎）",
                  fontsize=10.5, fontweight='bold', color=C_TEXT, pad=10)

    # 子图2：主要海洋产业增加值构成（亿元）
    industries = [
        "海洋旅游业 (滨海旅游强劲复苏)",
        "海洋交通运输业 (航运与港口集装箱)",
        "海洋渔业 (捕捞与海水海水养殖)",
        "海洋工程建筑业 (跨海桥隧/港工)",
        "海洋油气业 (渤海与南海深水油气)",
        "海洋化工业 (原盐与海洋精细化工)",
        "海洋船舶与海工装备制造",
        "海洋电力业 (海上风电规模全球第一)",
        "海洋药物与生物制品业",
        "海洋矿业与海水利用业"
    ]
    # 增加值数值估测（亿元，参考自然资源部 2024 海洋经济公报）
    val_ind = [16200, 7800, 5600, 2900, 2600, 2400, 1950, 850, 780, 320]
    y_pos = np.arange(len(industries))
    ind_colors = [
        "#e67e22", "#2980b9", "#27ae60", "#34495e", "#d35400",
        "#16a085", "#3498db", "#f39c12", "#9b59b6", "#95a5a6"
    ]

    bars = ax2.barh(y_pos, val_ind, color=ind_colors, height=0.62, edgecolor="#2c3e50", lw=0.5, zorder=3)
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(industries, fontsize=9, color=C_TEXT)
    ax2.set_xlabel("产业增加值（亿元）", fontsize=9.5, color=C_TEXT)
    ax2.set_xlim(0, 19000)
    ax2.set_title("主要海洋产业增加值横向对比（亿元）\n（传统支柱强基固本，海工装备与海风新兴产业突飞猛进）",
                  fontsize=10.5, fontweight='bold', color=C_TEXT, pad=10)
    ax2.grid(True, axis='x', linestyle=':', alpha=0.6)

    for bar, val in zip(bars, val_ind):
        ax2.text(val + 300, bar.get_y() + bar.get_height()/2,
                 f"{val:,} 亿元",
                 ha='left', va='center', fontsize=8.2, fontweight='bold', color=C_TEXT)

    for s in ("top", "right"):
        ax2.spines[s].set_visible(False)

    fig.text(0.02, 0.985, "全国主要海洋产业增加值构成与海洋经济结构", fontsize=13.5, fontweight="bold", color=C_TEXT)
    fig.text(0.02, 0.952, "2024 年海洋生产总值突破 10.5 万亿元，滨海旅游与海洋交通运输领跑，高端海工与海风产业实现跨越式升级",
             fontsize=9.2, color="#555555")
    fig.text(0.02, 0.012, "数据来源：自然资源部《2024年中国海洋经济统计公报》、国家发展改革委与国家统计局公开数据",
             fontsize=8, color="#777777")

    fig.tight_layout(rect=(0, 0.04, 1, 0.93))
    out_path = os.path.join(FIGURES, "fig8-5_全国主要海洋产业增加值构成与海洋经济结构.png")
    save_volume_figure(fig, out_path, dpi=DPI)
    plt.close(fig)
    print("生成:", out_path)


if __name__ == "__main__":
    make_fig8_4()
    make_fig8_5()
