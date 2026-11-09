# -*- coding: utf-8 -*-
"""生成补充小节插图：
fig9-6_汉语方言分区与空间分布.png
fig10-6_传统民居与风味地理.png
fig11-8_风光大基地与东数西算格局.png
fig12-5_历史地理通道与京杭大运河.png
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


# ---------------------------------------------------------------- fig 9-6
from volume1_topics import dialects as generate_fig9_6


# ---------------------------------------------------------------- fig 10-6
from volume1_topics import dwellings as generate_fig10_6


# ---------------------------------------------------------------- fig 11-8
from volume1_topics import energy_computing as generate_fig11_8


# ---------------------------------------------------------------- fig 12-5
from volume1_topics import historic_corridors as generate_fig12_5


if __name__ == "__main__":
    generate_fig9_6()
    generate_fig10_6()
    generate_fig11_8()
    generate_fig12_5()
