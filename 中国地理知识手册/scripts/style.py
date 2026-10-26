# -*- coding: utf-8 -*-
"""《中国地理知识手册》共享绘图样式与工具。

所有章节绘图脚本均 import 本模块，保证全书图表风格统一：
学术地图风格、Albers 等积圆锥投影（全国图）、统一字体与注记。
"""
import os
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrow

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
FIGURES = os.path.join(ROOT, "figures")

# 中国全国图标准投影：Albers 等积圆锥（中央经线 105°E，标准纬线 25°N/47°N）
ALBERS = ("+proj=aea +lat_1=25 +lat_2=47 +lat_0=0 +lon_0=105 "
          "+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs")

# 全书统一配色
C_CHINA = "#c0392b"      # 中国主色（红）
C_CHINA_FILL = "#f5c6aa" # 中国填充（浅橙红）
C_LAND = "#f2efe9"       # 一般陆地
C_SEA = "#d4e6f1"        # 海洋
C_NEIGHBOR = "#fdf3d7"   # 陆上邻国
C_MARITIME = "#d6eaf8"   # 隔海相望国家
C_EDGE = "#7f7f7f"       # 行政界线
C_TEXT = "#2c3e50"

DPI = 200


def setup():
    matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    matplotlib.rcParams["axes.unicode_minus"] = False
    matplotlib.rcParams["font.size"] = 10.5
    matplotlib.rcParams["figure.facecolor"] = "white"
    matplotlib.rcParams["savefig.facecolor"] = "white"


def load_china():
    """载入全国界线（含南海诸岛与九段线），GeoDataFrame。"""
    import geopandas as gpd
    return gpd.read_file(os.path.join(DATA, "boundaries", "datav", "100000.json"))


def load_world(resolution="50m"):
    """载入 Natural World 各国界线。resolution: '110m' 或 '50m'。"""
    import geopandas as gpd
    path = os.path.join(DATA, "boundaries", "natural_earth", f"ne_{resolution}",
                        f"ne_{resolution}_admin_0_countries.shp")
    return gpd.read_file(path)


def set_extent_from(ax, gdf, pad_frac=0.04):
    """按要素范围设置图幅（含留白）。"""
    minx, miny, maxx, maxy = gdf.total_bounds
    dx, dy = (maxx - minx), (maxy - miny)
    ax.set_xlim(minx - dx * pad_frac, maxx + dx * pad_frac)
    ax.set_ylim(miny - dy * pad_frac, maxy + dy * pad_frac)
    return ax


def save_fig(fig, ax, filename, footer=None):
    """清除 geopandas 自动加的坐标轴标签后统一保存。

    footer：写在图幅下方（地图主体之外）的说明/来源文字，
    避免在图内放置说明造成遮挡。
    ax 可传单个 Axes 或其列表/元组（多子图时全部清除）。
    """
    for a in (ax if isinstance(ax, (list, tuple)) else [ax]):
        a.set_xlabel("")
        a.set_ylabel("")
    if footer:
        fig.text(0.5, 0.012, footer, ha="center", va="bottom",
                 fontsize=8.2, color="#555555")
        fig.tight_layout(rect=(0, 0.05, 1, 1))
    else:
        fig.tight_layout()
    fig.savefig(os.path.join(FIGURES, filename), dpi=DPI)
    plt.close(fig)


def add_north_arrow(ax, x=0.955, y=0.90, size=0.055):
    """在轴坐标系指定比例位置加指北针。"""
    trans = ax.transAxes
    ax.add_patch(FancyArrow(x, y - size * 0.55, 0, size,
                            width=0.002, head_width=size * 0.42,
                            head_length=size * 0.42, fc="#2c3e50", ec="#2c3e50",
                            transform=trans, zorder=20))
    ax.text(x, y + size * 0.62, "N", transform=trans, ha="center", va="bottom",
            fontsize=11, fontweight="bold", color="#2c3e50", zorder=20)


def add_note(ax, text, x=0.005, y=0.008, fontsize=7.5):
    """左下角来源/说明注记。"""
    ax.text(x, y, text, transform=ax.transAxes, ha="left", va="bottom",
            fontsize=fontsize, color="#555555", zorder=20,
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.75))


def add_title(ax, title, subtitle=None):
    """地图标题与副标题（置于图内上方，学术风格）。"""
    ax.text(0.5, 0.985, title, transform=ax.transAxes, ha="center", va="top",
            fontsize=15, fontweight="bold", color=C_TEXT, zorder=20)
    if subtitle:
        ax.text(0.5, 0.952, subtitle, transform=ax.transAxes, ha="center", va="top",
                fontsize=10, color="#555555", zorder=20)


def new_map_axes(figsize):
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_aspect("equal")
    # 不能用 set_axis_off()：matplotlib 在 axison=False 时不绘制
    # 轴背景 patch（海面底色会丢失），改为手动隐藏刻度与边框。
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    return fig, ax
