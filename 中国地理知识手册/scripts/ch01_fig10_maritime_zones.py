# -*- coding: utf-8 -*-
"""生成第 1 章新扩充图表：fig1-10 海洋权益空间划分示意图。"""
from volume1_layout import save_volume_figure
import os
import sys
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon, Rectangle

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import C_TEXT, DPI, FIGURES, setup

setup()
OUT = FIGURES
os.makedirs(OUT, exist_ok=True)

from volume1_topics import maritime_spaces as generate_fig1_10

if __name__ == "__main__":
    generate_fig1_10()
