# -*- coding: utf-8 -*-
"""第 5 章 河流与湖泊 —— 补充高水准专业统计图表。

fig5-8: 中国主要江河年径流量与流域面积对比（产水模数与水力反差）
fig5-9: 主要水资源分区开发利用率与人均水资源量对比（南丰北缺与水资源红线）
fig5-10: 1950—2023年黄河潼关站年代际输沙量演变（黄土高原治理与河沙断崖式锐减）
"""
from volume1_layout import save_volume_figure
import os
import sys
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import FIGURES, DPI, setup

setup()


def make_fig5_8():
    """图5-8：中国主要江河年径流量与流域面积对比。"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 7), sharey=True)

    rivers = [
        "长江", "珠江", "黑龙江(境内)", "雅鲁藏布江", "澜沧江(境内)",
        "怒江(境内)", "淮河", "黄河", "海河", "辽河", "塔里木河(干流)"
    ]
    # 年径流量 (亿 m³)
    runoff = [9600, 3360, 2720, 1650, 740, 690, 620, 580, 220, 150, 50]
    # 流域面积 (万 km²)
    area = [180.0, 45.4, 88.7, 24.0, 16.7, 13.8, 27.0, 79.5, 26.4, 22.9, 102.0]

    y = np.arange(len(rivers))
    for ax, values, color, title, unit in [
        (ax1, runoff, "#2369A0", "多年平均年径流量", "亿 m³"),
        (ax2, area, "#B26815", "流域面积", "万 km²"),
    ]:
        bars = ax.barh(y, values, height=0.6, color=color)
        for bar, value in zip(bars, values):
            ax.text(value + max(values) * 0.02, bar.get_y() + 0.3,
                    f"{value:g}", va="center", fontsize=9)
        ax.set_xlim(0, max(values) * 1.18)
        ax.set_xlabel(unit)
        ax.set_title(title, fontsize=11)
        ax.spines[["top", "right", "left"]].set_visible(False)
    ax1.set_yticks(y, rivers)
    ax1.invert_yaxis()
    fig.text(0.025, 0.98, "主要江河年径流量与流域面积", fontsize=15, weight="bold")
    fig.text(0.025, 0.93, "两项指标分别使用独立数轴，河流按同一顺序对齐", fontsize=9)
    fig.tight_layout(rect=(0, 0.04, 1, 0.86))
    out_path = os.path.join(FIGURES, "fig5-8_中国主要江河年径流量与流域面积对比.png")
    save_volume_figure(fig, out_path, dpi=DPI)
    plt.close(fig)
    print(f"Saved {out_path}")


def make_fig5_9():
    """图5-9：主要水资源分区水资源开发利用率与人均水资源量对比。"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6), sharey=True)

    regions = [
        "西南诸河", "东南诸河", "珠江流域", "长江流域", "松花江区",
        "辽河流域", "黄河流域", "淮河流域", "海河流域"
    ]
    # 水资源开发利用率 (%)
    exploit_rate = [1.8, 14.5, 16.2, 19.5, 31.0, 68.5, 80.2, 65.4, 106.0]
    # 人均水资源量 (m³/人)
    per_capita = [22500, 3420, 3650, 2210, 1850, 780, 450, 480, 250]

    y_pos = np.arange(len(regions))

    # 左子图：开发利用率（条形图）
    bars1 = ax1.barh(y_pos, exploit_rate, color=['#27ae60' if r < 40 else '#e74c3c' for r in exploit_rate],
                     edgecolor='white', height=0.6, zorder=3)
    # 40% 生态警戒线
    ax1.axvline(40, color="#c0392b", linestyle="--", linewidth=1.5, zorder=4)
    ax1.text(42, 1.5, "40% 国际公认\n生态警戒线", color="#c0392b", fontsize=9.5, fontweight='bold')

    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(regions, fontsize=10.5, fontweight='bold', color="#2c3e50")
    ax1.set_xlabel("水资源开发利用率（%）", fontsize=10.5, color="#2c3e50")
    ax1.set_title("水资源开发利用率\n（北方三大流域极度超载，南方尚有充裕空间）",
                  fontsize=11.5, fontweight='bold', color="#2c3e50", pad=10)
    ax1.grid(True, axis='x', linestyle=':', alpha=0.6)
    ax1.set_xlim(0, 120)

    # 数值标注
    for bar in bars1:
        w = bar.get_width()
        ax1.text(w + 1.5, bar.get_y() + bar.get_height()/2, f"{w:.1f}%",
                 ha='left', va='center', fontsize=9, color="#2c3e50")

    # 右子图：人均水资源量（条形图）
    bars2 = ax2.barh(y_pos, per_capita, color="#2980b9", edgecolor='white', height=0.6, zorder=3)
    # 1700 m³ 缺水警戒线与 500 m³ 极度缺水线
    ax2.axvline(1700, color="#f39c12", linestyle="--", linewidth=1.2, zorder=4)
    ax2.text(1800, 7.5, "1700m³ 国际缺水警戒线", color="#d35400", fontsize=9)
    ax2.axvline(500, color="#c0392b", linestyle="--", linewidth=1.2, zorder=4)
    ax2.text(600, 6.2, "500m³ 极度缺水线", color="#c0392b", fontsize=9)

    ax2.set_xlabel("人均水资源量（m³/人）", fontsize=10.5, color="#2c3e50")
    ax2.set_title("人均水资源拥有量\n（海河、淮河、黄河人均水资源不及全国均值1/4）",
                  fontsize=11.5, fontweight='bold', color="#2c3e50", pad=10)
    ax2.grid(True, axis='x', linestyle=':', alpha=0.6)
    ax2.set_xlim(0, 25000)

    for bar in bars2:
        w = bar.get_width()
        ax2.text(w + 300, bar.get_y() + bar.get_height()/2, f"{int(w)}",
                 ha='left', va='center', fontsize=9, color="#2c3e50")

    fig.tight_layout()
    out_path = os.path.join(FIGURES, "fig5-9_主要水资源分区开发利用率与人均水资源量对比.png")
    save_volume_figure(fig, out_path, dpi=DPI)
    plt.close(fig)
    print(f"Saved {out_path}")


def make_fig5_10():
    """图5-10：1950—2023年黄河潼关水文站年代际输沙量演变。"""
    fig, ax = plt.subplots(figsize=(10, 5.5))

    decades = ["1950s", "1960s", "1970s", "1980s", "1990s", "2000s", "2010s", "2020—23"]
    sediment = [13.5, 14.8, 12.1, 7.9, 8.2, 2.6, 1.8, 1.45]  # 亿吨/年

    colors = ['#c0392b', '#c0392b', '#d35400', '#e67e22', '#f39c12', '#27ae60', '#2ecc71', '#1abc9c']
    bars = ax.bar(decades, sediment, color=colors, edgecolor="#2c3e50", width=0.55, zorder=3)

    # 折线连接与点
    ax.plot(decades, sediment, color="#2c3e50", marker='o', linewidth=2, markersize=6, zorder=4)

    # 标注数值
    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + 0.35, f"{h:.2f}亿吨",
                ha='center', va='bottom', fontsize=9.5, fontweight='bold', color="#2c3e50")

    # 历史基线与治理阶段注记
    ax.axhline(16.0, color="#7f8c8d", linestyle=":", linewidth=1.2)
    ax.text(0.2, 16.2, "历史长期年均输沙量（约16亿吨）", color="#7f8c8d", fontsize=9)

    fig.text(0.025, 0.015,
             "流域治理措施包括退耕还林还草、淤地坝建设与小浪底调水调沙等。",
             fontsize=8.5, color="#555555")

    ax.set_title("1950—2023年黄河潼关站年均输沙量年代际演变\n（黄河流域泥沙实现历史性断崖式下降）",
                 fontsize=13, fontweight='bold', color="#2c3e50", pad=12)
    ax.set_ylabel("年代际年均输沙量（亿吨/年）", fontsize=11, color="#2c3e50")
    ax.set_xlabel("年代", fontsize=11, color="#2c3e50")
    ax.set_ylim(0, 18)
    ax.grid(True, axis='y', linestyle='--', alpha=0.5)

    fig.tight_layout()
    out_path = os.path.join(FIGURES, "fig5-10_黄河潼关水文站输沙量年代际演变.png")
    save_volume_figure(fig, out_path, dpi=DPI)
    plt.close(fig)
    print(f"Saved {out_path}")


if __name__ == "__main__":
    make_fig5_8()
    make_fig5_9()
    make_fig5_10()
