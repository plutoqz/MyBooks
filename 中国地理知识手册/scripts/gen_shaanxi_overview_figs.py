# -*- coding: utf-8 -*-
"""陕西省省级地理统揽专题地图生成引擎（25-00）
包含 5 幅全省出版级权威地图与分析图表（精细调优排版、严格杜绝压盖）：
1. fig25-00-1_陕西省地势起伏与骨干河流水系格局图.png
2. fig25-00-2_陕西省10个市行政区划与西安都市圈空间战略格局图.png
3. fig25-00-3_陕西省综合立体交通网络与亚欧大陆桥国际通道格局图.png
4. fig25-00-4_陕西省特色优势产业集群与先进制造能源基地空间分布图.png
5. fig25-00-5_陕西省1986-2024年夜间灯光演化与开发强度对比图.png
"""
import os
import sys
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import Rectangle, Patch, PathPatch
from shapely.geometry import Polygon as ShpPolygon
from matplotlib.path import Path
from matplotlib.lines import Line2D
from matplotlib.colors import LinearSegmentedColormap, Normalize
from pyproj import Transformer

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册"
sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))
from style import ALBERS, C_TEXT, DATA, DPI, FIGURES, setup
import mapkit
from shaanxi_configs import SHAANXI_OVERVIEW
from shaanxi_city_configs import SHAANXI_CITY_CONFIGS

setup()
OUT_DIR = os.path.join(BASE_DIR, "figures")
os.makedirs(OUT_DIR, exist_ok=True)
_T = Transformer.from_crs("EPSG:4326", ALBERS, always_xy=True)

def to_alb(lon, lat):
    return _T.transform(lon, lat)

def get_mpl_clip_patch(poly_geom):
    if poly_geom.geom_type == 'Polygon':
        geoms = [poly_geom]
    else:
        geoms = list(poly_geom.geoms)
    all_verts = []
    all_codes = []
    for g in geoms:
        ext = np.array(g.exterior.coords)
        verts = list(ext)
        codes = [Path.MOVETO] + [Path.LINETO] * (len(verts) - 2) + [Path.CLOSEPOLY]
        all_verts.extend(verts)
        all_codes.extend(codes)
        for interior in g.interiors:
            intr = np.array(interior.coords)
            verts = list(intr)
            codes = [Path.MOVETO] + [Path.LINETO] * (len(verts) - 2) + [Path.CLOSEPOLY]
            all_verts.extend(verts)
            all_codes.extend(codes)
    mpl_path = Path(all_verts, all_codes)
    return PathPatch(mpl_path, facecolor='none', edgecolor='none')

def calc_hillshade(dem, res, az=315.0, alt=45.0):
    az_rad = np.radians(az)
    alt_rad = np.radians(alt)
    d = np.nan_to_num(dem, nan=0.0)
    gy, gx = np.gradient(d, res)
    slope = np.arctan(np.sqrt(gx * gx + gy * gy))
    aspect = np.arctan2(-gx, gy)
    shaded = np.sin(alt_rad) * np.cos(slope) + np.cos(alt_rad) * np.sin(slope) * np.cos(az_rad - aspect)
    return np.clip(shaded, 0.0, 1.0)

def add_compass(ax, x=0.94, y=0.92):
    ax.annotate("N", xy=(x, y), xytext=(x, y - 0.055), transform=ax.transAxes,
                arrowprops=dict(facecolor="#2c3e50", edgecolor="#2c3e50", width=1.8, headwidth=5.5, headlength=6.5),
                ha="center", va="center", fontsize=8.8, fontweight="bold", color="#2c3e50", zorder=30)

print("Loading Shaanxi provincial boundaries and DEM...")
DATA_DIR = os.path.join(BASE_DIR, "data")
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")

sn_all = gpd.read_file(os.path.join(DATAV_DIR, "610000_full.json")).to_crs(ALBERS)
sn_all["geometry"] = sn_all.geometry.buffer(0)
sn_union = sn_all.union_all()

b = sn_all.total_bounds
span_x = b[2] - b[0]
span_y = b[3] - b[1]
pad_x = span_x * 0.04
pad_y = span_y * 0.04
ax_xlim = (b[0] - pad_x, b[2] + pad_x)
ax_ylim = (b[1] - pad_y, b[3] + pad_y)

dem_file = os.path.join(DATA_DIR, "dem", "province", "610000_z9.npz")
dem_data = np.load(dem_file)
step = 3
dem_raw = dem_data['dem'][::step, ::step]
res = float(dem_data['res']) * step
minx = float(dem_data['minx'])
maxy = float(dem_data['maxy'])
nrows, ncols = dem_raw.shape
dem_extent = [minx, minx + ncols * res, maxy - nrows * res, maxy]

dem_elev = np.where(dem_raw < 0, np.nan, dem_raw)
hillshade = calc_hillshade(dem_elev, res)

terrain_cmap = LinearSegmentedColormap.from_list("sn_terrain", [
    (0.0, "#27ae60"),   # 汉江白石河口/关中渭河低谷 (168m ~ 500m) 柔绿
    (0.15, "#a9dfbf"),  # 关中平原与汉中盆地 (500m ~ 800m) 浅绿
    (0.30, "#f9e79f"),  # 陕北黄土丘陵沟壑区 (800m ~ 1300m) 暖黄
    (0.48, "#f5b041"),  # 陕北北部风沙草滩/秦巴低中山 (1300m ~ 1800m) 橙黄
    (0.68, "#e59866"),  # 西岳华山/秦岭中山区 (1800m ~ 2500m) 棕褐
    (0.85, "#873600"),  # 秦岭高山区/牛背梁 (2500m ~ 3200m) 暗褐
    (1.0, "#ffffff")    # 太白山拔仙台雪线极顶 (3200m ~ 3771.2m) 纯白
])

# =============================================================================
# 图 1: 陕西省地势起伏与骨干河流水系格局图
# =============================================================================
def plot_fig1():
    print("Rendering fig25-00-1: Shaanxi topography & river network...")
    fig, ax = plt.subplots(figsize=(8.8, 10.5), dpi=DPI)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.94, bottom=0.02)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    norm = Normalize(vmin=168.6, vmax=3771.2)
    rgb_c = terrain_cmap(norm(dem_elev))[:, :, :3]
    rgb_s = np.clip(rgb_c * (hillshade[:, :, np.newaxis] * 0.72 + 0.28), 0.0, 1.0)

    im = ax.imshow(rgb_s, extent=dem_extent, origin="upper", zorder=1)
    clip_patch = get_mpl_clip_patch(sn_union)
    ax.add_patch(clip_patch)
    im.set_clip_path(clip_patch)

    sn_all.boundary.plot(ax=ax, color="#7f8c8d", lw=0.6, ls="--", zorder=3)
    gpd.GeoSeries([sn_union]).boundary.plot(ax=ax, color="#1b4f72", lw=1.6, zorder=4)

    # 绘制骨干水系
    for rname, rcoords, rcolor, rwidth in SHAANXI_OVERVIEW["major_rivers"]:
        pts = [to_alb(c[0], c[1]) for c in rcoords]
        xs, ys = zip(*pts)
        ax.plot(xs, ys, color=rcolor, lw=rwidth, alpha=0.9, zorder=5)
        mid_idx = len(xs) // 2
        ax.text(xs[mid_idx], ys[mid_idx], rname.split()[0], fontsize=7.2, color="#0b5345",
                fontweight="bold", ha="center", va="center",
                path_effects=[pe.withStroke(linewidth=2.0, foreground="#ffffff")], zorder=6)

    sl = mapkit.SymbolLabels(ax, fig)
    sl.reserve([(0.0, 0.0, 0.32, 0.24), (0.70, 0.0, 1.0, 0.12), (0.84, 0.84, 1.0, 1.0)])

    for item in SHAANXI_OVERVIEW["landmarks_macro"]:
        name, lon, lat, ltype = item[0], item[1], item[2], item[3]
        x, y = to_alb(lon, lat)
        nm, nt = mapkit.split_note(name)
        if ltype == "peak_max":
            sl.add(x, y, nm, "peak_max", note=nt, priority=0, marker="^", face="#78281f", size=9.5,
                   kind_label="省域最高极顶 (秦岭拔仙台)")
        elif ltype == "peak":
            sl.add(x, y, nm, "peak", note=nt, priority=1, marker="^", face="#935116", size=7.8,
                   kind_label="五岳名山 / 秦岭世界地质公园")
        elif ltype == "waterfall":
            sl.add(x, y, nm, "waterfall", note=nt, priority=1, marker="o", face="#b7950b", size=7.5,
                   kind_label="黄河壶口瀑布大奇观")
        elif ltype == "heritage":
            sl.add(x, y, nm, "heritage", note=nt, priority=2, marker="D", face="#b7950b", size=7.0,
                   kind_label="世界文化遗产与革命圣地")
        elif ltype == "lake":
            sl.add(x, y, nm, "lake", note=nt, priority=2, marker="o", face="#1b4f72", size=6.8,
                   kind_label="中国最大沙漠淡水湖泊")
        else:
            sl.add(x, y, nm, "energy", note=nt, priority=2, marker="s", face="#154360", size=7.0,
                   kind_label="世界级特大型煤田与能化基地")

    sym_type_h, sym_idx_h = sl.flush()

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    sb_x0 = ax_xlim[0] + span_x * 0.05
    sb_y0 = ax_ylim[0] + span_y * 0.05
    mapkit.add_scalebar(ax, sb_x0, sb_y0, length_km=100)
    add_compass(ax, 0.94, 0.92)

    cax = ax.inset_axes([0.04, 0.10, 0.025, 0.30])
    cb = plt.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=terrain_cmap), cax=cax, orientation="vertical")
    cb.set_label("高程 Elevation (m)", fontsize=6.8, color="#2c3e50")
    cb.ax.tick_params(labelsize=6.0, length=2.0)

    leg = mapkit.stacked_legends(ax, [
        dict(handles=sym_type_h, title="宏观自然地貌与控制性地标", ncol=2, fontsize=6.8, title_fontsize=7.6),
        dict(handles=sym_idx_h, title="重要地理要素编号对照", ncol=2, fontsize=6.8, title_fontsize=7.6),
    ], top=-0.010, gap=0.014)

    ax.set_title("陕西省地势起伏与骨干河流水系格局图", fontsize=12.5, fontweight="bold", pad=20, color=C_TEXT)
    ax.text(0.5, 1.008, "Topography, Landforms & Major River Networks of Shaanxi Province",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
    mapkit.footer_below_legend(ax, leg, "数据源：AWS Terrain GLO-30 DEM · 水利部黄河/长江流域公报 · 制作：《中国地理知识手册》", fontsize=6.5)

    out_file = os.path.join(OUT_DIR, "fig25-00-1_陕西省地势起伏与骨干河流水系格局图.png")
    fig.savefig(out_file, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f" Saved: {out_file}")

# =============================================================================
# 图 2: 陕西省 10 个市行政区划与西安都市圈空间战略格局图
# =============================================================================
def plot_fig2():
    print("Rendering fig25-00-2: Shaanxi 10 cities & Xi'an Metropolitan Area...")
    fig, ax = plt.subplots(figsize=(8.8, 10.5), dpi=DPI)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.94, bottom=0.02)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    city_colors = {
        "610100": "#d4e6f1",  # 西安 (深蓝)
        "610200": "#fcf3cf",  # 铜川 (暖黄)
        "610300": "#d5f5e3",  # 宝鸡 (柔绿)
        "610400": "#fadbd8",  # 咸阳 (浅红)
        "610500": "#ebdef0",  # 渭南 (紫罗兰)
        "610600": "#fdebd0",  # 延安 (金黄)
        "610700": "#d1f2eb",  # 汉中 (青绿)
        "610800": "#e8f8f5",  # 榆林 (浅翠)
        "610900": "#a9dfbf",  # 安康 (秦巴绿)
        "611000": "#f5cba7",  # 商洛 (暖橙)
    }

    for _, row in sn_all.iterrows():
        c_code = str(row.get("adcode", ""))
        c_fill = city_colors.get(c_code, "#f2f3f4")
        gpd.GeoSeries([row.geometry]).plot(ax=ax, facecolor=c_fill, edgecolor="#7f8c8d", lw=0.8, zorder=2)
        c_name = row.get("name", "")
        pt = row.geometry.representative_point()
        ax.text(pt.x, pt.y, c_name, fontsize=8.5, fontweight="bold", color="#1a252f", ha="center", va="center",
                path_effects=[pe.withStroke(linewidth=2.2, foreground="#ffffff")], zorder=6)

    gpd.GeoSeries([sn_union]).boundary.plot(ax=ax, color="#1b4f72", lw=1.8, zorder=4)

    sl = mapkit.SymbolLabels(ax, fig)
    sl.reserve([(0.0, 0.0, 0.32, 0.22), (0.70, 0.0, 1.0, 0.12), (0.84, 0.84, 1.0, 1.0)])

    for item in SHAANXI_OVERVIEW["strategy_nodes"]:
        name, lon, lat, stype = item[0], item[1], item[2], item[3]
        x, y = to_alb(lon, lat)
        nm, nt = mapkit.split_note(name)
        if stype == "core":
            sl.add(x, y, nm, "core", note=nt, priority=0, marker="*", face="#c0392b", size=10.5,
                   kind_label="省域双核引领中心 (西安-咸阳)")
        elif stype == "subcore":
            sl.add(x, y, nm, "subcore", note=nt, priority=1, marker="D", face="#8e44ad", size=7.8,
                   kind_label="省域副中心城市 (榆林/宝鸡/延安)")
        elif stype == "agri_tech":
            sl.add(x, y, nm, "agri_tech", note=nt, priority=2, marker="s", face="#1e8449", size=7.2,
                   kind_label="国家级现代农业高新技术产业示范区")
        else:
            sl.add(x, y, nm, "node", note=nt, priority=2, marker="o", face="#1f618d", size=6.5,
                   kind_label="区域战略枢纽城市 / 秦巴生态节点")

    sym_type_h, sym_idx_h = sl.flush()

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    sb_x0 = ax_xlim[0] + span_x * 0.05
    sb_y0 = ax_ylim[0] + span_y * 0.05
    mapkit.add_scalebar(ax, sb_x0, sb_y0, length_km=100)
    add_compass(ax, 0.94, 0.92)

    leg = mapkit.stacked_legends(ax, [
        dict(handles=sym_type_h, title="空间战略发展梯队", ncol=2, fontsize=6.8, title_fontsize=7.6),
        dict(handles=sym_idx_h, title="战略节点编号对照", ncol=2, fontsize=6.8, title_fontsize=7.6),
    ], top=-0.010, gap=0.014)

    ax.set_title("陕西省10个市行政区划与西安都市圈空间战略格局图", fontsize=12.5, fontweight="bold", pad=20, color=C_TEXT)
    ax.text(0.5, 1.008, "Administrative Divisions & Xi'an Metropolitan Area of Shaanxi",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
    mapkit.footer_below_legend(ax, leg, "数据源：自然资源部标准地图服务 · 陕西省“十四五”新型城镇化规划 · 制作：《中国地理知识手册》", fontsize=6.5)

    out_file = os.path.join(OUT_DIR, "fig25-00-2_陕西省10个市行政区划与西安都市圈空间战略格局图.png")
    fig.savefig(out_file, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f" Saved: {out_file}")

# =============================================================================
# 图 3: 陕西省综合立体交通网络与亚欧大陆桥国际通道格局图
# =============================================================================
def plot_fig3():
    print("Rendering fig25-00-3: Shaanxi transport & Eurasian Land Bridge corridors...")
    fig, ax = plt.subplots(figsize=(8.8, 10.5), dpi=DPI)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.94, bottom=0.02)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#fcfcfc")

    sn_all.plot(ax=ax, facecolor="#f4f6f7", edgecolor="#bdc3c7", lw=0.6, zorder=1)
    gpd.GeoSeries([sn_union]).boundary.plot(ax=ax, color="#2c3e50", lw=1.6, zorder=2)

    sl = mapkit.SymbolLabels(ax, fig)
    sl.reserve([(0.0, 0.0, 0.32, 0.22), (0.70, 0.0, 1.0, 0.12), (0.84, 0.84, 1.0, 1.0)])

    trans_nodes = [
        ("西安北站 (全国特大型高铁十字枢纽)", 108.94, 34.38, "rail"),
        ("西安站 (百年陇海铁路现代化特等客站)", 108.96, 34.28, "station"),
        ("西安国际港站 (中欧班列长安号集结中心)", 109.08, 34.39, "port"),
        ("西安咸阳国际机场 (4F级双跑道三期空港)", 108.75, 34.44, "airport"),
        ("宝鸡南站 (徐兰高铁西出关中枢纽大站)", 107.20, 34.34, "rail"),
        ("渭南北站 (徐兰与大西高铁交汇站)", 109.52, 34.54, "rail"),
        ("汉中站 (西成高铁汉中盆地枢纽站)", 107.03, 33.08, "rail"),
        ("延安站 (包西铁路陕北客运枢纽)", 109.48, 36.54, "station"),
        ("榆林榆阳机场 (高高原百万级航空港)", 109.60, 38.36, "airport"),
        ("安康站 (阳安襄渝西康铁路三线交汇枢纽)", 109.04, 32.70, "station"),
        ("浩吉铁路浩勒报吉起点 (北煤南运超级重载)", 108.90, 38.45, "port"),
        ("秦岭终南山公路隧道 (世界最长双洞公路隧道)", 108.98, 33.85, "bridge"),
    ]

    for item in trans_nodes:
        name, lon, lat, ttype = item[0], item[1], item[2], item[3]
        x, y = to_alb(lon, lat)
        nm, nt = mapkit.split_note(name)
        if ttype == "rail":
            sl.add(x, y, nm, "rail", note=nt, priority=0, marker="s", face="#1b4f72", size=6.5,
                   kind_label="高速铁路客货综合枢纽")
        elif ttype == "airport":
            sl.add(x, y, nm, "airport", note=nt, priority=1, marker="^", face="#196f3d", size=6.8,
                   kind_label="民用运输航空港 (4F级门户及支线)")
        elif ttype == "bridge":
            sl.add(x, y, nm, "bridge", note=nt, priority=0, marker="D", face="#b7950b", size=7.2,
                   kind_label="秦岭终南山超级隧道工程")
        elif ttype == "port":
            sl.add(x, y, nm, "port", note=nt, priority=2, marker="o", face="#154360", size=6.0,
                   kind_label="中欧班列集结港 / 重载铁路枢纽")
        else:
            sl.add(x, y, nm, "station", note=nt, priority=1, marker="s", face="#2c3e50", size=6.0,
                   kind_label="普速干线特等与一等客货火车站")

    sym_type_h, sym_idx_h = sl.flush()

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    sb_x0 = ax_xlim[0] + span_x * 0.05
    sb_y0 = ax_ylim[0] + span_y * 0.05
    mapkit.add_scalebar(ax, sb_x0, sb_y0, length_km=100)
    add_compass(ax, 0.94, 0.92)

    leg = mapkit.stacked_legends(ax, [
        dict(handles=sym_type_h, title="综合交通设施分类", ncol=2, fontsize=6.8, title_fontsize=7.6),
        dict(handles=sym_idx_h, title="交通通道编号对照", ncol=2, fontsize=6.8, title_fontsize=7.6),
    ], top=-0.010, gap=0.014)

    ax.set_title("陕西省综合立体交通网络与亚欧大陆桥国际通道格局图", fontsize=12.5, fontweight="bold", pad=20, color=C_TEXT)
    ax.text(0.5, 1.008, "Comprehensive Transport Network & Eurasian Land Bridge of Shaanxi",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
    mapkit.footer_below_legend(ax, leg, "数据源：中国国家铁路集团 · 交通运输部 · 制作：《中国地理知识手册》", fontsize=6.5)

    out_file = os.path.join(OUT_DIR, "fig25-00-3_陕西省综合立体交通网络与亚欧大陆桥国际通道格局图.png")
    fig.savefig(out_file, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f" Saved: {out_file}")

# =============================================================================
# 图 4: 陕西省特色优势产业集群与先进制造能源基地空间分布图
# =============================================================================
def plot_fig4():
    print("Rendering fig25-00-4: Shaanxi Advantage Industries & Advanced Manufacturing...")
    fig, ax = plt.subplots(figsize=(8.8, 10.5), dpi=DPI)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.94, bottom=0.02)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    sn_all.plot(ax=ax, facecolor="#fef9e7", edgecolor="#f1c40f", lw=0.6, zorder=1)
    gpd.GeoSeries([sn_union]).boundary.plot(ax=ax, color="#b7950b", lw=1.6, zorder=2)

    sl = mapkit.SymbolLabels(ax, fig)
    sl.reserve([(0.0, 0.0, 0.32, 0.22), (0.70, 0.0, 1.0, 0.12), (0.84, 0.84, 1.0, 1.0)])

    industry_nodes = [
        ("西安阎良国家航空高技术产业基地 (西飞集团)", 109.30, 34.65, "aviation"),
        ("西安高新区三星电子半导体芯片工厂", 108.82, 34.16, "chip"),
        ("比亚迪西安高新区新能源汽车全球制造基地", 108.72, 34.06, "auto"),
        ("陕煤集团神木煤炭分质利用多联产基地", 110.45, 38.80, "energy"),
        ("延长石油延安煤油气资源综合利用园区", 109.95, 36.55, "energy"),
        ("宝鸡·中国钛谷宝钛集团核心基地", 107.28, 34.35, "titanium"),
        ("杨凌现代农业种业创新硅谷示范中心", 108.08, 34.28, "agri"),
        ("陕西飞机工业有限责任公司 (城固中型战鹰基地)", 107.35, 33.13, "aviation"),
        ("西凤酒集团凤翔柳林名镇古法酿造区", 107.42, 34.53, "liquor"),
        ("洛川现代苹果科技深加工现代农业产业园", 109.44, 35.75, "apple"),
        ("铜仁大龙/安康毛绒玩具新都产业集聚区", 109.01, 32.74, "toy"),
    ]

    for item in industry_nodes:
        name, lon, lat, itype = item[0], item[1], item[2], item[3]
        x, y = to_alb(lon, lat)
        nm, nt = mapkit.split_note(name)
        if itype == "aviation":
            sl.add(x, y, nm, "aviation", note=nt, priority=0, marker="^", face="#154360", size=7.2,
                   kind_label="大国航空战鹰制造基地 (运-20/运-9)")
        elif itype == "chip" or itype == "auto":
            sl.add(x, y, nm, "tech", note=nt, priority=0, marker="s", face="#6c3483", size=7.0,
                   kind_label="半导体芯片与新能源汽车万亿产业集群")
        elif itype == "energy":
            sl.add(x, y, nm, "energy", note=nt, priority=1, marker="D", face="#b7950b", size=7.0,
                   kind_label="现代高端煤油气综合能源化工基地")
        elif itype == "titanium":
            sl.add(x, y, nm, "titanium", note=nt, priority=1, marker="D", face="#117864", size=6.8,
                   kind_label="中国钛谷·先进结构钛金属材料基地")
        elif itype == "agri" or itype == "apple":
            sl.add(x, y, nm, "agri", note=nt, priority=2, marker="o", face="#1e8449", size=6.8,
                   kind_label="国家农高区与世界优质苹果现代基地")
        else:
            sl.add(x, y, nm, "liquor", note=nt, priority=2, marker="o", face="#c0392b", size=6.5,
                   kind_label="凤香型名酒与特色轻工出口高地")

    sym_type_h, sym_idx_h = sl.flush()

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    sb_x0 = ax_xlim[0] + span_x * 0.05
    sb_y0 = ax_ylim[0] + span_y * 0.05
    mapkit.add_scalebar(ax, sb_x0, sb_y0, length_km=100)
    add_compass(ax, 0.94, 0.92)

    leg = mapkit.stacked_legends(ax, [
        dict(handles=sym_type_h, title="特色优势产业门类", ncol=2, fontsize=6.8, title_fontsize=7.6),
        dict(handles=sym_idx_h, title="产业集群编号对照", ncol=2, fontsize=6.8, title_fontsize=7.6),
    ], top=-0.010, gap=0.014)

    ax.set_title("陕西省特色优势产业集群与先进制造能源基地空间分布图", fontsize=12.5, fontweight="bold", pad=20, color=C_TEXT)
    ax.text(0.5, 1.008, "Advantage Industry Clusters & Advanced Manufacturing of Shaanxi",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
    mapkit.footer_below_legend(ax, leg, "数据源：陕西省发展和改革委员会 · 陕西省工业和信息化厅 · 制作：《中国地理知识手册》", fontsize=6.5)

    out_file = os.path.join(OUT_DIR, "fig25-00-4_陕西省特色优势产业集群与先进制造能源基地空间分布图.png")
    fig.savefig(out_file, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f" Saved: {out_file}")

# =============================================================================
# 图 5: 陕西省 1986-2024 年夜间灯光演化与开发强度对比图
# =============================================================================
def plot_fig5():
    print("Rendering fig25-00-5: Shaanxi Nightlight evolution 1986-2024...")
    fig, (ax_nl, ax_gdp) = plt.subplots(1, 2, figsize=(11.0, 5.2), dpi=DPI)
    fig.subplots_adjust(left=0.07, right=0.96, top=0.88, bottom=0.14, wspace=0.22)
    fig.patch.set_facecolor("white")

    nl_file = os.path.join(DATA_DIR, "shaanxi_nightlight_clean.csv")
    nl_df = pd.read_csv(nl_file)
    nl_agg = nl_df.groupby("year")["sum"].sum().reset_index().sort_values("year")

    years = nl_agg["year"].values
    sums = nl_agg["sum"].values

    ax_nl.plot(years, sums, color="#d35400", lw=2.2, marker="o", ms=4.0, label="全省夜光总辐射 (DN)")
    ax_nl.fill_between(years, sums, color="#fdebd0", alpha=0.55)

    annotations = [
        (1996, 38000, 1989, 90000, "1996: 关中老工业走廊微弱灯火初显"),
        (2005, 110000, 1998, 200000, "2005: 陕北能源大开发·西宝高速贯通"),
        (2015, 310000, 2008, 430000, "2015: 国家级西咸新区设立·高铁成网"),
        (2023, 730000, 2017, 850000, "2023: 西安都市圈获批·陕北能化万亿爆发"),
    ]

    for y_pt, val_est, text_x, text_y, note in annotations:
        sub_pt = nl_agg[nl_agg["year"] == y_pt]
        if not sub_pt.empty:
            real_val = float(sub_pt["sum"].values[0])
            ax_nl.annotate(note, xy=(y_pt, real_val), xytext=(text_x, text_y),
                           arrowprops=dict(arrowstyle="->", color="#c0392b", lw=0.9),
                           fontsize=7.0, fontweight="bold", color="#78281f",
                           bbox=dict(boxstyle="round,pad=0.25", facecolor="#ffffff", edgecolor="#e74c3c", alpha=0.92))

    ax_nl.set_title("陕西省 1986—2024 年夜间灯光总辐射时序跃迁演进", fontsize=10.5, fontweight="bold", color=C_TEXT)
    ax_nl.set_ylabel("夜间灯光辐射总积分 (DN)", fontsize=7.8, color="#2c3e50")
    ax_nl.set_xlabel("年份 Year", fontsize=7.8, color="#2c3e50")
    ax_nl.grid(True, linestyle="--", alpha=0.45)
    ax_nl.tick_params(labelsize=7.0)

    # 10 市 2024 年 GDP 对比图
    cities = []
    gdps = []
    for code, cfg in SHAANXI_CITY_CONFIGS.items():
        cities.append(cfg["name"].replace("市", ""))
        gdps.append(cfg["gdp_2024"])

    bars = ax_gdp.bar(cities, gdps, color="#1b4f72", edgecolor="#0b2545", alpha=0.85, width=0.6)
    for bar in bars:
        h = bar.get_height()
        ax_gdp.text(bar.get_x() + bar.get_width() / 2.0, h + 150.0, f"{h:g}",
                    ha="center", va="bottom", fontsize=6.8, fontweight="bold", color="#0b2545")

    ax_gdp.set_title("陕西省 10 个地级市 2024 年经济总量 (GDP, 亿元) 空间梯度格局", fontsize=10.5, fontweight="bold", color=C_TEXT)
    ax_gdp.set_ylabel("地区生产总值 (GDP, 亿元)", fontsize=7.8, color="#2c3e50")
    ax_gdp.set_xlabel("城市名称 City", fontsize=7.8, color="#2c3e50")
    ax_gdp.set_ylim(0, max(gdps) * 1.15)
    ax_gdp.grid(True, linestyle="--", alpha=0.45, axis="y")
    ax_gdp.tick_params(labelsize=7.0)

    fig.tight_layout(pad=2.5)
    fig.text(0.5, 0.01, "数据来源：夜间灯光遥感时序数据集 (1986-2024) · 陕西省统计局国民经济和社会发展统计公报 · 制作：《中国地理知识手册》",
             ha="center", va="bottom", fontsize=6.5, color="#7f8c8d")

    out_file = os.path.join(OUT_DIR, "fig25-00-5_陕西省1986-2024年夜间灯光演化与开发强度对比图.png")
    fig.savefig(out_file, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f" Saved: {out_file}")

def main():
    plot_fig1()
    plot_fig2()
    plot_fig3()
    plot_fig4()
    plot_fig5()
    print("\n=== SHAANXI OVERVIEW FIGURES GENERATION COMPLETE ===")

if __name__ == "__main__":
    main()
