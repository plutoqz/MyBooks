# -*- coding: utf-8 -*-
"""第 11 章 经济地理 —— 规范图表并补充高水准专业学术图表。

图表总览：
fig11-1: 经济总量与人均 (已有)
fig11-2: 分省GDP排序 (已有)
fig11-3: 四大板块 (已有)
fig11-4: 粮食产量 (已有)
fig11-5: 粮食作物优势区 (已有)
fig11-6: 能源消费结构 (已有)
fig11-7: 四大工业基地与先进制造业集群 (全新生成)
fig11-8: 重大区域战略 (原 fig11-7 重命名)
fig11-9: 风光大基地与东数西算格局 (原 fig11-8 重命名)
fig11-10: 海上风电集群与特高压外送通道 (全新生成)
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
    """重命名原 fig11-7 和 fig11-8 为连续编号。"""
    old_7 = os.path.join(FIGURES, "fig11-7_重大区域战略.png")
    new_8 = os.path.join(FIGURES, "fig11-8_重大区域战略.png")
    old_8 = os.path.join(FIGURES, "fig11-8_风光大基地与东数西算格局.png")
    new_9 = os.path.join(FIGURES, "fig11-9_风光大基地与东数西算格局.png")

    # 先处理 old_8 -> new_9，避免覆盖
    if os.path.exists(old_8):
        shutil.move(old_8, new_9)
        print(f"Move: {os.path.basename(old_8)} -> {os.path.basename(new_9)}")

    if os.path.exists(old_7):
        shutil.move(old_7, new_8)
        print(f"Move: {os.path.basename(old_7)} -> {os.path.basename(new_8)}")


def make_fig11_7():
    """图11-7：四大工业基地与先进制造业集群。"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.0, 5.8), gridspec_kw={"width_ratios": [1.05, 1.05]})

    # 子图1：四大传统工业基地发展特征与综合实力对比
    bases = [
        "辽中南工业基地\n(重工业基地·装备钢铁)",
        "京津唐工业基地\n(北方最大综合性·高科技研发)",
        "沪宁杭工业基地\n(全国最大综合性·集成电路/高端制造)",
        "珠江三角洲工业基地\n(外向型与智能硬件·消费电子代工)"
    ]
    gdp_share = [4.5, 9.8, 23.5, 12.8]  # 工业规模占全国比重估算值 (%)
    density_score = [72, 85, 98, 95]     # 产业链完备度指数 (0-100)
    colors_base = ["#7f8c8d", "#2980b9", "#c0392b", "#27ae60"]

    y_pos = np.arange(len(bases))
    bars = ax1.barh(y_pos, gdp_share, color=colors_base, height=0.55, edgecolor="#2c3e50", lw=0.5, zorder=3)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(bases, fontsize=9.0, fontweight="bold", color=C_TEXT)
    ax1.set_xlabel("制造业增加值占全国估算份额 (%)", fontsize=9.2, color=C_TEXT)
    ax1.set_xlim(0, 30)
    ax1.set_title("中国四大传统工业基地体量份额与支柱门类\n（从老东北重工业摇篮到沿海巨型制造业基地）",
                  fontsize=10.5, fontweight="bold", color=C_TEXT, pad=10)
    ax1.grid(True, axis="x", linestyle=":", alpha=0.6)

    for bar, val in zip(bars, gdp_share):
        ax1.text(val + 0.6, bar.get_y() + bar.get_height()/2,
                 f"{val:.1f}%",
                 va="center", fontsize=8.6, fontweight="bold", color=C_TEXT)

    for s in ("top", "right"):
        ax1.spines[s].set_visible(False)

    # 子图2：45个国家级先进制造业集群六大战略领域构成与代表性集群
    fields = [
        "新一代信息技术 (10个·广深/苏锡常/成渝)",
        "高端装备制造 (11个·长株潭工程机械/沈阳等)",
        "新材料产业 (6个·徐州工程机械/宁波磁性等)",
        "生物医药与高端医疗 (5个·泰州医美/沪苏药谷)",
        "新能源与智能网联汽车 (8个·上海/合肥/广佛)",
        "绿色石化与高端消费品 (5个·东营化工/南通家纺)"
    ]
    counts = [10, 11, 6, 5, 8, 5]
    colors_clusters = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]

    y_pos2 = np.arange(len(fields))
    bars2 = ax2.barh(y_pos2, counts, color=colors_clusters, height=0.55, edgecolor="#2c3e50", lw=0.5, zorder=3)
    ax2.set_yticks(y_pos2)
    ax2.set_yticklabels(fields, fontsize=8.6, fontweight="bold", color=C_TEXT)
    ax2.set_xlabel("国家级先进制造业集群数量（个）", fontsize=9.2, color=C_TEXT)
    ax2.set_xlim(0, 14)
    ax2.set_title("45个国家级先进制造业集群产业领域结构分布\n（工信部高水平产业集群引领新质生产力空间跃升）",
                  fontsize=10.5, fontweight="bold", color=C_TEXT, pad=10)
    ax2.grid(True, axis="x", linestyle=":", alpha=0.6)

    for bar, c in zip(bars2, counts):
        ax2.text(c + 0.3, bar.get_y() + bar.get_height()/2,
                 f"{c} 个",
                 va="center", fontsize=8.4, fontweight="bold", color=C_TEXT)

    for s in ("top", "right"):
        ax2.spines[s].set_visible(False)

    fig.text(0.02, 0.98, "中国四大工业基地格局与国家级先进制造业集群分布",
             fontsize=13.5, fontweight="bold", color=C_TEXT)
    fig.text(0.02, 0.94,
             "四大传统工业基地奠定工业骨架，45个国家级先进制造业集群引领中国从制造大国向制造强国跨越",
             fontsize=9.2, color="#555555")
    fig.text(0.02, 0.015,
             "数据来源：工业和信息化部先进制造业集群建设名单、国家统计局《中国工业统计年鉴》",
             fontsize=8.0, color="#777777")

    fig.tight_layout(rect=(0, 0.04, 1, 0.92))
    path = os.path.join(FIGURES, "fig11-7_四大工业基地与先进制造业集群.png")
    save_volume_figure(fig, path, dpi=DPI)
    plt.close(fig)
    print("生成:", path)


def make_fig11_10():
    """图11-10：海上风电集群与特高压外送通道。"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.0, 5.8), gridspec_kw={"width_ratios": [1.05, 1.05]})

    # 子图1：沿海六大千万千瓦级海上风电基地规划并网规模 (GW)
    sea_bases = [
        "山东半岛海风基地\n(渤海与黄海深远海)",
        "江苏盐城/南通海风集群\n(黄海辐射沙洲海域)",
        "浙江舟山/温台海风走廊\n(东海海岛与近海风电)",
        "福建台湾海峡海风集群\n(狭管效应·高利用小时数)",
        "广东粤东/粤西海风基地\n(南海深水漂浮式大基地)",
        "广西北部湾海风基地\n(北部湾低纬度季风海域)"
    ]
    planned_cap = [35.0, 30.0, 25.0, 38.0, 45.0, 18.0]  # GW
    colors_sea = ["#3498db", "#2980b9", "#1f618d", "#16a085", "#27ae60", "#f39c12"]

    y_pos = np.arange(len(sea_bases))
    bars = ax1.barh(y_pos, planned_cap, color=colors_sea, height=0.55, edgecolor="#1a5276", lw=0.5, zorder=3)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(sea_bases, fontsize=8.8, fontweight="bold", color=C_TEXT)
    ax1.set_xlabel("中远期规划并网容量（GW，百万千瓦）", fontsize=9.2, color=C_TEXT)
    ax1.set_xlim(0, 55)
    ax1.set_title("中国沿海六大千万千瓦级海上风电基地布局\n（深远海“蓝色电厂”贴近东部沿海最高负荷中心）",
                  fontsize=10.5, fontweight="bold", color=C_TEXT, pad=10)
    ax1.grid(True, axis="x", linestyle=":", alpha=0.6)

    for bar, val in zip(bars, planned_cap):
        ax1.text(val + 1.0, bar.get_y() + bar.get_height()/2,
                 f"{val:.1f} GW",
                 va="center", fontsize=8.4, fontweight="bold", color=C_TEXT)

    for s in ("top", "right"):
        ax1.spines[s].set_visible(False)

    # 子图2：全国特高压“西电东送”三大通道年输送电量与清洁能源比重 (亿千瓦时)
    channels = [
        "北通道 (晋蒙新向京津冀鲁)\n[大秦/特高压火电+光伏外送]",
        "中通道 (川渝藏向华中长三角)\n[三峡/金沙江/雅砻江水电+光伏]",
        "南通道 (滇黔向粤港澳大湾区)\n[澜沧江/南盘江水电+风电]"
    ]
    total_twh = [3850, 4200, 2900]   # 亿千瓦时
    green_pct = [48, 88, 82]          # 清洁能源比重 (%)

    y_pos2 = np.arange(len(channels))
    bars2 = ax2.barh(y_pos2, total_twh, color="#2e4053", height=0.5, edgecolor="#17202a", lw=0.5, zorder=3)
    ax2.set_yticks(y_pos2)
    ax2.set_yticklabels(channels, fontsize=8.8, fontweight="bold", color=C_TEXT)
    ax2.set_xlabel("各走廊特高压/超高压年输电总量（亿千瓦时）", fontsize=9.2, color=C_TEXT)
    ax2.set_xlim(0, 5500)
    ax2.set_title("特高压“西电东送”三大通道输电规模与清洁度\n（累计输送能力超3亿千瓦，构建全国能源空间大循环）",
                  fontsize=10.5, fontweight="bold", color=C_TEXT, pad=10)
    ax2.grid(True, axis="x", linestyle=":", alpha=0.6)

    for bar, twh, pct in zip(bars2, total_twh, green_pct):
        ax2.text(twh + 120, bar.get_y() + bar.get_height()/2,
                 f"{twh:,} 亿kWh (绿电占{pct}%)",
                 va="center", fontsize=8.2, fontweight="bold", color="#117a65")

    for s in ("top", "right"):
        ax2.spines[s].set_visible(False)

    fig.text(0.02, 0.98, "中国海上风电基地集群与特高压外送通道空间格局",
             fontsize=13.5, fontweight="bold", color=C_TEXT)
    fig.text(0.02, 0.94,
             "深远海风能就近直供沿海负荷中心，特高压通道打通西部陆上清洁电力向中东部大动脉，构建绿色低碳能源大网",
             fontsize=9.2, color="#555555")
    fig.text(0.02, 0.015,
             "数据来源：国家能源局《“十四五”可再生能源发展规划》、国家电网与南方电网社会责任报告",
             fontsize=8.0, color="#777777")

    fig.tight_layout(rect=(0, 0.04, 1, 0.92))
    path = os.path.join(FIGURES, "fig11-10_海上风电集群与特高压外送通道.png")
    save_volume_figure(fig, path, dpi=DPI)
    plt.close(fig)
    print("生成:", path)


if __name__ == "__main__":
    standardize_existing_figs()
    make_fig11_7()
    make_fig11_10()
