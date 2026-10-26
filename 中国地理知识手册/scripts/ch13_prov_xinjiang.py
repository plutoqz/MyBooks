# -*- coding: utf-8 -*-
"""13.5.32 新疆维吾尔自治区 —— 省域地势图与分区统计图。

fig13-210 新疆维吾尔自治区地势图（z9 DEM，300 m/px；14 地州市编号，
          兵团直辖县级市不单独标注）
fig13-211 分地州市常住人口（七普）与人口密度双联图
fig13-212 分区域地区生产总值（2025，北疆/南疆/东疆）条形图
"""
import os
import sys

import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import setup, C_TEXT, FIGURES, DPI
from ch13_prov_common import fig_relief, fig_pop

ADCODE = "650000"

POP7 = {  # 七普常住人口（万人，2020-11-01，新疆第七次全国人口普查公报；伊犁为州直口径）
    "乌鲁木齐市": 405.4, "克拉玛依市": 49.0, "吐鲁番市": 69.4, "哈密市": 67.3,
    "昌吉回族自治州": 161.4, "博尔塔拉蒙古自治州": 48.8,
    "巴音郭楞蒙古自治州": 161.4, "阿克苏地区": 271.4,
    "克孜勒苏柯尔克孜自治州": 62.2, "喀什地区": 449.6, "和田地区": 250.5,
    "伊犁哈萨克自治州": 284.8, "塔城地区": 113.9, "阿勒泰地区": 66.9,
}

REGION_GDP25 = [  # 2025 年分区域地区生产总值（亿元，自治区公报口径）
    ("北疆", 13192.11, 5.2), ("南疆", 6438.98, 5.9), ("东疆", 1831.05, 7.1),
]

GEO = [
    ("k", "阿尔泰山", 88.0, 47.8),
    ("k", "天山", 85.0, 43.3),
    ("k", "昆仑山", 81.5, 36.4),
    ("k", "准噶尔盆地", 86.0, 45.5),
    ("k", "塔里木盆地", 83.0, 40.5),
    ("k", "吐鲁番盆地", 88.6, 42.35),
    ("r", "塔里木河", 84.5, 41.2),
    ("r", "伊犁河", 81.5, 43.7),
    ("r", "额尔齐斯河", 88.0, 47.5),
    ("l", "博斯腾湖", 86.8, 41.95, {"dot": "lake"}),
    ("l", "赛里木湖", 81.2, 44.6, {"dot": "lake"}),
    ("l", "天山天池", 88.1, 43.88, {"dot": "lake"}),
    ("m", "准东煤田", 89.3, 44.6, {"dot": "mine"}),
    ("m", "塔里木油气田", 83.5, 41.3, {"dot": "mine"}),
    ("m", "罗布泊钾盐", 90.8, 40.3, {"dot": "mine"}),
    ("p", "霍尔果斯口岸", 80.4, 44.2, {"dot": "port"}),
    ("p", "阿拉山口口岸", 82.6, 45.15, {"dot": "port"}),
]

BINGTUAN_CITIES = ["石河子市", "阿拉尔市", "图木舒克市", "五家渠市", "北屯市",
                   "铁门关市", "双河市", "可克达拉市", "昆玉市", "胡杨河市"]

RENAME = {  # 图下编号列表用简称（仅影响图例显示，不改坐标查找）
    "昌吉回族自治州": "昌吉州", "博尔塔拉蒙古自治州": "博尔塔拉州",
    "巴音郭楞蒙古自治州": "巴音郭楞州", "克孜勒苏柯尔克孜自治州": "克孜勒苏州",
    "伊犁哈萨克自治州": "伊犁州",
}


def fig_region_gdp(fname, title, subtitle, footer):
    """分区域地区生产总值条形图（2025）。"""
    labels = [r[0] for r in REGION_GDP25]
    vals = [r[1] for r in REGION_GDP25]
    growth = [r[2] for r in REGION_GDP25]
    fig, ax = plt.subplots(figsize=(9.8, 4.6))
    bars = ax.barh(labels[::-1], vals[::-1], color="#8fa8b8",
                   edgecolor="white", lw=0.4, height=0.55, zorder=3)
    for b, v, g in zip(bars, vals[::-1], growth[::-1]):
        ax.text(b.get_width() + max(vals) * 0.012,
                b.get_y() + b.get_height() / 2, f"{v:,.0f}（+{g}%）",
                va="center", ha="left", fontsize=10, color=C_TEXT, zorder=4)
    ax.set_xlim(0, max(vals) * 1.22)
    ax.grid(axis="x", color="#dde3e8", lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#999999")
    ax.tick_params(axis="y", length=0, labelsize=11)
    ax.tick_params(axis="x", labelsize=8.5, colors="#666666")
    ax.set_xlabel("地区生产总值（亿元）", fontsize=9, color="#666666")
    fig.text(0.02, 0.94, title, fontsize=14.5, fontweight="bold", color=C_TEXT)
    fig.text(0.02, 0.87, subtitle, fontsize=9.0, color="#666666")
    fig.text(0.02, 0.02, footer, fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.06, 1, 0.85))
    fig.savefig(os.path.join(FIGURES, fname), dpi=DPI)
    plt.close(fig)
    print(f"region gdp sum = {sum(vals):,.2f}")


def run():
    areas = fig_relief(
        "210", ADCODE, "fig13-210_新疆地势图.png",
        "新疆维吾尔自治区地势与14地州市",
        "“三山夹两盆”——阿尔泰山、天山、昆仑山之间，准噶尔与塔里木两大盆地相望",
        geo_tags=GEO,
        footer_lines=[
            "乔戈里峰（8 611 m）为中国第二高峰，艾丁湖（−154 m）为中国陆地最低点；"
            "兵团直辖县级市（石河子等）界线照绘、未单独编号",
            "界线：DataV.GeoAtlas（2021.5，仅供学习交流）；高程按 AWS Terrain z9（300 m）量算；"
            "示意地图，不作为权属划界依据；投影：Albers 等积圆锥",
        ],
        tag_top=0.335, cols=4, chunk=3, tag_fs=8.4, footer_y0=0.006,
        map_bottom=0.345, skip_names=BINGTUAN_CITIES, rename_map=RENAME)
    big = sorted(areas.items(), key=lambda kv: kv[1])
    print("地州面积最大/最小：", big[-1], big[0])

    fig_pop(
        "211", ADCODE, POP7, "fig13-211_新疆分区人口.png",
        "新疆维吾尔自治区分地州市人口格局",
        "数据：新疆维吾尔自治区第七次全国人口普查公报（2021），伊犁为州直口径；"
        "不含兵团直辖县级市（七普合计 123.1 万人）",
        panel_titles=("分地州市常住人口（2020 年七普）", "分地州市人口密度（七普口径）"),
        unit_note="人口为第七次全国人口普查（2020-11-01）口径，伊犁为州直口径；面积按 DataV 界线在 Albers 投影下量算")

    fig_region_gdp(
        "fig13-212_新疆分区GDP.png",
        "新疆分区域地区生产总值（2025 年）",
        "北疆占约 61%——天山北坡经济带是全疆经济重心，东疆增速最快",
        "数据：《新疆维吾尔自治区 2025 年国民经济和社会发展统计公报》分区域核算")


if __name__ == "__main__":
    setup()
    run()
    print("xinjiang figures done")
