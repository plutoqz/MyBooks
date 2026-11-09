# -*- coding: utf-8 -*-
"""生成第 6.2、8.1、10.3、12.3 节缺失插图：
fig6-5_三十年土地覆盖演变.png
fig8-3_三大半岛与海湾海岸特征.png
fig10-5_历史文化名城与八大古都.png
fig12-4_沿边口岸与沿海港口群.png
"""
from volume1_layout import save_volume_figure
import os
import sys

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import C_TEXT, DPI, FIGURES, setup

setup()
OUT = FIGURES


# ---------------------------------------------------------------- fig 6-5
from volume1_topics import land_cover as generate_fig6_5


# ---------------------------------------------------------------- fig 8-3
def generate_fig8_3():
    """8.1 海岸与海湾半岛：三大半岛、三大海湾与海岸线类型构成。"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.0, 5.6), gridspec_kw={"width_ratios": [1.0, 1.15]})

    # 子图1：大陆海岸线类型构成（约 1.8 万公里）
    coast_types = ["砂质海岸\n(32%)", "基岩海岸\n(28%)", "淤泥质海岸\n(24%)", "生物与人工岸线\n(16%)"]
    lens = [5760, 5040, 4320, 2880]
    colors = ["#f39c12", "#7f8c8d", "#16a085", "#2980b9"]

    wedges, texts, autotexts = ax1.pie(lens, labels=coast_types, autopct="%1.0f%%",
                                       colors=colors, startangle=140,
                                       textprops=dict(fontsize=9, color=C_TEXT),
                                       pctdistance=0.68,
                                       wedgeprops=dict(width=0.45, edgecolor="white", lw=2))
    for at in autotexts:
        at.set_fontsize(8.8)
        at.set_fontweight("bold")
        at.set_color("white")
    ax1.set_title("大陆海岸线类型构成", fontsize=11, fontweight="bold", pad=10, color=C_TEXT)

    # 子图2：三大半岛面积与三大海湾海域面积对比
    labels = ["山东半岛", "辽东半岛", "雷州半岛", "北部湾", "渤海湾", "杭州湾"]
    vals = [73000, 29400, 7800, 128000, 15900, 5000]  # 平方公里
    group_colors = ["#c0392b", "#c0392b", "#c0392b", "#2980b9", "#2980b9", "#2980b9"]

    y_pos = np.arange(len(labels))
    bars = ax2.barh(y_pos, vals, color=group_colors, height=0.58, zorder=3)
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(labels, fontsize=9.5)
    ax2.set_xlim(0, 180000)
    ax2.set_xlabel("面积（km²）", fontsize=9, color="#666666")
    ax2.set_title("三大半岛（陆域）与主要海湾（水域）规模对比", fontsize=11, fontweight="bold", pad=10, color=C_TEXT)
    ax2.grid(axis="x", ls=":", color="#e0e0e0", zorder=0)

    for b, v in zip(bars, vals):
        ax2.text(v * 1.15, b.get_y() + b.get_height() / 2, f"{v:,} km²", va="center", fontsize=8.6, color=C_TEXT)

    for s in ("top", "right"):
        ax2.spines[s].set_visible(False)

    # 图例
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor="#c0392b", label="主要半岛（陆地面积）"),
                       Patch(facecolor="#2980b9", label="主要海湾（水域面积）")]
    ax2.legend(handles=legend_elements, loc="upper center",
               bbox_to_anchor=(0.5, -0.27), fontsize=8.6, frameon=False)

    fig.text(0.02, 0.98, "中国三大半岛、主要海湾与大陆海岸类型构成", fontsize=13.5, fontweight="bold", color=C_TEXT)
    fig.text(0.02, 0.94, "大陆海岸线约 1.8 万公里；岸线类型、半岛陆域与海湾水域分别比较", fontsize=9.2, color="#555555")
    fig.text(0.02, 0.015, "数据来源：自然资源部《中国海洋统计年鉴》、通行海洋地理教材与沿海港口岸线专项普查", fontsize=8, color="#777777")

    fig.tight_layout(rect=(0, 0.04, 1, 0.92))
    path = os.path.join(OUT, "fig8-3_三大半岛与海湾海岸特征.png")
    save_volume_figure(fig, path, dpi=DPI)
    plt.close(fig)
    print("生成:", path)


# ---------------------------------------------------------------- fig 10-5
def generate_fig10_5():
    """10.3 历史文化名城：国家历史文化名城类型结构与八大古都谱系。"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.2, 5.8), gridspec_kw={"width_ratios": [1.1, 1.0]})

    # 子图1：八大古都建都年限（累计年数）与建都朝代跨度
    capitals = ["西安", "洛阳", "北京", "南京", "开封", "杭州", "安阳", "郑州"]
    years_as_cap = [1070, 850, 870, 450, 360, 210, 255, 180]
    c_bars = ["#8e2b20", "#9b59b6", "#c0392b", "#2980b9", "#d35400", "#16a085", "#7f8c8d", "#34495e"]

    x = np.arange(len(capitals))
    bars = ax1.bar(x, years_as_cap, color=c_bars, width=0.55, zorder=3)
    ax1.set_xticks(x)
    ax1.set_xticklabels(capitals, fontsize=9.5, fontweight="bold")
    ax1.set_ylabel("累计作为正统/主要王朝国都年限（年）", fontsize=9, color="#666666")
    ax1.set_ylim(0, 1250)
    ax1.set_title("中国“八大古都”建都累计历史年限谱系", fontsize=11, fontweight="bold", pad=10, color=C_TEXT)
    ax1.grid(axis="y", ls=":", color="#e0e0e0", zorder=0)

    for b, v in zip(bars, years_as_cap):
        ax1.text(b.get_x() + b.get_width() / 2, v + 25, f"{v}年", ha="center", fontsize=8.8, fontweight="bold", color=C_TEXT)

    for s in ("top", "right"):
        ax1.spines[s].set_visible(False)

    # 子图2：全国 140 余座国家历史文化名城五大类型构成与领先省份
    types = ["传统风貌型\n(平遥/丽江/歙县等)", "古都型\n(西安/洛阳/北京等)", "近代史迹型\n(上海/遵义/延安等)", "风景名胜型\n(桂林/承德/黄山等)", "地方特色与民族型\n(喀什/拉萨/大理等)"]
    counts = [42, 33, 27, 22, 18]
    type_colors = ["#e67e22", "#c0392b", "#3498db", "#2ecc71", "#9b59b6"]

    y_pos = np.arange(len(types))
    bars2 = ax2.barh(y_pos, counts, color=type_colors, height=0.52, zorder=3)
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(types, fontsize=8.8)
    ax2.set_xlim(0, 52)
    ax2.set_xlabel("名城数量（座，截至 2024 年底共 142 座）", fontsize=9, color="#666666")
    ax2.set_title("国家历史文化名城五大分类构成", fontsize=11, fontweight="bold", pad=10, color=C_TEXT)
    ax2.grid(axis="x", ls=":", color="#e0e0e0", zorder=0)

    for b, v in zip(bars2, counts):
        ax2.text(v + 1.0, b.get_y() + b.get_height() / 2, f"{v} 座", va="center", fontsize=9, fontweight="bold", color=C_TEXT)

    for s in ("top", "right"):
        ax2.spines[s].set_visible(False)

    fig.text(0.02, 0.98, "国家历史文化名城类型结构与八大古都谱系", fontsize=13.5, fontweight="bold", color=C_TEXT)
    fig.text(0.02, 0.94, "全国已公布逾 140 座历史文化名城，古都重心沿“西安—洛阳—开封—北京”向东向北演变，体现地缘与政治经济重心的历史变迁", fontsize=9.2, color="#555555")
    fig.text(0.02, 0.015, "数据来源：国务院批复历批国家历史文化名城名录、国家文物局《中国文物地图集》", fontsize=8, color="#777777")

    fig.tight_layout(rect=(0, 0.04, 1, 0.92))
    path = os.path.join(OUT, "fig10-7_历史文化名城与八大古都.png")
    save_volume_figure(fig, path, dpi=DPI)
    plt.close(fig)
    print("生成:", path)


# ---------------------------------------------------------------- fig 12-4
from volume1_topics import port_gateways as generate_fig12_4


if __name__ == "__main__":
    generate_fig6_5()
    generate_fig8_3()
    generate_fig10_5()
    generate_fig12_4()
