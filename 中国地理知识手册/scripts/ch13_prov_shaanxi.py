# -*- coding: utf-8 -*-
"""13.5.10 陕西省 —— 省域地势图与分区统计图。

fig13-25 陕西省地势图（z9 DEM，300 m/px；10 地级市编号标注）
fig13-26 分市常住人口（七普）与人口密度双联图
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import setup
from ch13_prov_common import fig_relief, fig_pop

ADCODE = "610000"

POP7 = {  # 七普常住人口（万人，2020-11-01，陕西省第七次全国人口普查公报）
    "西安市": 1295.3, "铜川市": 69.8, "宝鸡市": 332.2, "咸阳市": 396.0,
    "渭南市": 468.9, "延安市": 228.3, "汉中市": 321.1, "榆林市": 362.5,
    "安康市": 249.4, "商洛市": 204.1,
}

GEO = [
    ("k", "太白山", 107.78, 34.03),
    ("k", "华山", 110.09, 34.48),
    ("k", "毛乌素沙地", 108.95, 38.05),
    ("k", "汉中盆地", 106.50, 33.05),
    ("r", "黄河", 110.45, 36.10),
    ("r", "汉江", 110.10, 32.81),
    ("l", "红碱淖", 109.80, 38.95, {"dot": "lake"}),
    ("m", "神府煤田", 110.40, 39.00, {"dot": "mine"}),
]


def run():
    areas = fig_relief(
        25, ADCODE, "fig13-25_陕西省地势图.png",
        "陕西省地势与10市",
        "黄土高原、关中平原与秦巴山地——秦岭南北，一省三貌",
        geo_tags=GEO,
        footer_lines=[
            "秦岭为中国南北地理分界线；界线：DataV.GeoAtlas（2021.5，仅供学习交流）；"
            "高程按 AWS Terrain z9（300 m）量算；示意地图，不作为权属划界依据；投影：Albers 等积圆锥",
        ],
        tag_top=0.285, cols=3, tag_fs=8.4, footer_y0=0.008)
    print("陕西分区面积（km²）：", areas)

    fig_pop(
        26, ADCODE, POP7, "fig13-26_陕西分区人口.png",
        "陕西省分市人口格局",
        "数据：陕西省第七次全国人口普查公报（2021）；界线：DataV.GeoAtlas areas_v3（2021.5，仅供学习交流）",
        unit_note="人口为第七次全国人口普查（2020-11-01）口径，省直辖杨凌示范区（25.3 万）未列入；"
                  "面积按 DataV 界线在 Albers 投影下量算")


if __name__ == "__main__":
    setup()
    run()
    print("shaanxi figures done")
