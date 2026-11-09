# -*- coding: utf-8 -*-
"""第 12 章 交通地理 —— 规范图表并补充高水准专业学术图表。

图表编排：
fig12-1: 交通网络增长 (已有)
fig12-2: 货运结构与港口 (已有)
fig12-3: 八纵八横高铁网 (已有)
fig12-4: 极端地质铁路工程攻坚与川藏铁路 (全新生成)
fig12-5: 沿边口岸与沿海港口群 (原 fig12-4 重命名)
fig12-6: 中欧班列三大走廊与西部陆海新通道 (全新生成)
fig12-7: 历史地理通道与京杭大运河 (原 fig12-5 重命名)
fig12-8: 大运河历史水工演进与平陆运河江海联运 (全新生成)
"""
from volume1_layout import save_volume_figure
import os
import sys
import shutil
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import FIGURES, DPI, setup, C_TEXT

setup()


def standardize_existing_figs():
    """重命名原 fig12-5 -> fig12-7, fig12-4 -> fig12-5。"""
    old_5 = os.path.join(FIGURES, "fig12-5_历史地理通道与京杭大运河.png")
    new_7 = os.path.join(FIGURES, "fig12-7_历史地理通道与京杭大运河.png")
    old_4 = os.path.join(FIGURES, "fig12-4_沿边口岸与沿海港口群.png")
    new_5 = os.path.join(FIGURES, "fig12-5_沿边口岸与沿海港口群.png")

    if os.path.exists(old_5):
        shutil.move(old_5, new_7)
        print(f"Move: {os.path.basename(old_5)} -> {os.path.basename(new_7)}")

    if os.path.exists(old_4):
        shutil.move(old_4, new_5)
        print(f"Move: {os.path.basename(old_4)} -> {os.path.basename(new_5)}")


def make_fig12_4():
    """图12-4：极端地质铁路工程攻坚与川藏铁路。"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.0, 5.8), gridspec_kw={"width_ratios": [1.05, 1.05]})

    # 子图1：中国五大标志性高难度铁路工程地质挑战与指标对比
    railways = [
        "成昆铁路\n(地质博物馆·滑坡泥石流)",
        "青藏铁路\n(高寒缺氧·550km多年冻土)",
        "兰新高铁\n(百里风区·戈壁强横风防风障)",
        "贵南高铁\n(喀斯特峰丛·桥隧比超90%)",
        "川藏铁路(雅林段)\n(八起八落·高地温岩爆断裂带)"
    ]
    bridge_tunnel_ratio = [41.6, 16.0, 32.0, 92.5, 95.0]  # 桥隧比 (%)
    max_elev = [2280, 5072, 3607, 1200, 4400]              # 最高海拔/轨顶标高 (米)
    colors_proj = ["#7f8c8d", "#2980b9", "#f39c12", "#16a085", "#c0392b"]

    y_pos = np.arange(len(railways))
    bars = ax1.barh(y_pos, bridge_tunnel_ratio, color=colors_proj, height=0.55, edgecolor="#2c3e50", lw=0.5, zorder=3)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(railways, fontsize=8.6, fontweight="bold", color=C_TEXT)
    ax1.set_xlabel("全线桥隧占比 (%)", fontsize=9.2, color=C_TEXT)
    ax1.set_xlim(0, 115)
    ax1.set_title("中国代表性极端地质环境铁路工程地质挑战对比\n（从成昆突破到川藏超级工程桥隧比达95%）",
                  fontsize=10.5, fontweight="bold", color=C_TEXT, pad=10)
    ax1.grid(True, axis="x", linestyle=":", alpha=0.6)

    for bar, ratio, elev in zip(bars, bridge_tunnel_ratio, max_elev):
        ax1.text(ratio + 1.2, bar.get_y() + bar.get_height()/2,
                 f"{ratio:.1f}% (最高轨标{elev:,}m)",
                 va="center", fontsize=8.2, fontweight="bold", color=C_TEXT)

    for s in ("top", "right"):
        ax1.spines[s].set_visible(False)

    # 子图2：川藏铁路雅安至林芝段地形剖面与关键控制性深埋特长隧道
    sections = [
        "雅安起点 (海拔约600m)",
        "大渡河特大桥 (悬索桥高落差)",
        "折多山隧道 (埋深超千米·高地温)",
        "雅砻江特大桥 (深切峡谷过河)",
        "沙鲁里山隧道 (超长岩爆高风险)",
        "金沙江特大桥 (横跨川藏省界)",
        "伯舒拉岭隧道 (全线最长·38公里)",
        "易贡藏布特大桥 (大滑坡次生灾害)",
        "林芝终点 (海拔约3000m)"
    ]
    elevations = [600, 1450, 3800, 2600, 4200, 2700, 4350, 2200, 3000]

    y_pos2 = np.arange(len(sections))
    ax2.plot(elevations, y_pos2, marker="o", color="#c0392b", lw=2.0, ms=6, zorder=4)
    ax2.set_yticks(y_pos2)
    ax2.set_yticklabels(sections, fontsize=8.6, fontweight="bold", color=C_TEXT)
    ax2.set_xlabel("沿线地表与工程关键节点海拔标高（米）", fontsize=9.2, color=C_TEXT)
    ax2.set_xlim(300, 4800)
    ax2.set_title("川藏铁路雅林段“八起八落”极端地形梯度与重大控制工程\n（横穿7大江河、8大雪山与多条全新世活动断裂带）",
                  fontsize=10.5, fontweight="bold", color=C_TEXT, pad=10)
    ax2.grid(True, linestyle=":", alpha=0.6)

    for x_val, y_val in zip(elevations, y_pos2):
        ax2.text(x_val + 70, y_val, f"{x_val}m", va="center", fontsize=8.0, fontweight="bold", color="#922b21")

    for s in ("top", "right"):
        ax2.spines[s].set_visible(False)

    fig.text(0.02, 0.98, "中国极端地质环境铁路工程攻坚与川藏铁路地标",
             fontsize=13.5, fontweight="bold", color=C_TEXT)
    fig.text(0.02, 0.94,
             "从冻土、风沙、喀斯特溶洞到青藏高原横断山强烈构造运动带，中国铁路工程书写世界山地轨道交通极限篇章",
             fontsize=9.2, color="#555555")
    fig.text(0.02, 0.015,
             "数据来源：中国国家铁路集团公开工程技术公报、中铁二院川藏铁路勘察设计科学报告",
             fontsize=8.0, color="#777777")

    fig.tight_layout(rect=(0, 0.04, 1, 0.92))
    path = os.path.join(FIGURES, "fig12-4_极端地质铁路工程攻坚与川藏铁路.png")
    save_volume_figure(fig, path, dpi=DPI)
    plt.close(fig)
    print("生成:", path)


from volume1_topics import rail_corridors as make_fig12_6


def make_fig12_8():
    """图12-8：大运河历史水工演进与平陆运河江海联运。"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.0, 5.8), gridspec_kw={"width_ratios": [1.05, 1.05]})

    # 子图1：隋唐运河 vs 京杭运河核心水工参数与通航里程对比
    canals = [
        "隋唐大运河\n(以洛阳为中心放射·辐射海河淮河黄河长江)",
        "元明清京杭大运河\n(郭守敬截弯取直·直达北京)",
        "京杭大运河(现代通航段)\n(微山湖至杭州江南运河·千吨级航道)"
    ]
    total_km = [2700, 1794, 877]      # 全线通航里程 (km)
    annual_freight = [150, 450, 32000] # 年货运量 (万吨，现代段突破3.2亿吨)
    colors_c = ["#d35400", "#c0392b", "#2980b9"]

    y_pos = np.arange(len(canals))
    bars = ax1.barh(y_pos, total_km, color=colors_c, height=0.5, edgecolor="#2c3e50", lw=0.5, zorder=3)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(canals, fontsize=8.6, fontweight="bold", color=C_TEXT)
    ax1.set_xlabel("运河全线或通航里程（公里）", fontsize=9.2, color=C_TEXT)
    ax1.set_xlim(0, 3200)
    ax1.set_title("中国大运河历史形制变迁与现代内河黄金水道\n（隋唐洛阳中心枢纽到元大都截弯取直，苏南段货运超莱茵河）",
                  fontsize=10.5, fontweight="bold", color=C_TEXT, pad=10)
    ax1.grid(True, axis="x", linestyle=":", alpha=0.6)

    for bar, km, fr in zip(bars, total_km, annual_freight):
        if fr > 10000:
            f_str = f"年货运量超 {fr/10000:.1f} 亿吨"
        else:
            f_str = f"漕运粮食约 {fr} 万吨"
        ax1.text(km + 50, bar.get_y() + bar.get_height()/2,
                 f"{km:,} km ({f_str})",
                 va="center", fontsize=8.2, fontweight="bold", color=C_TEXT)

    for s in ("top", "right"):
        ax1.spines[s].set_visible(False)

    # 子图2：平陆运河（世纪工程·全长134公里）越岭通航阶梯工程剖面
    steps = [
        "平塘江口 (西江干流平南/横州起点)",
        "马道梯级枢纽 (第一级大型省水船闸)",
        "企石梯级枢纽 (第二级船闸·越岭分水岭)",
        "青年梯级枢纽 (第三级入海防潮防汛船闸)",
        "钦州沙井港区 (北部湾茅尾海入海口)"
    ]
    # 水位落差或距起点里程 (公里)
    step_km = [0.0, 32.5, 61.2, 98.4, 134.2]
    water_drops = [65.0, 42.0, 18.0, 5.0, 0.0] # 相对海平面高程 (米)

    y_pos2 = np.arange(len(steps))
    bars2 = ax2.barh(y_pos2, step_km, color="#117a65", height=0.5, edgecolor="#0e6251", lw=0.5, zorder=3)
    ax2.set_yticks(y_pos2)
    ax2.set_yticklabels(steps, fontsize=8.6, fontweight="bold", color=C_TEXT)
    ax2.set_xlabel("运河自西江起点向下游里程（公里）", fontsize=9.2, color=C_TEXT)
    ax2.set_xlim(0, 160)
    ax2.set_title("世纪工程平陆运河（在建·全长134.2公里）梯级船闸剖面\n（连通珠江水系与北部湾，西南货物出海运距缩短560公里）",
                  fontsize=10.5, fontweight="bold", color=C_TEXT, pad=10)
    ax2.grid(True, axis="x", linestyle=":", alpha=0.6)

    for bar, d, wd in zip(bars2, step_km, water_drops):
        ax2.text(d + 2.5, bar.get_y() + bar.get_height()/2,
                 f"{d:.1f} km  [水位高程~{wd:.0f}m]",
                 va="center", fontsize=8.0, fontweight="bold", color=C_TEXT)

    for s in ("top", "right"):
        ax2.spines[s].set_visible(False)

    fig.text(0.02, 0.98, "中国历史运河水工演进与新时代平陆运河出海新通道",
             fontsize=13.5, fontweight="bold", color=C_TEXT)
    fig.text(0.02, 0.94,
             "京杭大运河沟通五大水系成就华夏大一统经济命脉，新时代平陆运河重构西南江海联运国际物流大通道",
             fontsize=9.2, color="#555555")
    fig.text(0.02, 0.015,
             "数据来源：交通运输部水运局水运年鉴、平陆运河工程建设指挥部公开规划设计技术方案",
             fontsize=8.0, color="#777777")

    fig.tight_layout(rect=(0, 0.04, 1, 0.92))
    path = os.path.join(FIGURES, "fig12-8_大运河历史水工演进与平陆运河江海联运.png")
    save_volume_figure(fig, path, dpi=DPI)
    plt.close(fig)
    print("生成:", path)


if __name__ == "__main__":
    standardize_existing_figs()
    make_fig12_4()
    make_fig12_6()
    make_fig12_8()
