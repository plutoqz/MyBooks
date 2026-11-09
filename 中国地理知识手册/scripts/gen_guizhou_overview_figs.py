# -*- coding: utf-8 -*-
"""贵州省省级地理统揽专题地图生成引擎（23-00）
包含 5 幅全省出版级权威地图与分析图表（精细调优排版、严格杜绝压盖）：
1. fig23-00-1_贵州省地势起伏与骨干河流水系格局图.png
2. fig23-00-2_贵州省9个市州行政区划与黔中城市群空间战略格局图.png
3. fig23-00-3_贵州省综合立体交通网络与世界桥梁博物馆大通道格局图.png
4. fig23-00-4_贵州省特色优势产业集群与中国数谷算力高地空间分布图.png
5. fig23-00-5_贵州省1986-2024年夜间灯光演化与开发强度对比图.png
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
from guizhou_configs import GUIZHOU_OVERVIEW
from guizhou_city_configs import GUIZHOU_CITY_CONFIGS

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

print("Loading Guizhou provincial boundaries and DEM...")
DATA_DIR = os.path.join(BASE_DIR, "data")
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")

gz_all = gpd.read_file(os.path.join(DATAV_DIR, "520000_full.json")).to_crs(ALBERS)
gz_all["geometry"] = gz_all.geometry.buffer(0)
gz_union = gz_all.union_all()

b = gz_all.total_bounds
span_x = b[2] - b[0]
span_y = b[3] - b[1]
pad_x = span_x * 0.04
pad_y = span_y * 0.04
ax_xlim = (b[0] - pad_x, b[2] + pad_x)
ax_ylim = (b[1] - pad_y, b[3] + pad_y)

dem_file = os.path.join(DATA_DIR, "dem", "province", "520000_z9.npz")
dem_data = np.load(dem_file)
step = 2
dem_raw = dem_data['dem'][::step, ::step]
res = float(dem_data['res']) * step
minx = float(dem_data['minx'])
maxy = float(dem_data['maxy'])
nrows, ncols = dem_raw.shape
dem_extent = [minx, minx + ncols * res, maxy - nrows * res, maxy]

dem_elev = np.where(dem_raw < 0, np.nan, dem_raw)
hillshade = calc_hillshade(dem_elev, res)

terrain_cmap = LinearSegmentedColormap.from_list("gz_terrain", [
    (0.0, "#2e7d32"),   # 峡谷河谷低地 翠绿 (148m ~ 600m)
    (0.18, "#81c784"),  # 丘陵平坝 浅绿 (600m ~ 1000m)
    (0.35, "#d4e157"),  # 低山谷地 浅黄绿 (1000m ~ 1400m)
    (0.55, "#ffd54f"),  # 喀斯特山原 暖黄 (1400m ~ 1900m)
    (0.75, "#ff8a65"),  # 苗岭大娄山高山 橙褐 (1900m ~ 2400m)
    (0.90, "#8d6e63"),  # 乌蒙高山灰岩 灰褐 (2400m ~ 2700m)
    (1.0, "#f5f5f5")    # 贵州屋脊韭菜坪极顶 (2700m ~ 2900.6m)
])

# =============================================================================
# 图 1: 贵州省地势起伏与骨干河流水系格局图
# =============================================================================
def plot_fig1():
    print("Rendering fig23-00-1: Guizhou topography & river network...")
    fig, ax = plt.subplots(figsize=(10.5, 8.8), dpi=DPI)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.94, bottom=0.02)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    norm = Normalize(vmin=148.0, vmax=2900.6)
    rgb_c = terrain_cmap(norm(dem_elev))[:, :, :3]
    rgb_s = np.clip(rgb_c * (hillshade[:, :, np.newaxis] * 0.72 + 0.28), 0.0, 1.0)

    im = ax.imshow(rgb_s, extent=dem_extent, origin="upper", zorder=1)
    clip_patch = get_mpl_clip_patch(gz_union)
    ax.add_patch(clip_patch)
    im.set_clip_path(clip_patch)

    gz_all.boundary.plot(ax=ax, color="#7f8c8d", lw=0.6, ls="--", zorder=3)
    gpd.GeoSeries([gz_union]).boundary.plot(ax=ax, color="#1b4f72", lw=1.6, zorder=4)

    # 绘制骨干水系
    for rname, rcoords, rcolor, rwidth in GUIZHOU_OVERVIEW["major_rivers"]:
        pts = [to_alb(c[0], c[1]) for c in rcoords]
        xs, ys = zip(*pts)
        ax.plot(xs, ys, color=rcolor, lw=rwidth, alpha=0.9, zorder=5)
        mid_idx = len(xs) // 2
        ax.text(xs[mid_idx], ys[mid_idx], rname.split()[0], fontsize=7.2, color="#0b5345",
                fontweight="bold", ha="center", va="center",
                path_effects=[pe.withStroke(linewidth=2.0, foreground="#ffffff")], zorder=6)

    sl = mapkit.SymbolLabels(ax, fig)
    sl.reserve([(0.0, 0.0, 0.32, 0.24), (0.70, 0.0, 1.0, 0.12), (0.84, 0.84, 1.0, 1.0)])

    for item in GUIZHOU_OVERVIEW["landmarks_macro"]:
        name, lon, lat, ltype = item[0], item[1], item[2], item[3]
        x, y = to_alb(lon, lat)
        nm, nt = mapkit.split_note(name)
        if ltype == "peak_max":
            sl.add(x, y, nm, "peak_max", note=nt, priority=0, marker="^", face="#78281f", size=9.5,
                   kind_label="省域最高峰 (贵州屋脊)")
        elif ltype == "peak":
            sl.add(x, y, nm, "peak", note=nt, priority=1, marker="^", face="#935116", size=7.8,
                   kind_label="骨干山脉名峰 / 历史雄关")
        elif ltype == "water_fall":
            sl.add(x, y, nm, "water_fall", note=nt, priority=1, marker="o", face="#1b4f72", size=7.5,
                   kind_label="举世闻名大瀑布 / 喀斯特水景")
        elif ltype == "bridge":
            sl.add(x, y, nm, "bridge", note=nt, priority=2, marker="D", face="#b7950b", size=7.0,
                   kind_label="世界级超级桥梁丰碑")
        elif ltype == "tech":
            sl.add(x, y, nm, "tech", note=nt, priority=2, marker="s", face="#6c3483", size=7.0,
                   kind_label="国家重大科技基础设施 (FAST)")
        else:
            sl.add(x, y, nm, "scenic", note=nt, priority=2, marker="o", face="#27ae60", size=6.8,
                   kind_label="世界自然遗产与生态胜迹")

    sym_type_h, sym_idx_h = sl.flush()

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    sb_x0 = ax_xlim[0] + span_x * 0.05
    sb_y0 = ax_ylim[0] + span_y * 0.05
    mapkit.add_scalebar(ax, sb_x0, sb_y0, length_km=50)
    add_compass(ax, 0.94, 0.92)

    cax = ax.inset_axes([0.04, 0.12, 0.025, 0.28])
    cb = plt.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=terrain_cmap), cax=cax, orientation="vertical")
    cb.set_label("高程 Elevation (m)", fontsize=6.8, color="#2c3e50")
    cb.ax.tick_params(labelsize=6.0, length=2.0)

    leg = mapkit.stacked_legends(ax, [
        dict(handles=sym_type_h, title="宏观自然地貌与控制性地标", ncol=2, fontsize=6.8, title_fontsize=7.6),
        dict(handles=sym_idx_h, title="重要地理要素编号对照", ncol=2, fontsize=6.8, title_fontsize=7.6),
    ], top=-0.010, gap=0.014)

    ax.set_title("贵州省地势起伏与骨干河流水系格局图", fontsize=12.5, fontweight="bold", pad=20, color=C_TEXT)
    ax.text(0.5, 1.008, "Topography, Landforms & Major River Networks of Guizhou Province",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
    mapkit.footer_below_legend(ax, leg, "数据源：AWS Terrain GLO-30 DEM · 水利部水文水资源公报 · 制作：《中国地理知识手册》", fontsize=6.5)

    out_file = os.path.join(OUT_DIR, "fig23-00-1_贵州省地势起伏与骨干河流水系格局图.png")
    fig.savefig(out_file, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f" Saved: {out_file}")

# =============================================================================
# 图 2: 贵州省 9 个市州行政区划与黔中城市群空间战略格局图
# =============================================================================
def plot_fig2():
    print("Rendering fig23-00-2: Guizhou 9 cities & Qianzhong Urban Agglomeration...")
    fig, ax = plt.subplots(figsize=(10.5, 8.8), dpi=DPI)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.94, bottom=0.02)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    city_colors = {
        "520100": "#d4e6f1",  # 贵阳 (深蓝)
        "520200": "#fcf3cf",  # 六盘水 (暖黄)
        "520300": "#d5f5e3",  # 遵义 (柔绿)
        "520400": "#fadbd8",  # 安顺 (浅红)
        "520500": "#ebdef0",  # 毕节 (紫罗兰)
        "520600": "#d1f2eb",  # 铜仁 (青绿)
        "522300": "#fdebd0",  # 黔西南 (金黄)
        "522600": "#e8f8f5",  # 黔东南 (翠绿)
        "522700": "#eaeded",  # 黔南 (蓝灰)
    }

    for _, row in gz_all.iterrows():
        c_code = str(row.get("adcode", ""))
        c_fill = city_colors.get(c_code, "#f2f3f4")
        gpd.GeoSeries([row.geometry]).plot(ax=ax, facecolor=c_fill, edgecolor="#7f8c8d", lw=0.8, zorder=2)
        c_name = row.get("name", "")
        pt = row.geometry.representative_point()
        ax.text(pt.x, pt.y, c_name, fontsize=8.8, fontweight="bold", color="#1a252f", ha="center", va="center",
                path_effects=[pe.withStroke(linewidth=2.2, foreground="#ffffff")], zorder=6)

    gpd.GeoSeries([gz_union]).boundary.plot(ax=ax, color="#1b4f72", lw=1.8, zorder=4)

    sl = mapkit.SymbolLabels(ax, fig)
    sl.reserve([(0.0, 0.0, 0.32, 0.22), (0.70, 0.0, 1.0, 0.12), (0.84, 0.84, 1.0, 1.0)])

    for item in GUIZHOU_OVERVIEW["strategy_nodes"]:
        name, lon, lat, stype = item[0], item[1], item[2], item[3]
        x, y = to_alb(lon, lat)
        nm, nt = mapkit.split_note(name)
        if stype == "core":
            sl.add(x, y, nm, "core", note=nt, priority=0, marker="*", face="#c0392b", size=10.5,
                   kind_label="省域主核心极核 (贵阳-贵安)")
        elif stype == "subcore":
            sl.add(x, y, nm, "subcore", note=nt, priority=1, marker="D", face="#8e44ad", size=7.8,
                   kind_label="省域经济副中心 (遵义)")
        else:
            sl.add(x, y, nm, "node", note=nt, priority=2, marker="o", face="#1f618d", size=6.5,
                   kind_label="区域中心城市 / 战略支撑极")

    sym_type_h, sym_idx_h = sl.flush()

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    sb_x0 = ax_xlim[0] + span_x * 0.05
    sb_y0 = ax_ylim[0] + span_y * 0.05
    mapkit.add_scalebar(ax, sb_x0, sb_y0, length_km=50)
    add_compass(ax, 0.94, 0.92)

    leg = mapkit.stacked_legends(ax, [
        dict(handles=sym_type_h, title="空间战略发展梯队", ncol=2, fontsize=6.8, title_fontsize=7.6),
        dict(handles=sym_idx_h, title="战略节点编号对照", ncol=2, fontsize=6.8, title_fontsize=7.6),
    ], top=-0.010, gap=0.014)

    ax.set_title("贵州省9个市州行政区划与黔中城市群空间战略格局图", fontsize=12.5, fontweight="bold", pad=20, color=C_TEXT)
    ax.text(0.5, 1.008, "Administrative Divisions & Qianzhong Urban Agglomeration of Guizhou",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
    mapkit.footer_below_legend(ax, leg, "数据源：自然资源部标准地图服务 · 贵州省“十四五”新型城镇化规划 · 制作：《中国地理知识手册》", fontsize=6.5)

    out_file = os.path.join(OUT_DIR, "fig23-00-2_贵州省9个市州行政区划与黔中城市群空间战略格局图.png")
    fig.savefig(out_file, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f" Saved: {out_file}")

# =============================================================================
# 图 3: 贵州省综合立体交通网络与世界桥梁博物馆大通道格局图
# =============================================================================
def plot_fig3():
    print("Rendering fig23-00-3: Guizhou transport & World Bridge Museum corridors...")
    fig, ax = plt.subplots(figsize=(10.5, 8.8), dpi=DPI)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.94, bottom=0.02)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#fcfcfc")

    gz_all.plot(ax=ax, facecolor="#f4f6f7", edgecolor="#bdc3c7", lw=0.6, zorder=1)
    gpd.GeoSeries([gz_union]).boundary.plot(ax=ax, color="#2c3e50", lw=1.6, zorder=2)

    sl = mapkit.SymbolLabels(ax, fig)
    sl.reserve([(0.0, 0.0, 0.32, 0.22), (0.70, 0.0, 1.0, 0.12), (0.84, 0.84, 1.0, 1.0)])

    # 枢纽站点与世界高桥
    trans_nodes = [
        ("贵阳北站 (特大型高铁枢纽)", 106.64, 26.62, "rail"),
        ("遵义站 (渝贵铁路核心大站)", 106.96, 27.71, "rail"),
        ("安顺西站 (沪昆高铁枢纽)", 105.89, 26.23, "rail"),
        ("盘州站 (出入黔滇交通门户)", 104.45, 25.73, "rail"),
        ("凯里南站 (沪昆高铁侗乡枢纽)", 107.95, 26.55, "rail"),
        ("都匀东站 (贵广客专南向枢纽)", 107.60, 26.29, "rail"),
        ("毕节站 (成贵高铁骨干站)", 105.32, 27.27, "rail"),
        ("铜仁南站 (玉屏沪昆客专站)", 108.95, 27.20, "rail"),
        ("贵阳龙洞堡机场 (4E级枢纽空港)", 106.80, 26.54, "airport"),
        ("遵义新舟机场 (黔北综合机场)", 107.25, 27.81, "airport"),
        ("铜仁凤凰机场 (川黔湘交界空港)", 109.31, 27.88, "airport"),
        ("兴义万峰林机场 (山地商旅空港)", 104.96, 25.08, "airport"),
        ("北盘江第一桥 (565m 杭瑞高速世界最高桥)", 104.68, 26.11, "bridge"),
        ("鸭池河大桥 (434m 贵黔高速超级大跨径斜拉桥)", 106.12, 26.98, "bridge"),
        ("坝陵河大桥 (370m 沪昆高速钢桁悬索丰碑)", 105.63, 25.97, "bridge"),
        ("花江峡谷大桥 (625m 六安高速世界第一高桥)", 105.52, 25.75, "bridge"),
        ("平塘特大桥 (平罗高速世界第一大跨径槽梁三塔斜拉桥)", 107.12, 25.79, "bridge"),
        ("乌江余庆沙湾港 (千里乌江水运主枢纽)", 107.78, 27.30, "port"),
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
                   kind_label="民航客货运航空港 (干支结合)")
        elif ttype == "bridge":
            sl.add(x, y, nm, "bridge", note=nt, priority=0, marker="D", face="#b7950b", size=7.2,
                   kind_label="世界级高桥丰碑 (桥梁博物馆标志)")
        elif ttype == "port":
            sl.add(x, y, nm, "port", note=nt, priority=2, marker="o", face="#154360", size=6.0,
                   kind_label="内河水运核心集装箱港口")

    sym_type_h, sym_idx_h = sl.flush()

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    sb_x0 = ax_xlim[0] + span_x * 0.05
    sb_y0 = ax_ylim[0] + span_y * 0.05
    mapkit.add_scalebar(ax, sb_x0, sb_y0, length_km=50)
    add_compass(ax, 0.94, 0.92)

    leg = mapkit.stacked_legends(ax, [
        dict(handles=sym_type_h, title="综合交通设施分类", ncol=2, fontsize=6.8, title_fontsize=7.6),
        dict(handles=sym_idx_h, title="交通与桥梁编号对照", ncol=2, fontsize=6.8, title_fontsize=7.6),
    ], top=-0.010, gap=0.014)

    ax.set_title("贵州省综合立体交通网络与世界桥梁博物馆大通道格局图", fontsize=12.5, fontweight="bold", pad=20, color=C_TEXT)
    ax.text(0.5, 1.008, "Comprehensive Transport Network & World Bridge Museum of Guizhou",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
    mapkit.footer_below_legend(ax, leg, "数据源：交通运输部 · 中国国家铁路集团 · 制作：《中国地理知识手册》", fontsize=6.5)

    out_file = os.path.join(OUT_DIR, "fig23-00-3_贵州省综合立体交通网络与世界桥梁博物馆大通道格局图.png")
    fig.savefig(out_file, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f" Saved: {out_file}")

# =============================================================================
# 图 4: 贵州省特色优势产业集群与中国数谷算力高地空间分布图
# =============================================================================
def plot_fig4():
    print("Rendering fig23-00-4: Guizhou Advantage Industries & China Data Valley...")
    fig, ax = plt.subplots(figsize=(10.5, 8.8), dpi=DPI)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.94, bottom=0.02)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    gz_all.plot(ax=ax, facecolor="#fef9e7", edgecolor="#f1c40f", lw=0.6, zorder=1)
    gpd.GeoSeries([gz_union]).boundary.plot(ax=ax, color="#b7950b", lw=1.6, zorder=2)

    sl = mapkit.SymbolLabels(ax, fig)
    sl.reserve([(0.0, 0.0, 0.32, 0.22), (0.70, 0.0, 1.0, 0.12), (0.84, 0.84, 1.0, 1.0)])

    industry_nodes = [
        ("贵安新区华为云七星湖数据中心 (智算中心)", 106.43, 26.41, "data"),
        ("腾讯贵安七星数据中心 (山洞绿色数据机房)", 106.45, 26.39, "data"),
        ("苹果中国贵安超级数据中心", 106.47, 26.44, "data"),
        ("中国电信贵安国家超级算力中心", 106.46, 26.46, "data"),
        ("仁怀茅台酱香白酒核心酿造区 (世界名酒)", 106.42, 27.80, "liquor"),
        ("习水习酒生态酿造基地", 106.20, 28.30, "liquor"),
        ("金沙回沙酒酱酒产区", 106.25, 27.48, "liquor"),
        ("毕节织金新型煤化工新材料基地", 105.77, 26.68, "energy"),
        ("六盘水盘江煤电火电联营超级枢纽", 104.45, 25.95, "energy"),
        ("福泉开阳双龙现代磷系电池材料基地", 107.50, 26.70, "battery"),
        ("铜仁碧江大龙新型锰系储能材料基地", 109.12, 27.60, "battery"),
        ("安顺贵飞航空工业基地 (无人机与教练机)", 105.90, 26.20, "aviation"),
        ("遵义正安国际吉他智造产业园", 107.45, 28.53, "guitar"),
    ]

    for item in industry_nodes:
        name, lon, lat, itype = item[0], item[1], item[2], item[3]
        x, y = to_alb(lon, lat)
        nm, nt = mapkit.split_note(name)
        if itype == "data":
            sl.add(x, y, nm, "data", note=nt, priority=0, marker="s", face="#6c3483", size=7.2,
                   kind_label="东数西算全国超级算力数据中心")
        elif itype == "liquor":
            sl.add(x, y, nm, "liquor", note=nt, priority=0, marker="o", face="#c0392b", size=7.0,
                   kind_label="世界级酱香白酒原产地与核心酿造区")
        elif itype == "energy":
            sl.add(x, y, nm, "energy", note=nt, priority=1, marker="D", face="#154360", size=6.5,
                   kind_label="现代煤电与新型综合能源化工基地")
        elif itype == "battery":
            sl.add(x, y, nm, "battery", note=nt, priority=1, marker="D", face="#1e8449", size=6.8,
                   kind_label="新能源电池正负极材料与磷锰新材料")
        elif itype == "aviation":
            sl.add(x, y, nm, "aviation", note=nt, priority=2, marker="^", face="#2874a6", size=6.5,
                   kind_label="国家先进航空装备与高端智造")
        else:
            sl.add(x, y, nm, "guitar", note=nt, priority=2, marker="o", face="#d35400", size=6.2,
                   kind_label="特色轻工特色制造业出口高地")

    sym_type_h, sym_idx_h = sl.flush()

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    sb_x0 = ax_xlim[0] + span_x * 0.05
    sb_y0 = ax_ylim[0] + span_y * 0.05
    mapkit.add_scalebar(ax, sb_x0, sb_y0, length_km=50)
    add_compass(ax, 0.94, 0.92)

    leg = mapkit.stacked_legends(ax, [
        dict(handles=sym_type_h, title="特色优势产业门类", ncol=2, fontsize=6.8, title_fontsize=7.6),
        dict(handles=sym_idx_h, title="产业集群编号对照", ncol=2, fontsize=6.8, title_fontsize=7.6),
    ], top=-0.010, gap=0.014)

    ax.set_title("贵州省特色优势产业集群与中国数谷算力高地空间分布图", fontsize=12.5, fontweight="bold", pad=20, color=C_TEXT)
    ax.text(0.5, 1.008, "Advantage Industry Clusters & Digital Economy Hubs of Guizhou",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
    mapkit.footer_below_legend(ax, leg, "数据源：贵州省工业和信息化厅 · 国家大数据综合试验区统计 · 制作：《中国地理知识手册》", fontsize=6.5)

    out_file = os.path.join(OUT_DIR, "fig23-00-4_贵州省特色优势产业集群与中国数谷算力高地空间分布图.png")
    fig.savefig(out_file, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f" Saved: {out_file}")

# =============================================================================
# 图 5: 贵州省 1986-2024 年夜间灯光演化与开发强度对比图
# =============================================================================
def plot_fig5():
    print("Rendering fig23-00-5: Guizhou Nightlight evolution 1986-2024...")
    fig, (ax_nl, ax_gdp) = plt.subplots(1, 2, figsize=(11.0, 5.2), dpi=DPI)
    fig.subplots_adjust(left=0.07, right=0.96, top=0.88, bottom=0.14, wspace=0.22)
    fig.patch.set_facecolor("white")

    nl_file = os.path.join(DATA_DIR, "guizhou_nightlight_clean.csv")
    nl_df = pd.read_csv(nl_file)
    nl_agg = nl_df.groupby("year")["sum"].sum().reset_index().sort_values("year")

    years = nl_agg["year"].values
    sums = nl_agg["sum"].values

    ax_nl.plot(years, sums, color="#d35400", lw=2.2, marker="o", ms=4.0, label="全省夜光总辐射 (DN)")
    ax_nl.fill_between(years, sums, color="#fdebd0", alpha=0.55)

    max_sum = max(sums)
    annotations = [
        (1996, 25000, 1989, 70000, "1996: 老城区与三线厂矿点状暗弱微光"),
        (2005, 75000, 1998, 140000, "2005: 黔中高等级公路网破土拉开"),
        (2015, 230000, 2008, 320000, "2015: 县县通高速/中国数谷落户贵安"),
        (2023, 490000, 2017, 560000, "2023: 东数西算枢纽/世界桥梁与文旅狂飙"),
    ]

    for y_pt, val_est, text_x, text_y, note in annotations:
        sub_pt = nl_agg[nl_agg["year"] == y_pt]
        if not sub_pt.empty:
            real_val = float(sub_pt["sum"].values[0])
            ax_nl.annotate(note, xy=(y_pt, real_val), xytext=(text_x, text_y),
                           arrowprops=dict(arrowstyle="->", color="#c0392b", lw=0.9),
                           fontsize=7.0, fontweight="bold", color="#78281f",
                           bbox=dict(boxstyle="round,pad=0.25", facecolor="#ffffff", edgecolor="#e74c3c", alpha=0.92))

    ax_nl.set_title("贵州省 1986—2024 年夜间灯光总辐射时序狂飙跃升", fontsize=10.5, fontweight="bold", color=C_TEXT)
    ax_nl.set_ylabel("夜间灯光辐射总积分 (DN)", fontsize=7.8, color="#2c3e50")
    ax_nl.set_xlabel("年份 Year", fontsize=7.8, color="#2c3e50")
    ax_nl.grid(True, linestyle="--", alpha=0.45)
    ax_nl.tick_params(labelsize=7.0)

    # 9 市州 2024 年 GDP 与城镇化率对比图
    cities = []
    gdps = []
    for code, cfg in GUIZHOU_CITY_CONFIGS.items():
        cities.append(cfg["name"].replace("市", "").replace("布依族苗族自治州", "").replace("苗族侗族自治州", ""))
        gdps.append(cfg["gdp_2024"])

    bars = ax_gdp.bar(cities, gdps, color="#1b4f72", edgecolor="#0b2545", alpha=0.85, width=0.6)
    for bar in bars:
        h = bar.get_height()
        ax_gdp.text(bar.get_x() + bar.get_width() / 2.0, h + 80.0, f"{h:g}",
                    ha="center", va="bottom", fontsize=6.8, fontweight="bold", color="#0b2545")

    ax_gdp.set_title("贵州省 9 个市州 2024 年经济总量 (GDP, 亿元) 空间梯度格局", fontsize=10.5, fontweight="bold", color=C_TEXT)
    ax_gdp.set_ylabel("地区生产总值 (GDP, 亿元)", fontsize=7.8, color="#2c3e50")
    ax_gdp.set_xlabel("市州名称 City / Prefecture", fontsize=7.8, color="#2c3e50")
    ax_gdp.set_ylim(0, max(gdps) * 1.15)
    ax_gdp.grid(True, linestyle="--", alpha=0.45, axis="y")
    ax_gdp.tick_params(labelsize=7.0)

    fig.tight_layout(pad=2.5)
    fig.text(0.5, 0.01, "数据来源：夜间灯光遥感时序数据集 (1986-2024) · 贵州省统计局国民经济和社会发展统计公报 · 制作：《中国地理知识手册》",
             ha="center", va="bottom", fontsize=6.5, color="#7f8c8d")

    out_file = os.path.join(OUT_DIR, "fig23-00-5_贵州省1986-2024年夜间灯光演化与开发强度对比图.png")
    fig.savefig(out_file, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f" Saved: {out_file}")

def main():
    plot_fig1()
    plot_fig2()
    plot_fig3()
    plot_fig4()
    plot_fig5()
    print("\n=== GUIZHOU OVERVIEW FIGURES GENERATION COMPLETE ===")

if __name__ == "__main__":
    main()
