# -*- coding: utf-8 -*-
"""《中国地理知识手册》共享绘图样式与工具。

所有章节绘图脚本均 import 本模块，保证全书图表风格统一：
学术地图风格、Albers 等积圆锥投影（全国图）、统一字体与注记。
"""
import os
try:
    import pyproj
    _proj_dir = pyproj.datadir.get_data_dir()
    os.environ['PROJ_LIB'] = _proj_dir
    os.environ['PROJ_DATA'] = _proj_dir
except Exception:
    pass
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
    """载入全国界线（含南海诸岛与九段线），GeoDataFrame。

    兼容两种数据文件名：优先 100000_full.json（现行 DataV 下载命名），
    回退 100000.json。旧实现只读后者，导致 ch01 系列在现有数据下无法重跑。
    """
    import geopandas as gpd
    for fn in ("100000_full.json", "100000.json", "100000.json.json"):
        p = os.path.join(DATA, "boundaries", "datav", fn)
        if os.path.exists(p):
            return gpd.read_file(p)
    raise FileNotFoundError(
        "未找到全国界线数据，请确认 data/boundaries/datav/100000_full.json 是否存在")


def china_borders(gdf):
    """拆分「省级政区」与「南海断续线」，返回 (prov, dash)。

    DataV 数据中以 name 为空、adchar=='JD' 的要素表示南海断续线，
    其几何是 MultiPolygon（窄条面）。旧代码把它当普通面要素、用 ls="--" 描边，
    结果被画成散布在南海的十余段零碎小弧线——这是"断续线碎化"的根因。
    正确做法：取窄条面的外环、以实线描边，得到连续的断续线段。
    """
    if "name" in gdf.columns:
        nm = gdf["name"].astype(str).str.strip()
        is_dash = gdf["name"].isna() | (nm == "") | (nm == "nan")
    else:
        is_dash = gdf.index == gdf.index  # 全 False
    return gdf[~is_dash], gdf[is_dash]


_OUTLINE_CACHE = {}


def safe_union(obj):
    """对可能拓扑无效的政区几何做稳健并集。

    DataV 的省界 JSON 中青海、甘肃等省存在自交/悬挂环，直接
    ``gdf.union_all()`` 会抛 ``GEOSException: TopologyException:
    side location conflict``。此处逐个 make_valid（失败再 buffer(0)，
    仍失败则跳过该要素）后求并集。
    obj 可以是 GeoDataFrame / GeoSeries，也可以是几何列表。
    """
    from shapely import make_valid
    from shapely.ops import unary_union

    if obj is None:
        return None
    geoms = list(obj.geometry) if hasattr(obj, "geometry") else list(obj)
    out = []
    for g in geoms:
        if g is None or g.is_empty:
            continue
        try:
            if not g.is_valid:
                g = make_valid(g)
        except Exception:
            try:
                g = g.buffer(0)
            except Exception:
                continue
        if g is not None and not g.is_empty:
            out.append(g)
    if not out:
        return None
    try:
        return unary_union(out)
    except Exception:
        try:
            return unary_union([g.buffer(0) for g in out])
        except Exception:
            return out[0]


def china_outline(prov):
    """省级政区并集（即中国国界内部范围）。

    DataV 的省界数据存在拓扑无效（side location conflict），直接 dissolve 会抛
    GEOSException。此处先逐个 make_valid / buffer(0) 修复再求并集。
    结果按「要素数 + 总范围」缓存：同一份数据在本书几十幅图中反复使用，
    每幅都重算 unary_union 会明显拖慢出图。
    """
    try:
        b = tuple(round(v, 3) for v in prov.total_bounds)
        key = (len(prov), b)
    except Exception:
        key = None
    if key is not None and key in _OUTLINE_CACHE:
        return _OUTLINE_CACHE[key]

    out = safe_union(prov)
    if out is None:
        return None
    if key is not None:
        _OUTLINE_CACHE[key] = out
    return out


def draw_borders(ax, prov, dash, z=3,
                 prov_color="#9aa5ad", prov_lw=0.32, prov_alpha=0.85,
                 nat_color="#2f3a44", nat_lw=1.15,
                 dash_color="#1b2631", dash_lw=1.0):
    """已有 prov/dash 拆分结果时，直接绘制「国界 + 省界 + 断续线」骨架。

    全书各章的旧写法都是：
        prov.boundary.plot(color="#5a5a5a", lw=0.28, alpha=0.5)
        dash.plot(facecolor="none", edgecolor=..., ls="--")
    既没有国界，断续线又被当成面用虚线描边而碎成小弧。
    此处统一修正为：省界浅灰细线 + 国界深色粗线 + 断续线实线描边。
    """
    import geopandas as gpd
    if prov is None or len(prov) == 0:
        return prov
    prov.boundary.plot(ax=ax, color=prov_color, linewidth=prov_lw,
                       alpha=prov_alpha, zorder=z)
    outline = china_outline(prov)
    if outline is not None:
        gpd.GeoSeries([outline], crs=prov.crs).boundary.plot(
            ax=ax, color=nat_color, linewidth=nat_lw, zorder=z + 1)
    else:
        prov.boundary.plot(ax=ax, color=nat_color, linewidth=nat_lw, zorder=z + 1)
    if dash is not None and len(dash):
        dash.boundary.plot(ax=ax, color=dash_color, linewidth=dash_lw, zorder=z + 2)
    return prov


def plot_china_frame(ax, gdf, z=3,
                     prov_color="#9aa5ad", prov_lw=0.32, prov_alpha=0.85,
                     nat_color="#2f3a44", nat_lw=1.15,
                     dash_color="#1b2631", dash_lw=1.0,
                     facecolor=None, facealpha=1.0, draw_dash=True):
    """统一绘制中国地图骨架：国界线（深）+ 省界（浅）+ 南海断续线（实线）。

    旧实现全书只调用 prov.boundary.plot(color="#6a6a6a", lw=0.28, alpha=0.5)，
    既不画国界、又把断续线当 Polygon 用 ls="--" 描边（碎成小弧）。
    本函数：国界 = 省界并集的外边界，用明显深于省界的线型；
    断续线 = 窄条面的外环，以实线描边。
    """
    prov, dd = china_borders(gdf)
    if len(prov) == 0:
        return prov, dd

    if facecolor is not None:
        prov.plot(ax=ax, facecolor=facecolor, edgecolor="none",
                  alpha=facealpha, zorder=max(z - 1, 0))

    draw_borders(ax, prov, dd if draw_dash else None, z=z,
                 prov_color=prov_color, prov_lw=prov_lw, prov_alpha=prov_alpha,
                 nat_color=nat_color, nat_lw=nat_lw,
                 dash_color=dash_color, dash_lw=dash_lw)
    return prov, dd


def load_world(resolution="50m"):
    """载入 Natural Earth 各国界线。resolution: '110m' / '50m'。

    本项目实际只落盘了 50m（且是 .geojson），旧实现硬拼
    ne_{res}/ne_{res}_admin_0_countries.shp，110m 一律 DataSourceError。
    此处依次尝试 shapefile / geojson，并允许降级到 50m。
    """
    import geopandas as gpd
    base = os.path.join(DATA, "boundaries", "natural_earth")
    cands = []
    for res in (resolution, "50m", "110m"):
        cands += [
            os.path.join(base, f"ne_{res}", f"ne_{res}_admin_0_countries.shp"),
            os.path.join(base, f"ne_{res}_admin_0_countries.geojson"),
            os.path.join(base, f"ne_{res}_admin_0_countries.shp"),
        ]
    for p in cands:
        if os.path.exists(p):
            return gpd.read_file(p)
    raise FileNotFoundError(
        f"缺少 Natural Earth 国界图层（请求 {resolution}），请置于 "
        f"data/boundaries/natural_earth/ne_50m_admin_0_countries.geojson")


def load_ne_layer(name):
    """读取 Natural Earth 图层，兼容 shapefile 目录与单文件 GeoJSON 两种落盘格式。

    旧代码硬编码 `ne_50m_rivers_lake_centerlines/…shp`，数据缺失时直接抛
    DataSourceError 导致整批图无法重跑。此处在缺失时给出明确的获取提示。
    """
    import geopandas as gpd
    base = os.path.join(DATA, "boundaries", "natural_earth")
    cands = [
        os.path.join(base, name, f"{name}.shp"),
        os.path.join(base, f"{name}.geojson"),
        os.path.join(base, f"{name}.shp"),
    ]
    for p in cands:
        if os.path.exists(p):
            return gpd.read_file(p)
    raise FileNotFoundError(
        f"缺少 Natural Earth 图层 {name}，请置于 "
        f"data/boundaries/natural_earth/{name}/ 或 .geojson")


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
    from volume1_layout import save_volume_figure
    save_volume_figure(fig, os.path.join(FIGURES, filename), dpi=DPI)
    plt.close(fig)


def add_north_arrow(ax, x=0.955, y=0.90, size=0.055):
    """在轴坐标系指定比例位置加指北针。"""
    trans = ax.transAxes
    ax.add_patch(FancyArrow(x, y - size * 0.55, 0, size,
                            width=0.002, head_width=size * 0.42,
                            head_length=size * 0.42, fc="#2c3e50", ec="#2c3e50",
                            length_includes_head=True, transform=trans, zorder=20))
    ax.text(x, y + size * 0.62, "N", transform=trans, ha="center", va="bottom",
            fontsize=11, fontweight="bold", color="#2c3e50", zorder=20)


def add_note(ax, text, x=0.005, y=0.008, fontsize=7.5):
    """左下角来源/说明注记。"""
    ax.text(x, y, text, transform=ax.transAxes, ha="left", va="bottom",
            fontsize=fontsize, color="#555555", zorder=20,
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.75))


def add_title(ax, title, subtitle=None, pad=24):
    """地图标题与副标题，置于坐标轴之外（画布上方）。

    旧实现用 ax.text(..., y=0.985) 把标题画在轴内部顶端，必然压在地图最北侧
    要素与国界上。改用 matplotlib 原生 set_title（参与 tight_layout 布局）
    + 轴外副标题，标题不再遮挡任何地图内容。
    """
    ax.set_title(title, fontsize=15, fontweight="bold", color=C_TEXT, pad=pad)
    if subtitle:
        ax.text(0.5, 1.006, subtitle, transform=ax.transAxes, ha="center",
                va="bottom", fontsize=10, color="#555555")


def add_map_caption(fig, text, y=0.012):
    """画布底部说明（图幅之外），避免图内文字遮挡。"""
    fig.text(0.5, y, text, ha="center", va="bottom", fontsize=8.2, color="#555555")


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
