# -*- coding: utf-8 -*-
"""云南省省级地理统揽专题地图生成引擎（24-00）
包含 5 幅全省出版级权威地图与分析图表（精细调优排版、严格杜绝压盖）：
1. fig24-00-1_云南省地势起伏与骨干河流水系格局图.png
2. fig24-00-2_云南省16个市州行政区划与滇中城市群空间战略格局图.png
3. fig24-00-3_云南省综合立体交通网络与辐射南亚东南亚大通道格局图.png
4. fig24-00-4_云南省特色优势产业集群与绿色能源强省空间分布图.png
5. fig24-00-5_云南省1986-2024年夜间灯光演化与开发强度对比图.png
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
from yunnan_configs import YUNNAN_OVERVIEW
from yunnan_city_configs import YUNNAN_CITY_CONFIGS

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

print("Loading Yunnan provincial boundaries and DEM...")
DATA_DIR = os.path.join(BASE_DIR, "data")
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")

yn_all = gpd.read_file(os.path.join(DATAV_DIR, "530000_full.json")).to_crs(ALBERS)
yn_all["geometry"] = yn_all.geometry.buffer(0)
yn_union = yn_all.union_all()

b = yn_all.total_bounds
span_x = b[2] - b[0]
span_y = b[3] - b[1]
pad_x = span_x * 0.04
pad_y = span_y * 0.04
ax_xlim = (b[0] - pad_x, b[2] + pad_x)
ax_ylim = (b[1] - pad_y, b[3] + pad_y)

dem_file = os.path.join(DATA_DIR, "dem", "province", "530000_z9.npz")
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

terrain_cmap = LinearSegmentedColormap.from_list("yn_terrain", [
    (0.0, "#1b4d3e"),   # 红河谷/元江/西双版纳热区极低谷 (76m ~ 500m) 浓绿
    (0.12, "#2e7d32"),  # 滇南滇西南中低山 (500m ~ 1200m) 翠绿
    (0.28, "#81c784"),  # 滇中高原盆地平坝 (1200m ~ 1800m) 柔绿
    (0.42, "#d4e157"),  # 滇中滇东山原草甸 (1800m ~ 2300m) 黄绿
    (0.58, "#ffd54f"),  # 滇西北高中山 (2300m ~ 3200m) 暖黄
    (0.72, "#ff8a65"),  # 滇西北亚高山草甸/峡谷上段 (3200m ~ 4200m) 橙红
    (0.85, "#8d6e63"),  # 高山流石滩与冻融角峰 (4200m ~ 5200m) 灰褐
    (1.0, "#ffffff")    # 梅里雪山/玉龙雪山现代冰川与极顶 (5200m ~ 6740m) 纯白
])

# =============================================================================
# 图 1: 云南省地势起伏与骨干河流水系格局图
# =============================================================================
def plot_fig1():
    print("Rendering fig24-00-1: Yunnan topography & river network...")
    fig, ax = plt.subplots(figsize=(10.5, 9.2), dpi=DPI)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.94, bottom=0.02)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    norm = Normalize(vmin=76.4, vmax=6740.0)
    rgb_c = terrain_cmap(norm(dem_elev))[:, :, :3]
    rgb_s = np.clip(rgb_c * (hillshade[:, :, np.newaxis] * 0.72 + 0.28), 0.0, 1.0)

    im = ax.imshow(rgb_s, extent=dem_extent, origin="upper", zorder=1)
    clip_patch = get_mpl_clip_patch(yn_union)
    ax.add_patch(clip_patch)
    im.set_clip_path(clip_patch)

    yn_all.boundary.plot(ax=ax, color="#7f8c8d", lw=0.6, ls="--", zorder=3)
    gpd.GeoSeries([yn_union]).boundary.plot(ax=ax, color="#1b4f72", lw=1.6, zorder=4)

    # 绘制骨干水系
    for rname, rcoords, rcolor, rwidth in YUNNAN_OVERVIEW["major_rivers"]:
        pts = [to_alb(c[0], c[1]) for c in rcoords]
        xs, ys = zip(*pts)
        ax.plot(xs, ys, color=rcolor, lw=rwidth, alpha=0.9, zorder=5)
        mid_idx = len(xs) // 2
        ax.text(xs[mid_idx], ys[mid_idx], rname.split()[0], fontsize=7.2, color="#0b5345",
                fontweight="bold", ha="center", va="center",
                path_effects=[pe.withStroke(linewidth=2.0, foreground="#ffffff")], zorder=6)

    sl = mapkit.SymbolLabels(ax, fig)
    sl.reserve([(0.0, 0.0, 0.32, 0.24), (0.70, 0.0, 1.0, 0.12), (0.84, 0.84, 1.0, 1.0)])

    for item in YUNNAN_OVERVIEW["landmarks_macro"]:
        name, lon, lat, ltype = item[0], item[1], item[2], item[3]
        x, y = to_alb(lon, lat)
        nm, nt = mapkit.split_note(name)
        if ltype == "peak_max":
            sl.add(x, y, nm, "peak_max", note=nt, priority=0, marker="^", face="#78281f", size=9.5,
                   kind_label="省域最高极顶 (云南屋脊·卡瓦格博)")
        elif ltype == "peak":
            sl.add(x, y, nm, "peak", note=nt, priority=1, marker="^", face="#935116", size=7.8,
                   kind_label="骨干名山绝顶 / 现代海洋性冰川")
        elif ltype == "lake":
            sl.add(x, y, nm, "lake", note=nt, priority=1, marker="o", face="#1b4f72", size=7.5,
                   kind_label="高原断陷湖泊 / 琉璃明珠")
        elif ltype == "heritage":
            sl.add(x, y, nm, "heritage", note=nt, priority=2, marker="D", face="#b7950b", size=7.0,
                   kind_label="世界文化与自然双重遗产奇迹")
        elif ltype == "forest":
            sl.add(x, y, nm, "forest", note=nt, priority=2, marker="s", face="#1e8449", size=7.0,
                   kind_label="热带雨林自然生态与亚洲象栖息地")
        else:
            sl.add(x, y, nm, "gorge", note=nt, priority=2, marker="o", face="#27ae60", size=6.8,
                   kind_label="世界最深大峡谷与地貌奇观")

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

    ax.set_title("云南省地势起伏与骨干河流水系格局图", fontsize=12.5, fontweight="bold", pad=20, color=C_TEXT)
    ax.text(0.5, 1.008, "Topography, Landforms & Major River Networks of Yunnan Province",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
    mapkit.footer_below_legend(ax, leg, "数据源：AWS Terrain GLO-30 DEM · 水利部水文水资源公报 · 制作：《中国地理知识手册》", fontsize=6.5)

    out_file = os.path.join(OUT_DIR, "fig24-00-1_云南省地势起伏与骨干河流水系格局图.png")
    fig.savefig(out_file, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f" Saved: {out_file}")

# =============================================================================
# 图 2: 云南省 16 个市州行政区划与滇中城市群空间战略格局图
# =============================================================================
def plot_fig2():
    print("Rendering fig24-00-2: Yunnan 16 cities & Dianzhong Urban Agglomeration...")
    fig, ax = plt.subplots(figsize=(10.5, 9.2), dpi=DPI)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.94, bottom=0.02)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    city_colors = {
        "530100": "#d4e6f1",  # 昆明 (深蓝)
        "530300": "#d5f5e3",  # 曲靖 (柔绿)
        "530400": "#fcf3cf",  # 玉溪 (暖黄)
        "530500": "#fadbd8",  # 保山 (浅红)
        "530600": "#ebdef0",  # 昭通 (紫罗兰)
        "530700": "#d1f2eb",  # 丽江 (青绿)
        "530800": "#e8f8f5",  # 普洱 (浅翠)
        "530900": "#fdebd0",  # 临沧 (金黄)
        "532300": "#eaeded",  # 楚雄 (蓝灰)
        "532500": "#d6eaf8",  # 红河 (天蓝)
        "532600": "#edbb99",  # 文山 (橙黄)
        "532800": "#a9dfbf",  # 西双版纳 (热带绿)
        "532900": "#fef9e7",  # 大理 (象牙黄)
        "533100": "#e8daef",  # 德宏 (淡紫)
        "533300": "#d0ece7",  # 怒江 (峡谷碧)
        "533400": "#f5cba7",  # 迪庆 (雪域暖)
    }

    for _, row in yn_all.iterrows():
        c_code = str(row.get("adcode", ""))
        c_fill = city_colors.get(c_code, "#f2f3f4")
        gpd.GeoSeries([row.geometry]).plot(ax=ax, facecolor=c_fill, edgecolor="#7f8c8d", lw=0.8, zorder=2)
        c_name = row.get("name", "")
        # 简化自治州名字避免压盖
        c_disp = c_name.replace("彝族自治州", "").replace("哈尼族彝族自治州", "").replace("壮族苗族自治州", "").replace("傣族自治州", "").replace("白族自治州", "").replace("傣族景颇族自治州", "").replace("傈僳族自治州", "").replace("藏族自治州", "")
        pt = row.geometry.representative_point()
        ax.text(pt.x, pt.y, c_disp, fontsize=8.2, fontweight="bold", color="#1a252f", ha="center", va="center",
                path_effects=[pe.withStroke(linewidth=2.2, foreground="#ffffff")], zorder=6)

    gpd.GeoSeries([yn_union]).boundary.plot(ax=ax, color="#1b4f72", lw=1.8, zorder=4)

    sl = mapkit.SymbolLabels(ax, fig)
    sl.reserve([(0.0, 0.0, 0.32, 0.22), (0.70, 0.0, 1.0, 0.12), (0.84, 0.84, 1.0, 1.0)])

    for item in YUNNAN_OVERVIEW["strategy_nodes"]:
        name, lon, lat, stype = item[0], item[1], item[2], item[3]
        x, y = to_alb(lon, lat)
        nm, nt = mapkit.split_note(name)
        if stype == "core":
            sl.add(x, y, nm, "core", note=nt, priority=0, marker="*", face="#c0392b", size=10.5,
                   kind_label="省域主核心极核 (昆明)")
        elif stype == "subcore":
            sl.add(x, y, nm, "subcore", note=nt, priority=1, marker="D", face="#8e44ad", size=7.8,
                   kind_label="省域经济副中心 (曲靖/红河/大理)")
        else:
            sl.add(x, y, nm, "node", note=nt, priority=2, marker="o", face="#1f618d", size=6.5,
                   kind_label="区域战略枢纽城市 / 沿边重点口岸极")

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

    ax.set_title("云南省16个市州行政区划与滇中城市群空间战略格局图", fontsize=12.5, fontweight="bold", pad=20, color=C_TEXT)
    ax.text(0.5, 1.008, "Administrative Divisions & Spatial Strategy of Yunnan Province",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
    mapkit.footer_below_legend(ax, leg, "数据源：自然资源部标准地图服务 · 云南省“十四五”区域协调发展规划 · 制作：《中国地理知识手册》", fontsize=6.5)

    out_file = os.path.join(OUT_DIR, "fig24-00-2_云南省16个市州行政区划与滇中城市群空间战略格局图.png")
    fig.savefig(out_file, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f" Saved: {out_file}")

# =============================================================================
# 图 3: 云南省综合立体交通网络与辐射南亚东南亚大通道格局图
# =============================================================================
def plot_fig3():
    print("Rendering fig24-00-3: Yunnan transport & South/Southeast Asia corridors...")
    fig, ax = plt.subplots(figsize=(10.5, 9.2), dpi=DPI)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.94, bottom=0.02)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#fcfcfc")

    yn_all.plot(ax=ax, facecolor="#f4f6f7", edgecolor="#bdc3c7", lw=0.6, zorder=1)
    gpd.GeoSeries([yn_union]).boundary.plot(ax=ax, color="#2c3e50", lw=1.6, zorder=2)

    sl = mapkit.SymbolLabels(ax, fig)
    sl.reserve([(0.0, 0.0, 0.32, 0.22), (0.70, 0.0, 1.0, 0.12), (0.84, 0.84, 1.0, 1.0)])

    # 交通枢纽节点
    trans_nodes = [
        ("昆明南站 (中老铁路国际始发枢纽)", 102.80, 24.87, "rail"),
        ("昆明长水国际机场 (4F级门户枢纽机场)", 102.93, 25.10, "airport"),
        ("曲靖北站 (沪昆高铁入滇门户大站)", 103.80, 25.56, "rail"),
        ("大理站 (滇西最大客货运综合高铁站)", 100.26, 25.59, "rail"),
        ("丽江站 (丽香铁路与大丽铁路枢纽)", 100.24, 26.80, "rail"),
        ("香格里拉站 (丽香铁路高原雪山终点站)", 99.68, 27.79, "rail"),
        ("保山站 (大瑞铁路大保段客货终点)", 99.18, 25.10, "rail"),
        ("临沧站 (大临铁路客货综合枢纽)", 100.10, 23.91, "rail"),
        ("西双版纳站 (中老铁路旅游黄金大站)", 100.76, 21.97, "rail"),
        ("磨憨站 (中老铁路中老跨境第一国门站)", 101.68, 21.19, "rail"),
        ("红河站 (弥蒙高铁与泛亚东线枢纽)", 103.35, 23.38, "rail"),
        ("普者黑站 (南昆客专滇东南重要站点)", 104.15, 24.08, "rail"),
        ("瑞丽口岸姐告国门 (全国最大对缅人员物资陆港)", 97.88, 23.98, "port"),
        ("河口口岸 (中越跨境一类国家级大口岸)", 103.95, 22.51, "port"),
        ("水富港 (万里长江第一港/云南直通上海航运港)", 104.42, 28.64, "port"),
        ("景洪港 (澜沧江-湄公河一类国际水运口岸)", 100.80, 22.02, "port"),
        ("龙江特大桥 (亚洲山区最大跨径悬索桥)", 98.66, 24.82, "bridge"),
        ("元江特大桥 (中老铁路世界最高铁路桥墩)", 101.98, 23.58, "bridge"),
    ]

    for item in trans_nodes:
        name, lon, lat, ttype = item[0], item[1], item[2], item[3]
        x, y = to_alb(lon, lat)
        nm, nt = mapkit.split_note(name)
        if ttype == "rail":
            sl.add(x, y, nm, "rail", note=nt, priority=0, marker="s", face="#1b4f72", size=6.5,
                   kind_label="高速铁路客货综合枢纽 / 国门第一站")
        elif ttype == "airport":
            sl.add(x, y, nm, "airport", note=nt, priority=1, marker="^", face="#196f3d", size=6.8,
                   kind_label="民航门户与支线干线航空港")
        elif ttype == "bridge":
            sl.add(x, y, nm, "bridge", note=nt, priority=0, marker="D", face="#b7950b", size=7.2,
                   kind_label="世界级高桥与跨江工程丰碑")
        elif ttype == "port":
            sl.add(x, y, nm, "port", note=nt, priority=2, marker="o", face="#154360", size=6.0,
                   kind_label="国际航运口岸 / 沿边陆路国门口岸")

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

    ax.set_title("云南省综合立体交通网络与辐射南亚东南亚大通道格局图", fontsize=12.5, fontweight="bold", pad=20, color=C_TEXT)
    ax.text(0.5, 1.008, "Comprehensive Transport Network & International Corridors of Yunnan",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
    mapkit.footer_below_legend(ax, leg, "数据源：中国国家铁路集团 · 云南省交通运输厅 · 制作：《中国地理知识手册》", fontsize=6.5)

    out_file = os.path.join(OUT_DIR, "fig24-00-3_云南省综合立体交通网络与辐射南亚东南亚大通道格局图.png")
    fig.savefig(out_file, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f" Saved: {out_file}")

# =============================================================================
# 图 4: 云南省特色优势产业集群与绿色能源强省空间分布图
# =============================================================================
def plot_fig4():
    print("Rendering fig24-00-4: Yunnan Advantage Industries & Green Energy clusters...")
    fig, ax = plt.subplots(figsize=(10.5, 9.2), dpi=DPI)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.94, bottom=0.02)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    yn_all.plot(ax=ax, facecolor="#fef9e7", edgecolor="#f1c40f", lw=0.6, zorder=1)
    gpd.GeoSeries([yn_union]).boundary.plot(ax=ax, color="#b7950b", lw=1.6, zorder=2)

    sl = mapkit.SymbolLabels(ax, fig)
    sl.reserve([(0.0, 0.0, 0.32, 0.22), (0.70, 0.0, 1.0, 0.12), (0.84, 0.84, 1.0, 1.0)])

    industry_nodes = [
        ("白鹤滩水电站 (1600万千瓦·世界第二大电站)", 102.90, 27.12, "energy"),
        ("溪洛渡水电站 (1260万千瓦·世界第四大电站)", 103.65, 28.26, "energy"),
        ("乌东德水电站 (1020万千瓦·世界第七大电站)", 102.62, 26.33, "energy"),
        ("糯扎渡水电站 (585万千瓦·澜沧江最大水电站)", 100.52, 22.64, "energy"),
        ("小湾水电站 (420万千瓦·世界第二高拱坝292m)", 100.09, 24.70, "energy"),
        ("文山绿色铝谷核心产业园 (砚山百万吨电解铝)", 104.36, 23.58, "aluminum"),
        ("曲靖南海子绿色硅光伏基地 (打造世界光伏之都)", 103.84, 25.64, "solar"),
        ("保山工贸园区绿色单晶硅产业基地", 99.20, 25.06, "solar"),
        ("楚雄高新区绿色光伏切片与彝医药基地", 101.52, 25.07, "solar"),
        ("昆明呈贡斗南国际花卉拍卖交易中心", 102.78, 24.91, "agri"),
        ("普洱景迈山古茶林文化景观 (世界文化遗产)", 100.02, 22.20, "agri"),
        ("临沧凤庆滇红茶核心工业产区", 99.91, 24.59, "agri"),
        ("红河个旧云锡集团 (全球最大锡金属基地)", 103.15, 23.33, "metal"),
        ("昆明国家高新区生物医药基地 (云南白药集团)", 102.66, 25.05, "pharma"),
    ]

    for item in industry_nodes:
        name, lon, lat, itype = item[0], item[1], item[2], item[3]
        x, y = to_alb(lon, lat)
        nm, nt = mapkit.split_note(name)
        if itype == "energy":
            sl.add(x, y, nm, "energy", note=nt, priority=0, marker="D", face="#154360", size=7.2,
                   kind_label="世界级巨型梯级水电基地 (大国重器)")
        elif itype == "solar":
            sl.add(x, y, nm, "solar", note=nt, priority=0, marker="s", face="#b7950b", size=7.0,
                   kind_label="绿色硅光伏产业链核心制造基地")
        elif itype == "aluminum":
            sl.add(x, y, nm, "aluminum", note=nt, priority=1, marker="s", face="#117864", size=7.0,
                   kind_label="中国绿色铝谷·水电铝材一体化基地")
        elif itype == "metal":
            sl.add(x, y, nm, "metal", note=nt, priority=1, marker="D", face="#78281f", size=6.8,
                   kind_label="世界有色金属与稀贵战略矿产基地")
        elif itype == "agri":
            sl.add(x, y, nm, "agri", note=nt, priority=2, marker="o", face="#1e8449", size=6.8,
                   kind_label="高原特色现代农业 (云茶/云花/云咖)")
        else:
            sl.add(x, y, nm, "pharma", note=nt, priority=2, marker="o", face="#6c3483", size=6.5,
                   kind_label="现代生物医药与天然植物药高地")

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

    ax.set_title("云南省特色优势产业集群与绿色能源强省空间分布图", fontsize=12.5, fontweight="bold", pad=20, color=C_TEXT)
    ax.text(0.5, 1.008, "Advantage Industry Clusters & Green Energy Bases of Yunnan Province",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
    mapkit.footer_below_legend(ax, leg, "数据源：云南省发展和改革委员会 · 云南省工业和信息化厅 · 制作：《中国地理知识手册》", fontsize=6.5)

    out_file = os.path.join(OUT_DIR, "fig24-00-4_云南省特色优势产业集群与绿色能源强省空间分布图.png")
    fig.savefig(out_file, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f" Saved: {out_file}")

# =============================================================================
# 图 5: 云南省 1986-2024 年夜间灯光演化与开发强度对比图
# =============================================================================
def plot_fig5():
    print("Rendering fig24-00-5: Yunnan Nightlight evolution 1986-2024...")
    fig, (ax_nl, ax_gdp) = plt.subplots(1, 2, figsize=(11.5, 5.4), dpi=DPI)
    fig.subplots_adjust(left=0.07, right=0.96, top=0.88, bottom=0.14, wspace=0.22)
    fig.patch.set_facecolor("white")

    nl_file = os.path.join(DATA_DIR, "yunnan_nightlight_clean.csv")
    nl_df = pd.read_csv(nl_file)
    nl_agg = nl_df.groupby("year")["sum"].sum().reset_index().sort_values("year")

    years = nl_agg["year"].values
    sums = nl_agg["sum"].values

    ax_nl.plot(years, sums, color="#d35400", lw=2.2, marker="o", ms=4.0, label="全省夜光总辐射 (DN)")
    ax_nl.fill_between(years, sums, color="#fdebd0", alpha=0.55)

    annotations = [
        (1996, 45000, 1989, 120000, "1996: 滇中盆地与主要城市微弱星火"),
        (2005, 130000, 1998, 230000, "2005: 泛亚铁路构想与高速公路网络拉开"),
        (2015, 380000, 2008, 520000, "2015: 绿色能源基地崛起/辐射中心战略提速"),
        (2023, 850000, 2016, 960000, "2023: 中老铁路通车/绿色铝硅全产业链爆发"),
    ]

    for y_pt, val_est, text_x, text_y, note in annotations:
        sub_pt = nl_agg[nl_agg["year"] == y_pt]
        if not sub_pt.empty:
            real_val = float(sub_pt["sum"].values[0])
            ax_nl.annotate(note, xy=(y_pt, real_val), xytext=(text_x, text_y),
                           arrowprops=dict(arrowstyle="->", color="#c0392b", lw=0.9),
                           fontsize=7.0, fontweight="bold", color="#78281f",
                           bbox=dict(boxstyle="round,pad=0.25", facecolor="#ffffff", edgecolor="#e74c3c", alpha=0.92))

    ax_nl.set_title("云南省 1986—2024 年夜间灯光总辐射时序跃迁演进", fontsize=10.5, fontweight="bold", color=C_TEXT)
    ax_nl.set_ylabel("夜间灯光辐射总积分 (DN)", fontsize=7.8, color="#2c3e50")
    ax_nl.set_xlabel("年份 Year", fontsize=7.8, color="#2c3e50")
    ax_nl.grid(True, linestyle="--", alpha=0.45)
    ax_nl.tick_params(labelsize=7.0)

    # 16 市州 2024 年 GDP 对比图
    cities = []
    gdps = []
    for code, cfg in YUNNAN_CITY_CONFIGS.items():
        c_short = cfg["name"].replace("市", "").replace("彝族自治州", "").replace("哈尼族彝族自治州", "").replace("壮族苗族自治州", "").replace("傣族自治州", "").replace("白族自治州", "").replace("傣族景颇族自治州", "").replace("傈僳族自治州", "").replace("藏族自治州", "")
        cities.append(c_short)
        gdps.append(cfg["gdp_2024"])

    bars = ax_gdp.bar(cities, gdps, color="#1b4f72", edgecolor="#0b2545", alpha=0.85, width=0.6)
    for bar in bars:
        h = bar.get_height()
        ax_gdp.text(bar.get_x() + bar.get_width() / 2.0, h + 110.0, f"{h:g}",
                    ha="center", va="bottom", fontsize=6.2, fontweight="bold", color="#0b2545")

    ax_gdp.set_title("云南省 16 个市州 2024 年经济总量 (GDP, 亿元) 空间梯度格局", fontsize=10.5, fontweight="bold", color=C_TEXT)
    ax_gdp.set_ylabel("地区生产总值 (GDP, 亿元)", fontsize=7.8, color="#2c3e50")
    ax_gdp.set_xlabel("市州名称 City / Prefecture", fontsize=7.8, color="#2c3e50")
    ax_gdp.set_ylim(0, max(gdps) * 1.15)
    ax_gdp.grid(True, linestyle="--", alpha=0.45, axis="y")
    ax_gdp.tick_params(labelsize=6.8, rotation=35)

    fig.tight_layout(pad=2.5)
    fig.text(0.5, 0.01, "数据来源：夜间灯光遥感时序数据集 (1986-2024) · 云南省统计局国民经济和社会发展统计公报 · 制作：《中国地理知识手册》",
             ha="center", va="bottom", fontsize=6.5, color="#7f8c8d")

    out_file = os.path.join(OUT_DIR, "fig24-00-5_云南省1986-2024年夜间灯光演化与开发强度对比图.png")
    fig.savefig(out_file, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f" Saved: {out_file}")

def main():
    plot_fig1()
    plot_fig2()
    plot_fig3()
    plot_fig4()
    plot_fig5()
    print("\n=== YUNNAN OVERVIEW FIGURES GENERATION COMPLETE ===")

if __name__ == "__main__":
    main()
