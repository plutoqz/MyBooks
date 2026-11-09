# -*- coding: utf-8 -*-
"""第 10 章 城市与城镇化 —— 补充高水准专业学术图表。

包含：
fig10-3: 城镇化进程与收缩型城市空间分异
fig10-6: 国家中心城市与都市圈通勤同城化
fig10-8: 古代城市营建形制演进与中轴线
fig10-10: 八大菜系地理成因与茶酒文化分布
"""
from volume1_layout import save_volume_figure
import os
import sys
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import FIGURES, DPI, setup, C_TEXT

setup()


def make_fig10_3():
    """图10-3：城镇化进程与收缩型城市空间分异。"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.0, 5.8), gridspec_kw={"width_ratios": [1.05, 1.05]})

    # 子图1：中国城镇化率历史轨迹（1949—2024）与四大板块分异
    years = [1949, 1958, 1965, 1978, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2024]
    urban_rates = [10.6, 16.2, 18.0, 17.9, 23.7, 26.4, 29.0, 36.2, 43.0, 49.9, 56.1, 63.9, 66.2]

    ax1.plot(years, urban_rates, marker="o", color="#c0392b", lw=2.4, ms=5, label="全国常住人口城镇化率 (%)", zorder=4)
    ax1.axhline(50.0, color="#7f8c8d", linestyle="--", lw=1.0, label="50% 临界线 (2011年突破)")
    ax1.axhline(70.0, color="#27ae60", linestyle=":", lw=1.0, label="70% 成熟期门槛")

    # 背景阶段底色
    ax1.axvspan(1949, 1978, color="#f9ebea", alpha=0.5, label="起步曲折期 (10.6%→17.9%)")
    ax1.axvspan(1978, 2011, color="#fef9e7", alpha=0.5, label="高速推进期 (17.9%→51.3%)")
    ax1.axvspan(2011, 2024, color="#eaf2f8", alpha=0.5, label="存量深化期 (51.3%→66.2%)")

    # 标注四大板块2024年水平
    ax1.text(1982, 72, "东部板块: 约74.5%\n东北板块: 约68.2%\n中部板块: 约62.1%\n西部板块: 约59.8%",
             fontsize=8.5, bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor="#bdc3c7", alpha=0.9))

    ax1.set_xlabel("年份", fontsize=9.2, color=C_TEXT)
    ax1.set_ylabel("城镇化率 (%)", fontsize=9.2, color=C_TEXT)
    ax1.set_ylim(5, 80)
    ax1.set_xlim(1947, 2026)
    ax1.set_title("中国城镇化率历史轨迹与诺瑟姆S型曲线演化阶段\n（1949—2024年从10.6%飞跃至66.2%的世界级快速城镇化）",
                  fontsize=10.5, fontweight="bold", color=C_TEXT, pad=10)
    ax1.grid(True, linestyle=":", alpha=0.6)
    ax1.legend(loc="upper center", bbox_to_anchor=(0.5, -0.23),
               ncol=2, fontsize=8.0, frameon=False)

    for s in ("top", "right"):
        ax1.spines[s].set_visible(False)

    # 子图2：典型收缩型城市 vs 强劲扩张型城市七普人口增减幅度对比 (%)
    city_sample = [
        "大兴安岭林区 (资源型)", "伊春市 (林业转型)", "鹤岗市 (煤炭枯竭)",
        "双鸭山市 (重化收缩)", "石嘴山市 (老工矿区)", "辽阳市 (老工业区)",
        "合肥市 (产业集聚)", "郑州市 (枢纽扩容)", "成都市 (西南极核)",
        "西安市 (西北中心)", "杭州市 (数字经济)", "深圳市 (创新之都)"
    ]
    pct_changes = [-30.8, -20.1, -15.8, -14.9, -5.6, -4.8, 24.7, 46.0, 38.5, 52.9, 37.2, 68.5]
    colors_pct = ["#c0392b" if v < 0 else "#27ae60" for v in pct_changes]

    y_pos2 = np.arange(len(city_sample))
    bars2 = ax2.barh(y_pos2, pct_changes, color=colors_pct, height=0.6, edgecolor="#2c3e50", lw=0.5, zorder=3)
    ax2.axvline(0, color="#2c3e50", lw=1.0)
    ax2.set_yticks(y_pos2)
    ax2.set_yticklabels(city_sample, fontsize=8.8, fontweight="bold", color=C_TEXT)
    ax2.set_xlabel("2010—2020年十年常住人口增减幅度 (%)", fontsize=9.2, color=C_TEXT)
    ax2.set_xlim(-40, 80)
    ax2.set_title("收缩型城市与扩张型城市人口增减两极分化\n（资源型老工业城市存量收缩 vs 核心城市群强劲吸纳）",
                  fontsize=10.5, fontweight="bold", color=C_TEXT, pad=10)
    ax2.grid(True, axis="x", linestyle=":", alpha=0.6)

    for bar, val in zip(bars2, pct_changes):
        if val > 0:
            ax2.text(val + 1.5, bar.get_y() + bar.get_height()/2, f"+{val:.1f}%",
                     va="center", fontsize=8.0, fontweight="bold", color="#1e8449")
        else:
            ax2.text(val - 1.5, bar.get_y() + bar.get_height()/2, f"{val:.1f}%",
                     ha="right", va="center", fontsize=8.0, fontweight="bold", color="#922b21")

    for s in ("top", "right"):
        ax2.spines[s].set_visible(False)

    fig.text(0.02, 0.98, "中国城镇化进程演化与收缩型城市空间分异特征",
             fontsize=13.5, fontweight="bold", color=C_TEXT)
    fig.text(0.02, 0.94,
             "从增量粗放扩张转向存量品质深化：沿海与强省会持续向心集聚，北方部分老工业和资源枯竭型城市面临减量提质",
             fontsize=9.2, color="#555555")
    fig.text(0.02, 0.015,
             "数据来源：国家统计局历年统计年鉴、第六与第七次全国人口普查分县市数据与自然资源部收缩型城市专项研究",
             fontsize=8.0, color="#777777")

    fig.tight_layout(rect=(0, 0.04, 1, 0.92))
    path = os.path.join(FIGURES, "fig10-3_城镇化进程与收缩型城市空间分异.png")
    save_volume_figure(fig, path, dpi=DPI)
    plt.close(fig)
    print("生成:", path)


def make_fig10_6():
    """图10-6：国家中心城市与都市圈通勤同城化。"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.0, 5.8), gridspec_kw={"width_ratios": [1.05, 1.05]})

    # 子图1：9 大国家中心城市经济总量与城区常住人口规模（2023-2024最新口径）
    cities = ["北京", "上海", "广州", "重庆", "成都", "武汉", "天津", "郑州", "西安"]
    gdps = [4.38, 4.72, 3.04, 3.01, 2.21, 2.00, 1.67, 1.36, 1.20]  # 万亿元
    urban_pops = [1775, 1987, 1488, 1634, 1334, 1094, 1093, 760, 928]  # 城区常住人口（万人，七普/年鉴）

    y_pos = np.arange(len(cities))
    colors_gdp = ["#2980b9", "#1f618d", "#2471a3", "#2e86c1", "#3498db", "#5dade2", "#85c1e9", "#aed6f1", "#d4e6f1"]

    bars = ax1.barh(y_pos, gdps, color=colors_gdp[::-1], height=0.6, edgecolor="#1a5276", lw=0.5, zorder=3)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(cities, fontsize=9.5, fontweight="bold", color=C_TEXT)
    ax1.set_xlabel("地区生产总值（万亿元）", fontsize=9.2, color=C_TEXT)
    ax1.set_xlim(0, 5.5)
    ax1.set_title("9大国家中心城市经济总量与城区常住人口矩阵\n（国家顶层战略布局的综合性经济与交通枢纽极核）",
                  fontsize=10.5, fontweight="bold", color=C_TEXT, pad=10)
    ax1.grid(True, axis="x", linestyle=":", alpha=0.6)

    for bar, gdp, pop in zip(bars, gdps, urban_pops):
        ax1.text(gdp + 0.1, bar.get_y() + bar.get_height()/2,
                 f"{gdp:.2f}万亿 | 城区{pop:,}万人",
                 va="center", fontsize=8.2, fontweight="bold", color="#1a5276")

    for s in ("top", "right"):
        ax1.spines[s].set_visible(False)

    # 子图2：代表性都市圈 1 小时通勤走廊跨城日均客流量（万人次/日）与主要通道
    corridors = [
        "广佛都市圈 (广州—佛山)",
        "深莞惠都市圈 (深圳—东莞)",
        "京津冀核心 (北京—廊坊/燕郊)",
        "上海大都市圈 (上海—苏州/昆山)",
        "长株潭都市圈 (长沙—株洲/湘潭)",
        "成德眉资都市圈 (成都—德阳/资阳)",
        "南京都市圈 (南京—句容/马鞍山)"
    ]
    flow_vals = [36.5, 29.8, 24.2, 19.5, 14.8, 11.2, 9.6]  # 万人次/日
    transit_modes = [
        "广佛地铁互联互通·高频城际",
        "深圳地铁延入·深莞跨城快线",
        "京沈客专·进京跨省公交矩阵",
        "轨交11号线跨省直达·高铁通勤",
        "长株潭城际铁路·融城干道",
        "成资S3线·市域铁路联网",
        "宁句城际·宁马城际轨道网"
    ]
    colors_flow = ["#c0392b", "#d35400", "#e67e22", "#27ae60", "#16a085", "#2980b9", "#8e44ad"]

    y_pos2 = np.arange(len(corridors))
    bars2 = ax2.barh(y_pos2, flow_vals, color=colors_flow, height=0.6, edgecolor="#2c3e50", lw=0.5, zorder=3)
    ax2.set_yticks(y_pos2)
    ax2.set_yticklabels(corridors, fontsize=9.0, fontweight="bold", color=C_TEXT)
    ax2.set_xlabel("跨城通勤日均出行量（万人次/日）", fontsize=9.2, color=C_TEXT)
    ax2.set_xlim(0, 45)
    ax2.set_title("全国主要都市圈1小时通勤圈跨城日均客流与同城化模式\n（轨道交通网络重构跨行政边界的职住与经济日常空间）",
                  fontsize=10.5, fontweight="bold", color=C_TEXT, pad=10)
    ax2.grid(True, axis="x", linestyle=":", alpha=0.6)

    for bar, val, mode in zip(bars2, flow_vals, transit_modes):
        ax2.text(val + 0.8, bar.get_y() + bar.get_height()/2,
                 f"{val:.1f}万 ({mode})",
                 va="center", fontsize=7.8, fontweight="bold", color=C_TEXT)

    for s in ("top", "right"):
        ax2.spines[s].set_visible(False)

    fig.text(0.02, 0.98, "中国国家中心城市与都市圈通勤同城化格局",
             fontsize=13.5, fontweight="bold", color=C_TEXT)
    fig.text(0.02, 0.94,
             "9大国家中心城市引领全国区域战略极核，都市圈跨行政区轨道通勤构建1小时同城化生活与产业链协作圈",
             fontsize=9.2, color="#555555")
    fig.text(0.02, 0.015,
             "数据来源：住房和城乡建设部《城市建设统计年鉴》、各都市圈发展规划公报与全国重点城市跨城通勤大数据监测报告",
             fontsize=8.0, color="#777777")

    fig.tight_layout(rect=(0, 0.04, 1, 0.92))
    path = os.path.join(FIGURES, "fig10-6_国家中心城市与都市圈通勤同城化.png")
    save_volume_figure(fig, path, dpi=DPI)
    plt.close(fig)
    print("生成:", path)


from volume1_topics import city_forms as make_fig10_8


from volume1_topics import cuisine as make_fig10_10


if __name__ == "__main__":
    make_fig10_3()
    make_fig10_6()
    make_fig10_8()
    make_fig10_10()
