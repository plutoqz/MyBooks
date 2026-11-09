# -*- coding: utf-8 -*-
"""第 9 章 人口与民族 —— 补充高水准专业图表。

fig9-7: 全国主要省份跨省人口净流入流出格局
fig9-8: 胡焕庸线两侧水热土地与人口经济要素全景对比
"""
from volume1_layout import save_volume_figure
import os
import sys
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import FIGURES, DPI, setup, C_TEXT

setup()


def make_fig9_7():
    """图9-7：全国主要省份跨省人口净流入流出格局。"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.8, 5.8), gridspec_kw={"width_ratios": [1.1, 1.0]})

    # 子图1：七普主要跨省净流入与净流出省份（万人）
    # 净流入省份（正值，蓝绿色系）
    in_provs = ["广东", "浙江", "江苏", "上海", "山东", "北京", "福建", "新疆"]
    in_vals = [2865, 1618, 1030, 1048, 412, 842, 489, 339]

    # 净流出省份（负值，暖橙红色系）
    out_provs = ["河南", "安徽", "四川", "贵州", "广西", "湖南", "江西", "湖北"]
    out_vals = [-1610, -1152, -1044, -852, -812, -785, -675, -512]

    # 拼合
    all_provs = in_provs[::-1] + out_provs
    all_vals = in_vals[::-1] + out_vals
    colors = ["#27ae60" if v > 0 else "#c0392b" for v in all_vals]

    y_pos = np.arange(len(all_provs))
    bars = ax1.barh(y_pos, all_vals, color=colors, height=0.62, edgecolor="#2c3e50", lw=0.5, zorder=3)
    ax1.axvline(0, color="#2c3e50", lw=1.0)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(all_provs, fontsize=9.2, fontweight="bold", color=C_TEXT)
    ax1.set_xlabel("净跨省迁移人口规模（万人，流入为正/流出为负）", fontsize=9.5, color=C_TEXT)
    ax1.set_xlim(-2000, 3200)
    ax1.set_title("第七次全国人口普查跨省人口净流入与净流出大省对比\n（广东、浙江、江苏吸纳全国近六成跨省净流入人口）",
                  fontsize=10.5, fontweight="bold", color=C_TEXT, pad=10)
    ax1.grid(True, axis="x", linestyle=":", alpha=0.6)

    for bar, val in zip(bars, all_vals):
        if val > 0:
            ax1.text(val + 60, bar.get_y() + bar.get_height()/2, f"+{val:,}万",
                     ha="left", va="center", fontsize=8.0, fontweight="bold", color="#1e8449")
        else:
            ax1.text(val - 60, bar.get_y() + bar.get_height()/2, f"{val:,}万",
                     ha="right", va="center", fontsize=8.0, fontweight="bold", color="#922b21")

    for s in ("top", "right"):
        ax1.spines[s].set_visible(False)

    # 子图2：六普至七普（2010—2020）各经济区常住人口增减构成
    regions = ["东部地区\n(+5432万)", "西部地区\n(+1736万)", "中部地区\n(+478万)", "东北地区\n(-1099万)"]
    changes = [5432, 1736, 478, -1099]
    reg_colors = ["#2980b9", "#16a085", "#f39c12", "#e74c3c"]

    bars2 = ax2.bar(regions, changes, color=reg_colors, width=0.55, edgecolor="#2c3e50", lw=0.6, zorder=3)
    ax2.axhline(0, color="#2c3e50", lw=1.0)
    ax2.set_ylabel("十年常住人口增减规模（万人）", fontsize=9.5, color=C_TEXT)
    ax2.set_ylim(-1600, 6500)
    ax2.set_title("四大板块十年常住人口增减分化格局（2010—2020）\n（东部经济带持续强劲虹吸，中西部省会成为新兴回流增长极）",
                  fontsize=10.5, fontweight="bold", color=C_TEXT, pad=10)
    ax2.grid(True, axis="y", linestyle=":", alpha=0.6)

    for b, c in zip(bars2, changes):
        if c > 0:
            ax2.text(b.get_x() + b.get_width()/2, c + 150, f"+{c:,} 万",
                     ha="center", va="bottom", fontsize=8.8, fontweight="bold", color="#1a5276")
        else:
            ax2.text(b.get_x() + b.get_width()/2, c - 280, f"{c:,} 万",
                     ha="center", va="top", fontsize=8.8, fontweight="bold", color="#922b21")

    for s in ("top", "right"):
        ax2.spines[s].set_visible(False)

    fig.text(0.02, 0.985, "全国主要省份跨省人口净流入流出格局与区域演化", fontsize=13.5, fontweight="bold", color=C_TEXT)
    fig.text(0.02, 0.952, "东南沿海三大城市群为跨省流动主要吸纳地；豫、皖、川、黔跨省外出规模大，但中西部核心省会近年来显现明显人口回流",
             fontsize=9.2, color="#555555")
    fig.text(0.02, 0.012, "数据来源：国家统计局《第六次、第七次全国人口普查主要数据公报》与各省统计年鉴",
             fontsize=8, color="#777777")

    fig.tight_layout(rect=(0, 0.04, 1, 0.93))
    out_path = os.path.join(FIGURES, "fig9-7_全国主要省份跨省人口净流入流出格局.png")
    save_volume_figure(fig, out_path, dpi=DPI)
    plt.close(fig)
    print("生成:", out_path)


def make_fig9_8():
    """图9-8：胡焕庸线两侧水热土地与人口经济要素全景对比。"""
    fig, ax = plt.subplots(figsize=(10.8, 5.8))

    indicators = [
        "陆地国土面积",
        "全国总人口 (常住)",
        "国内生产总值 (GDP)",
        "全国有效耕地面积",
        "地表多年平均径流量",
        "森林活立木总蓄积量",
        "大中城市与城镇化集聚",
        "粮食总产量"
    ]
    # 东南半壁 vs 西北半壁占比（%）
    se_shares = [43.2, 94.1, 95.7, 86.4, 95.8, 88.5, 93.6, 88.2]
    nw_shares = [100 - s for s in se_shares]

    y_pos = np.arange(len(indicators))

    # 堆叠条形图
    b1 = ax.barh(y_pos, se_shares, color="#c0392b", edgecolor="white", height=0.58, label="东南半壁（胡线以东）", zorder=3)
    b2 = ax.barh(y_pos, nw_shares, left=se_shares, color="#2980b9", edgecolor="white", height=0.58, label="西北半壁（胡线以西）", zorder=3)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(indicators, fontsize=10, fontweight="bold", color=C_TEXT)
    ax.set_xlim(0, 100)
    ax.set_xlabel("要素占比（%）", fontsize=10.5, color=C_TEXT)
    ax.set_title("胡焕庸线两侧主要自然水热与人口经济要素对比（%）\n（43% 的季风国土承载了 94% 的人口、95% 的 GDP 与 96% 的水资源，格局九十年坚如磐石）",
                 fontsize=11.5, fontweight="bold", color=C_TEXT, pad=12)
    ax.grid(True, axis="x", linestyle=":", alpha=0.5)

    # 标注数值
    for i, (se, nw) in enumerate(zip(se_shares, nw_shares)):
        ax.text(se / 2, i, f"{se:.1f}%", ha="center", va="center", color="white", fontweight="bold", fontsize=9.2)
        ax.text(se + nw / 2, i, f"{nw:.1f}%", ha="center", va="center", color="white", fontweight="bold", fontsize=9.2)

    ax.axvline(50, color="#2c3e50", ls="--", lw=0.8, alpha=0.7)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.20),
              ncol=2, fontsize=9.8, frameon=False)

    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

    fig.tight_layout(rect=(0, 0.05, 1, 0.96))
    out_path = os.path.join(FIGURES, "fig9-8_胡焕庸线两侧水热土地与人口经济要素对比.png")
    save_volume_figure(fig, out_path, dpi=DPI)
    plt.close(fig)
    print("生成:", out_path)


if __name__ == "__main__":
    make_fig9_7()
    make_fig9_8()
