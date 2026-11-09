# -*- coding: utf-8 -*-
"""第 6 章 自然资源与土地利用 —— 补充高质量专业图表。

fig6-6: 全国耕地质量等级构成比例（耕地金字塔与保质压力）
fig6-7: 中国重点战略性矿产对外依存度对比（资源大国与关键矿产供应链安全）
"""
from volume1_layout import save_volume_figure
import os
import sys
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import FIGURES, DPI, setup

setup()


def make_fig6_6():
    """图6-6：全国耕地质量等级构成比例。"""
    fig, ax = plt.subplots(figsize=(7.5, 5.5))

    labels = ['一至三等\n6.32亿亩',
              '四至六等\n9.47亿亩',
              '七至十等\n4.44亿亩']
    sizes = [31.24, 46.81, 21.95]
    colors = ['#27ae60', '#f39c12', '#e74c3c']
    explode = (0.04, 0.02, 0)

    wedges, texts, autotexts = ax.pie(
        sizes, explode=explode, labels=labels, autopct='%1.2f%%',
        startangle=140, colors=colors, pctdistance=0.75,
        textprops=dict(color="#2c3e50", fontsize=10.5),
        wedgeprops=dict(width=0.45, edgecolor='white', linewidth=2)
    )
    for at in autotexts:
        at.set_fontsize(10)
        at.set_fontweight('bold')

    ax.set_title("全国耕地质量等级构成（2019年评价口径）",
                 fontsize=12.5, fontweight='bold', color="#2c3e50", pad=15)

    # 中心文本注记
    ax.text(0, 0, "评价耕地面积\n20.23亿亩",
            ha='center', va='center', fontsize=10, fontweight='bold', color="#34495e")
    fig.text(0.03, 0.02, "来源：农业农村部《2019年全国耕地质量等级情况公报》",
             fontsize=8, color="#555555")

    fig.tight_layout()
    out_path = os.path.join(FIGURES, "fig6-6_全国耕地质量等级构成比例.png")
    save_volume_figure(fig, out_path, dpi=DPI)
    plt.close(fig)
    print(f"Saved {out_path}")


def make_fig6_7():
    """图6-7：中国重点战略性矿产对外依存度对比。"""
    fig, ax = plt.subplots(figsize=(10, 5.8))

    minerals = [
        "稀土", "动力煤", "炼焦煤", "天然气",
        "锂矿", "铝土矿", "原油", "铜矿", "铁矿石"
    ]
    dependency = [0.0, 7.5, 18.2, 42.5, 58.0, 65.4, 72.8, 78.5, 81.2]

    y_pos = np.arange(len(minerals))

    colors = ['#27ae60' if d < 20 else ('#f39c12' if d < 50 else '#e74c3c') for d in dependency]

    bars = ax.barh(y_pos, dependency, color=colors, edgecolor='#2c3e50', height=0.6, zorder=3)

    # 50% 安全警戒线
    ax.axvline(50, color="#c0392b", linestyle="--", linewidth=1.5, zorder=4)
    ax.text(51.5, 1.2, "50% 资源安全警戒线", color="#c0392b", fontsize=10, fontweight='bold')

    ax.set_yticks(y_pos)
    ax.set_yticklabels(minerals, fontsize=11, fontweight='bold', color="#2c3e50")
    ax.set_xlabel("对外依存度（%）", fontsize=11, color="#2c3e50")
    ax.set_title("中国主要战略性矿产对外依存度对比（2023年统计态）\n（大宗工业原料对外依存度居高不下，煤炭与稀土具备绝对自给优势）",
                 fontsize=12.5, fontweight='bold', color="#2c3e50", pad=12)
    ax.grid(True, axis='x', linestyle=':', alpha=0.6)
    ax.set_xlim(0, 100)

    for bar in bars:
        w = bar.get_width()
        if w == 0:
            ax.text(1.5, bar.get_y() + bar.get_height()/2, "净出口(自主可控)",
                    ha='left', va='center', fontsize=9.5, fontweight='bold', color="#27ae60")
        else:
            ax.text(w + 1.2, bar.get_y() + bar.get_height()/2, f"{w:.1f}%",
                    ha='left', va='center', fontsize=9.5, color="#2c3e50")

    fig.tight_layout()
    out_path = os.path.join(FIGURES, "fig6-7_中国重点战略性矿产对外依存度对比.png")
    save_volume_figure(fig, out_path, dpi=DPI)
    plt.close(fig)
    print(f"Saved {out_path}")


if __name__ == "__main__":
    make_fig6_6()
    make_fig6_7()
