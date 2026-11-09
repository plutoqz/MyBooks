# -*- coding: utf-8 -*-
"""第 13 章 区域地理分论 —— 补充生成高水准专业学术图表。

新增图表总览：
fig13-7: 中国三大自然区与四大地理分区综合特征对比 (13.1)
fig13-8: 北方三大自然单元水土资源与产粮产煤格局 (13.2)
fig13-9: 南方五大自然人文单元水热与经济要素对比 (13.3)
fig13-10: 西北内陆盆地绿洲水系与沙戈荒新能源格局 (13.4)
fig13-11: 青藏高原水塔冰冻圈与一江两河河谷农业空间格局 (13.5)
"""
from volume1_layout import save_volume_figure
import os
import sys
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import FIGURES, DPI, setup, C_TEXT

setup()


def make_fig13_7():
    """图13-7：中国三大自然区与四大地理分区综合特征对比。"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.2, 5.6), gridspec_kw={"width_ratios": [1.05, 1.15]})

    # 子图1：三大自然区核心参数对比（国土面积比、常住人口比、GDP占比、多年平均降水量）
    regions3 = ["东部季风区\n(温带/亚热带/热带季风)", "西北干旱半干旱区\n(内陆温带大陆性干旱)", "青藏高寒区\n(高海拔第三极·垂直带)"]
    area_share3 = [45.0, 30.0, 25.0]
    pop_share3 = [94.5, 4.8, 0.7]
    gdp_share3 = [94.8, 4.7, 0.5]
    precip_mean = [1050, 220, 380]  # mm

    x = np.arange(len(regions3))
    width = 0.22

    rects1 = ax1.bar(x - width, area_share3, width, label="国土面积占比 (%)", color="#3498db", edgecolor="#2980b9", alpha=0.9)
    rects2 = ax1.bar(x, pop_share3, width, label="常住人口占比 (%)", color="#e74c3c", edgecolor="#c0392b", alpha=0.9)
    rects3 = ax1.bar(x + width, gdp_share3, width, label="GDP 占比 (%)", color="#f39c12", edgecolor="#d68910", alpha=0.9)

    ax1.set_title("三大自然区国土面积、人口与经济体量结构", fontsize=11.5, fontweight="bold", pad=12, color=C_TEXT)
    ax1.set_xticks(x)
    ax1.set_xticklabels(regions3, fontsize=9.5)
    ax1.set_ylabel("全国占比 (%)", fontsize=10, color=C_TEXT)
    ax1.set_ylim(0, 110)
    ax1.grid(axis="y", linestyle="--", alpha=0.4)
    ax1.legend(loc="upper right", fontsize=9, framealpha=0.9)

    for rects in [rects1, rects2, rects3]:
        for rect in rects:
            h = rect.get_height()
            ax1.annotate(f"{h:.1f}",
                         xy=(rect.get_x() + rect.get_width() / 2, h),
                         xytext=(0, 2), textcoords="offset points",
                         ha="center", va="bottom", fontsize=8.5, fontweight="bold")

    # 子图2：四大地理分区自然指标与经济指标综合对比
    r4_names = ["北方地区", "南方地区", "西北地区", "青藏地区"]
    precip_r4 = [620, 1380, 180, 420]      # 年平均降水 (mm)
    temp_r4 = [10.2, 17.8, 7.5, 2.8]       # 年均温 (℃)
    forest_cover = [22.4, 48.6, 6.8, 12.1] # 森林覆盖率 (%)
    per_gdp = [7.83, 10.28, 7.42, 6.55]    # 人均GDP (万元/人)

    x2 = np.arange(len(r4_names))
    width2 = 0.35

    ax2_twin = ax2.twinx()

    b1 = ax2.bar(x2 - width2/2, precip_r4, width2, label="区域年均降水量 (mm)", color="#27ae60", edgecolor="#1e8449", alpha=0.85)
    b2 = ax2_twin.bar(x2 + width2/2, forest_cover, width2, label="森林覆盖率 (%)", color="#8e44ad", edgecolor="#71368a", alpha=0.85)

    ax2.set_title("四大地理分区水热生态指标对比 (降水量与森林覆盖率)", fontsize=11.5, fontweight="bold", pad=12, color=C_TEXT)
    ax2.set_xticks(x2)
    ax2.set_xticklabels(r4_names, fontsize=10, fontweight="bold")
    ax2.set_ylabel("年平均降水量 (mm)", fontsize=10, color="#1e8449")
    ax2_twin.set_ylabel("森林覆盖率 (%)", fontsize=10, color="#71368a")
    ax2.set_ylim(0, 1600)
    ax2_twin.set_ylim(0, 60)
    ax2.grid(axis="y", linestyle=":", alpha=0.4)

    for rect in b1:
        h = rect.get_height()
        ax2.annotate(f"{int(h)}mm", xy=(rect.get_x() + rect.get_width() / 2, h),
                     xytext=(0, 2), textcoords="offset points", ha="center", va="bottom", fontsize=8.5, color="#1e8449")
    for rect in b2:
        h = rect.get_height()
        ax2_twin.annotate(f"{h:.1f}%", xy=(rect.get_x() + rect.get_width() / 2, h),
                          xytext=(0, 2), textcoords="offset points", ha="center", va="bottom", fontsize=8.5, color="#71368a")

    lines1, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2_twin.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=9, framealpha=0.9)

    fig.suptitle("图 13-7 中国三大自然区与四大地理分区综合特征对比", fontsize=13, fontweight="bold", y=0.98, color=C_TEXT)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    out_path = os.path.join(FIGURES, "fig13-7_中国三大自然区与四大地理分区综合特征对比.png")
    save_volume_figure(fig, out_path, dpi=DPI)
    plt.close(fig)
    print("Generated:", out_path)


def make_fig13_8():
    """图13-8：北方三大自然单元水土资源与产粮产煤格局。"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.2, 5.6), gridspec_kw={"width_ratios": [1.1, 1.1]})

    # 子图1：三大单元核心资源要素对比（东北平原、华北平原、黄土高原）
    units = ["东北平原\n(黑土·商品粮·装备)", "华北平原\n(黄土·麦玉两熟·高密人口)", "黄土高原\n(塬梁峁·能源库·生态治理)"]
    grain_share = [37.2, 45.8, 17.0]       # 北方粮食产量内部比重 (%)
    water_per_capita = [1050, 280, 410]   # 人均水资源量 (m³/人，全国平均约 2000)
    coal_share = [4.2, 11.5, 84.3]        # 北方煤炭产量内部比重 (%)

    y = np.arange(len(units))
    height = 0.26

    r1 = ax1.barh(y + height, grain_share, height, label="北方粮食产量贡献比重 (%)", color="#27ae60", edgecolor="#1e8449", alpha=0.9)
    r2 = ax1.barh(y, coal_share, height, label="北方原煤产量贡献比重 (%)", color="#34495e", edgecolor="#2c3e50", alpha=0.9)

    ax1.set_title("北方三大自然单元粮食与煤炭能源贡献结构", fontsize=11.5, fontweight="bold", pad=12, color=C_TEXT)
    ax1.set_yticks(y)
    ax1.set_yticklabels(units, fontsize=9.5)
    ax1.set_xlabel("在北方地区内部占比 (%)", fontsize=10, color=C_TEXT)
    ax1.set_xlim(0, 100)
    ax1.grid(axis="x", linestyle="--", alpha=0.4)
    ax1.legend(loc="upper right", fontsize=9, framealpha=0.9)

    for rect in r1:
        w = rect.get_width()
        ax1.annotate(f"{w:.1f}%", xy=(w, rect.get_y() + rect.get_height()/2),
                     xytext=(3, 0), textcoords="offset points", va="center", fontsize=8.5, fontweight="bold", color="#1e8449")
    for rect in r2:
        w = rect.get_width()
        ax1.annotate(f"{w:.1f}%", xy=(w, rect.get_y() + rect.get_height()/2),
                     xytext=(3, 0), textcoords="offset points", va="center", fontsize=8.5, fontweight="bold", color="#2c3e50")

    # 子图2：水土资源配比与人均水资源极度紧缺对比
    x = np.arange(len(units))
    b_water = ax2.bar(x, water_per_capita, 0.45, color=["#2980b9", "#e74c3c", "#f39c12"], edgecolor="#1b4f72", alpha=0.9)
    ax2.axhline(500, color="#c0392b", linestyle="--", linewidth=1.5, label="国际重度缺水警戒线 (500 m³/人)")
    ax2.axhline(1000, color="#d35400", linestyle=":", linewidth=1.5, label="国际中度缺水警戒线 (1000 m³/人)")

    ax2.set_title("北方三大地形区人均水资源量与缺水警戒 (m³/人)", fontsize=11.5, fontweight="bold", pad=12, color=C_TEXT)
    ax2.set_xticks(x)
    ax2.set_xticklabels(["东北平原", "华北平原", "黄土高原"], fontsize=10, fontweight="bold")
    ax2.set_ylabel("人均水资源量 (m³/人)", fontsize=10, color=C_TEXT)
    ax2.set_ylim(0, 1400)
    ax2.grid(axis="y", linestyle="--", alpha=0.4)
    ax2.legend(loc="upper right", fontsize=9, framealpha=0.9)

    for rect in b_water:
        h = rect.get_height()
        ax2.annotate(f"{int(h)} m³", xy=(rect.get_x() + rect.get_width() / 2, h),
                     xytext=(0, 2), textcoords="offset points", ha="center", va="bottom", fontsize=9, fontweight="bold")

    fig.suptitle("图 13-8 北方三大自然单元水土资源与产粮产煤格局", fontsize=13, fontweight="bold", y=0.98, color=C_TEXT)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    out_path = os.path.join(FIGURES, "fig13-8_北方三大自然单元水土资源与产粮产煤格局.png")
    save_volume_figure(fig, out_path, dpi=DPI)
    plt.close(fig)
    print("Generated:", out_path)


def make_fig13_9():
    """图13-9：南方五大自然人文单元水热与经济要素对比。"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.2, 5.6), gridspec_kw={"width_ratios": [1.1, 1.1]})

    subregions = [
        "长江中下游平原\n(长三角/水乡鱼米)",
        "东南丘陵\n(浙闽粤赣/红壤林茶)",
        "四川盆地\n(成渝/天府之国/紫色土)",
        "云贵高原\n(喀斯特/立体气候/民族)",
        "华南与岭南沿海\n(大湾区/热带季风/海洋)"
    ]
    precip = [1180, 1620, 1020, 1100, 1850]     # 年均降水 (mm)
    gdp_share_south = [38.5, 14.8, 12.5, 6.2, 28.0] # 占南方GDP比重 (%)
    forest_cover = [28.5, 64.2, 38.0, 56.5, 58.2] # 森林覆盖率 (%)

    y = np.arange(len(subregions))
    height = 0.35

    r1 = ax1.barh(y + height/2, gdp_share_south, height, label="在南方经济总量占比 (%)", color="#e67e22", edgecolor="#d35400", alpha=0.9)
    r2 = ax1.barh(y - height/2, forest_cover, height, label="森林覆盖率 (%)", color="#27ae60", edgecolor="#1e8449", alpha=0.9)

    ax1.set_title("南方五大地貌单元经济占比与生态绿被对比", fontsize=11.5, fontweight="bold", pad=12, color=C_TEXT)
    ax1.set_yticks(y)
    ax1.set_yticklabels(subregions, fontsize=9)
    ax1.set_xlabel("比重指标 (%)", fontsize=10, color=C_TEXT)
    ax1.set_xlim(0, 75)
    ax1.grid(axis="x", linestyle="--", alpha=0.4)
    ax1.legend(loc="lower right", fontsize=9, framealpha=0.9)

    for rect in r1:
        w = rect.get_width()
        ax1.annotate(f"{w:.1f}%", xy=(w, rect.get_y() + rect.get_height()/2),
                     xytext=(3, 0), textcoords="offset points", va="center", fontsize=8, fontweight="bold", color="#d35400")
    for rect in r2:
        w = rect.get_width()
        ax1.annotate(f"{w:.1f}%", xy=(w, rect.get_y() + rect.get_height()/2),
                     xytext=(3, 0), textcoords="offset points", va="center", fontsize=8, fontweight="bold", color="#1e8449")

    # 子图2：南方四大城市群核心规模对比（长三角、粤港澳大湾区、成渝、长江中游）
    clusters = ["长江三角洲\n城市群", "粤港澳\n大湾区", "成渝地区\n双城经济圈", "长江中游\n城市群"]
    cluster_gdp = [30.5, 14.0, 8.2, 11.5]     # GDP 万亿元
    cluster_pop = [2.38, 0.86, 1.02, 1.25]    # 人口 亿人

    x = np.arange(len(clusters))
    width = 0.35

    ax2_twin = ax2.twinx()

    bar1 = ax2.bar(x - width/2, cluster_gdp, width, label="2023年经济总量 (万亿元)", color="#2980b9", edgecolor="#1a5276", alpha=0.9)
    bar2 = ax2_twin.bar(x + width/2, cluster_pop, width, label="常住人口规模 (亿人)", color="#c0392b", edgecolor="#922b21", alpha=0.9)

    ax2.set_title("南方四大国家级城市群经济与人口体量对比", fontsize=11.5, fontweight="bold", pad=12, color=C_TEXT)
    ax2.set_xticks(x)
    ax2.set_xticklabels(clusters, fontsize=9.5, fontweight="bold")
    ax2.set_ylabel("生产总值 (万亿元)", fontsize=10, color="#1a5276")
    ax2_twin.set_ylabel("常住人口 (亿人)", fontsize=10, color="#922b21")
    ax2.set_ylim(0, 35)
    ax2_twin.set_ylim(0, 3.0)
    ax2.grid(axis="y", linestyle=":", alpha=0.4)

    for rect in bar1:
        h = rect.get_height()
        ax2.annotate(f"{h:.1f}", xy=(rect.get_x() + rect.get_width() / 2, h),
                     xytext=(0, -10), textcoords="offset points", ha="center",
                     va="top", fontsize=8.5, color="white")
    for rect in bar2:
        h = rect.get_height()
        ax2_twin.annotate(f"{h:.2f}", xy=(rect.get_x() + rect.get_width() / 2, h),
                          xytext=(0, -12), textcoords="offset points", ha="center", va="top", fontsize=8.5, color="white")

    l1, lb1 = ax2.get_legend_handles_labels()
    l2, lb2 = ax2_twin.get_legend_handles_labels()
    ax2.legend(l1 + l2, lb1 + lb2, loc="upper right", fontsize=9, framealpha=0.9)

    fig.suptitle("图 13-9 南方五大自然人文单元水热与经济要素对比", fontsize=13, fontweight="bold", y=0.98, color=C_TEXT)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    out_path = os.path.join(FIGURES, "fig13-9_南方五大自然人文单元水热与经济要素对比.png")
    save_volume_figure(fig, out_path, dpi=DPI)
    plt.close(fig)
    print("Generated:", out_path)


def make_fig13_10():
    """图13-10：西北内陆盆地绿洲水系与沙戈荒新能源格局。"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.2, 5.6), gridspec_kw={"width_ratios": [1.05, 1.15]})

    # 子图1：西北主要内流与灌溉水系水文与灌溉绿洲特征
    rivers = ["塔里木河干流\n(内流河之首·天山昆仑雪水)", "黑河水系\n(祁连山·额济纳旗胡杨林)", "河套引黄灌区\n(塞上江南·天下黄河富宁蒙)", "石羊河与疏勒河\n(民勤防沙·敦煌莫高绿洲)"]
    flow_len = [2179, 821, 800, 540]          # 流程或干渠长 (km)
    annual_runoff = [398, 24.5, 120, 28.0]     # 年径流或引水量 (亿 m³)
    oasis_area = [4.2, 0.9, 1.1, 0.6]          # 灌溉滋养绿洲耕地 (千万亩)

    y = np.arange(len(rivers))
    height = 0.55
    r1 = ax1.barh(y, annual_runoff, height, color="#2980b9",
                 edgecolor="#1a5276", alpha=0.9)

    ax1.set_title("西北骨干水系水量与滋养绿洲规模对比", fontsize=11.5, fontweight="bold", pad=12, color=C_TEXT)
    ax1.set_yticks(y)
    ax1.set_yticklabels(rivers, fontsize=9)
    ax1.set_xlabel("年径流或引水量（亿 m³）", fontsize=10, color=C_TEXT)
    ax1.set_xlim(0, 450)
    ax1.grid(axis="x", linestyle="--", alpha=0.4)
    for rect, area_value in zip(r1, oasis_area):
        w = rect.get_width()
        ax1.annotate(f"{w:.1f} 亿m³\n绿洲 {area_value:.1f} 千万亩",
                     xy=(w, rect.get_y() + rect.get_height()/2),
                     xytext=(5, 0), textcoords="offset points", va="center",
                     fontsize=8.5, color="#1a5276")

    # 子图2：西北“沙戈荒”国家级大型风光基地与新能源装机
    bases = [
        "库布其沙漠\n风光基地 (蒙西)",
        "腾格里沙漠\n风光基地 (宁甘)",
        "乌兰布和沙漠\n风电光伏 (内蒙古)",
        "准噶尔盆地\n风光储基地 (新疆)",
        "塔里木盆地\n环沙漠新能源 (南疆)"
    ]
    plan_cap = [12.0, 13.0, 8.5, 15.0, 10.5]  # 规划总装机容量 (GW)
    x = np.arange(len(bases))
    b1 = ax2.bar(x, plan_cap, 0.55, color="#C07815",
                edgecolor="#956014", alpha=0.9)

    ax2.set_title("西北重点沙漠风光基地规划装机", fontsize=11.5, fontweight="bold", pad=12, color=C_TEXT)
    ax2.set_xticks(x)
    ax2.set_xticklabels(bases, fontsize=8.5, fontweight="bold")
    ax2.set_ylabel("装机容量 (GW)", fontsize=10, color="#d68910")
    ax2.set_ylim(0, 18)
    ax2.grid(axis="y", linestyle=":", alpha=0.4)

    for rect in b1:
        h = rect.get_height()
        ax2.annotate(f"{h:.1f}GW", xy=(rect.get_x() + rect.get_width() / 2, h),
                     xytext=(0, 2), textcoords="offset points", ha="center", va="bottom", fontsize=8, color="#d68910")

    fig.suptitle("图 13-10 西北内陆盆地绿洲水系与沙戈荒新能源格局", fontsize=13, fontweight="bold", y=0.98, color=C_TEXT)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    out_path = os.path.join(FIGURES, "fig13-10_西北内陆盆地绿洲水系与沙戈荒新能源格局.png")
    save_volume_figure(fig, out_path, dpi=DPI)
    plt.close(fig)
    print("Generated:", out_path)


def make_fig13_11():
    """图13-11：青藏高原水塔冰冻圈与一江两河河谷农业空间格局。"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.2, 5.6), gridspec_kw={"width_ratios": [1.1, 1.1]})

    # 子图1：“亚洲水塔”流出青藏高原主要国际与国内大河出流年水资源量与发源海拔
    rivers = [
        "长江源 (沱沱河/通天河)",
        "黄河源 (扎陵湖/鄂陵湖)",
        "澜沧江 (湄公河源)",
        "雅鲁藏布江 (布拉马普特拉河)",
        "怒江 (萨尔温江源)",
        "印度河上源 (狮泉河/象泉河)"
    ]
    outflow_runoff = [156, 215, 128, 1654, 252, 65]  # 流出高原区域年径流量 (亿 m³)
    source_elevation = [5800, 4800, 5200, 5590, 5450, 5300] # 源头高程 (m)

    y = np.arange(len(rivers))
    height = 0.55

    r1 = ax1.barh(y, outflow_runoff, height, color="#2980b9", edgecolor="#1b4f72", alpha=0.88)

    ax1.set_title("“亚洲水塔”主要江河源区流出高原径流量 (亿 m³)", fontsize=11.5, fontweight="bold", pad=12, color=C_TEXT)
    ax1.set_yticks(y)
    ax1.set_yticklabels(rivers, fontsize=9.5)
    ax1.set_xlabel("流出高原区多年平均年径流量 (亿 m³)", fontsize=10, color=C_TEXT)
    ax1.set_xlim(0, 1900)
    ax1.grid(axis="x", linestyle="--", alpha=0.4)

    for rect in r1:
        w = rect.get_width()
        ax1.annotate(f"{w} 亿m³", xy=(w, rect.get_y() + rect.get_height()/2),
                     xytext=(4, 0), textcoords="offset points", va="center", fontsize=8.5, fontweight="bold", color="#1b4f72")

    # 子图2：河谷农业集中区与高原生态安全屏障指标对比
    valleys = [
        "雅鲁藏布江中游\n“一江两河”谷地",
        "青海湟水谷地\n(西宁/海东农业核心)",
        "三江源国家公园\n(黄河/长江/澜沧江源)",
        "羌塘高原\n高寒荒漠与自然保护区"
    ]
    elevation_val = [3600, 2250, 4500, 4800] # 代表海拔 (m)

    x = np.arange(len(valleys))
    bar1 = ax2.bar(x, elevation_val, 0.55, color="#8052A0",
                  edgecolor="#6c3483", alpha=0.9)

    ax2.set_title("河谷农业区与高原生态区的代表海拔", fontsize=11.5, fontweight="bold", pad=12, color=C_TEXT)
    ax2.set_xticks(x)
    ax2.set_xticklabels(valleys, fontsize=9, fontweight="bold")
    ax2.set_ylabel("代表海拔（m）", fontsize=10, color="#6c3483")
    ax2.set_ylim(0, 5500)
    ax2.grid(axis="y", linestyle=":", alpha=0.4)

    for rect in bar1:
        h = rect.get_height()
        ax2.annotate(f"{int(h)}m", xy=(rect.get_x() + rect.get_width() / 2, h),
                     xytext=(0, 2), textcoords="offset points", ha="center", va="bottom", fontsize=8.5, color="#6c3483")

    fig.suptitle("图 13-11 青藏高原水塔冰冻圈与一江两河河谷农业空间格局", fontsize=13, fontweight="bold", y=0.98, color=C_TEXT)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    out_path = os.path.join(FIGURES, "fig13-11_青藏高原水塔冰冻圈与一江两河河谷农业空间格局.png")
    save_volume_figure(fig, out_path, dpi=DPI)
    plt.close(fig)
    print("Generated:", out_path)


if __name__ == "__main__":
    os.makedirs(FIGURES, exist_ok=True)
    print("=== Generating supplementary figures for Chapter 13 ===")
    make_fig13_7()
    make_fig13_8()
    make_fig13_9()
    make_fig13_10()
    make_fig13_11()
    print("=== All Chapter 13 figures generated successfully! ===")
