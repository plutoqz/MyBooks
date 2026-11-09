# -*- coding: utf-8 -*-
"""北京市地理统揽专题地图生成引擎（01-00）
包含 5 幅全市域权威地图与分析图表（精细调优排版、真实要素加载、杜绝压盖）：
1. fig01-00-1_北京市地形地貌与燕山太行合抱图.png （“北京湾”山峦合抱地势大格局，太行西山与军都燕山弧，千米高山与平原）
2. fig01-00-2_北京市五大水系格局图.png （海河流域蓟运河、潮白河、北运河、永定河、大清河全流域真实水网与密云/官厅/怀柔大水库）
3. fig01-00-3_北京市十六区空间格局与功能分区图.png （首都功能核心区、中心城区、平原新城、生态涵养区四大功能区规划空间）
4. fig01-00-4_北京市综合交通骨架与枢纽网络图.png （环路放射高速路网、首都+大兴双超级国际枢纽机场、各大高铁特等枢纽）
5. fig01-00-5_北京市经济总量与空间夜光演进图.png （1986—2013全市夜间灯光辐射总量跃迁与2000—2024年GDP跨越4.75万亿元）
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
from matplotlib.path import Path
from matplotlib.lines import Line2D
from matplotlib.colors import LinearSegmentedColormap, Normalize
from pyproj import Transformer

sys.path.insert(0, r"D:\code\Ideas\MyBooks\中国地理知识手册\scripts")
from style import ALBERS, C_TEXT, DATA, DPI, FIGURES, setup
import mapkit
from prov_pipeline import prov_dem

setup()
OUT_DIR = FIGURES
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
    gy, gx = np.gradient(dem, res)
    slope = np.arctan(np.sqrt(gx * gx + gy * gy))
    aspect = np.arctan2(-gx, gy)
    shaded = np.sin(alt_rad) * np.cos(slope) + np.cos(alt_rad) * np.sin(slope) * np.cos(az_rad - aspect)
    return np.clip(shaded, 0.0, 1.0)

def add_scalebar(ax, x0, y0, length_km=30):
    """统一走 mapkit 版本，按像素宽度自适应是否画中点刻度。"""
    import mapkit
    mapkit.add_scalebar(ax, x0, y0, length_km=length_km)

def add_compass(ax, x=0.94, y=0.90):
    ax.annotate("N", xy=(x, y), xytext=(x, y - 0.065), transform=ax.transAxes,
                arrowprops=dict(facecolor="#2c3e50", edgecolor="#2c3e50", width=2.2, headwidth=7.0, headlength=8.5),
                ha="center", va="center", fontsize=11.5, fontweight="bold", color="#2c3e50", zorder=30)

print("Loading Beijing municipal spatial data...")
DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
bj_districts = gpd.read_file(os.path.join(DATA_DIR, "boundaries", "datav", "110000_full.json")).to_crs(ALBERS)
bj_union = bj_districts.union_all()


def load_bj_roads():
    """北京市域 OSM 路网（motorway / trunk / primary / secondary 四级）。

    原「综合交通骨架图」只在图上写了几行高速通道名字，一条路都没画，
    但图例却标注了「环路体系与放射状国家高速公路网」——图例与图面不符。
    这里真实读取 OSM 路网，按等级分四层绘制。
    """
    roads_fp = os.path.join(DATA_DIR, "transport", "beijing", "Beijing-shp",
                            "shape", "roads.shp")
    if not os.path.exists(roads_fp):
        return None
    b = bj_districts.to_crs("EPSG:4326").total_bounds
    pad = 0.12
    bbox = (b[0] - pad, b[1] - pad, b[2] + pad, b[3] + pad)
    roads = gpd.read_file(roads_fp, bbox=bbox)
    if len(roads) == 0:
        return None
    roads = mapkit.clean_lines(roads.to_crs(ALBERS))
    return mapkit.classify_roads(roads)


BJ_ROADS = None
try:
    BJ_ROADS = load_bj_roads()
except Exception as _e:      # 数据缺失时退化为纯示意，不让整批图失败
    print("北京路网加载失败：", _e)
bb = bj_districts.total_bounds

# 中心与画幅计算
cx = (bb[0] + bb[2]) / 2.0
cy = (bb[1] + bb[3]) / 2.0
span_x = bb[2] - bb[0]
span_y = bb[3] - bb[1]
max_span = max(span_x, span_y)
# 视口紧贴市域 bbox，不再套正方形方框：北京东西宽、南北窄，方框视口会让
# 上下各空出两成画布；图例外移后这个浪费更明显。
pad_x = span_x * 0.045
pad_y = span_y * 0.055
ax_xlim = (bb[0] - pad_x, bb[2] + pad_x)
ax_ylim = (bb[1] - pad_y, bb[3] + pad_y)
# 画布随宽高比自适应
_ar = (ax_ylim[1] - ax_ylim[0]) / max(ax_xlim[1] - ax_xlim[0], 1e-9)
FIGSIZE = (10.0, max(5.6, min(10.4, 10.0 * _ar)))
sb_x0 = ax_xlim[0] + (ax_xlim[1] - ax_xlim[0]) * 0.60
sb_y0 = ax_ylim[0] + (ax_ylim[1] - ax_ylim[0]) * 0.05

dem_bj, dem_minx, dem_maxy, dem_res = prov_dem("110000", zoom=9, res=300.0)
osm_dir = os.path.join(DATA_DIR, "transport", "beijing", "Beijing-shp", "shape")
nl_clean_df = pd.read_csv(os.path.join(DATA_DIR, "beijing_nightlight_clean.csv"))

# -------------------------------------------------------------------------
# 图 1：北京市地形地貌与燕山太行合抱图（北京湾）
# -------------------------------------------------------------------------
def make_overview_map1():
    print("Generating Overview Map 1 (Terrain & Beijing Bay)...")
    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    hs = calc_hillshade(dem_bj, dem_res)
    colors = [
        (0.00, "#73a580"),
        (0.08, "#8bbd8b"),
        (0.18, "#c9bb86"),
        (0.35, "#c49257"),
        (0.65, "#9c6039"),
        (1.00, "#5a2b16")
    ]
    cmap = LinearSegmentedColormap.from_list("bj_dem_cmap", colors, N=256)
    norm = Normalize(vmin=10.0, vmax=2303.0)

    rgba = cmap(norm(dem_bj))
    h_weight = 0.52
    hs_c = np.clip(hs, 0, 1)
    for i in range(3):
        rgba[..., i] = rgba[..., i] * (1.0 - h_weight + h_weight * hs_c)

    sub_extent = (dem_minx, dem_minx + dem_bj.shape[1] * dem_res,
                  dem_maxy - dem_bj.shape[0] * dem_res, dem_maxy)

    patch = get_mpl_clip_patch(bj_union)
    ax.add_patch(patch)
    im = ax.imshow(rgba, extent=sub_extent, origin="upper", interpolation="bilinear", zorder=2)
    im.set_clip_path(patch)

    # 绘制区界与市界
    bj_districts.boundary.plot(ax=ax, color="#566573", lw=0.7, linestyle=":", zorder=5)
    gpd.GeoSeries([bj_union], crs=ALBERS).boundary.plot(ax=ax, color="#1c2833", lw=2.2, zorder=6)

    # 山脉走向注记（太行山脉往西南微调，与东灵山引线彻底分开）
    mountain_arcs = [
        ("太行山脉 (西山段)", 115.75, 39.80, 50, 11.0, "#4a235a"),
        ("燕山山脉 (军都山段)", 116.35, 40.65, 20, 11.0, "#4a235a"),
        ("【北京湾】冲积平原核心腹地", 116.42, 39.88, 0, 11.0, "#196f3d")
    ]
    for mname, mlon, mlat, rot, fsz, mcol in mountain_arcs:
        mx, my = to_alb(mlon, mlat)
        ax.text(mx, my, mname, fontsize=fsz, fontweight="bold", color=mcol, rotation=rot,
                ha="center", va="center", zorder=15,
                path_effects=[pe.withStroke(linewidth=3.5, foreground="white")])

    # 代表性高峰（东灵山引线向西北外延，杜绝与太行山脉文字叠压）
    key_peaks = [
        ("东灵山 (2303m·北京之巅)", 115.44, 39.975, -2800, 2500, "right"),
        ("海坨山 (2241m·冬奥主峰)", 115.785, 40.555, 2000, 2000, "left"),
        ("白草畔 (2161m)", 115.545, 39.775, -2200, -2200, "right"),
        ("云蒙山 (1414m)", 116.710, 40.570, 2000, 2000, "left"),
        ("黑坨山 (1534m)", 116.380, 40.470, -2200, -2200, "right"),
        ("东南平原 (10m最低点)", 116.850, 39.650, 0, -2500, "center")
    ]
    for pname, plon, plat, ox, oy, ha in key_peaks:
        px, py = to_alb(plon, plat)
        ax.plot(px, py, marker="^", color="#922b21", markersize=8.0, markeredgecolor="white", markeredgewidth=0.8, zorder=12)
        ax.annotate(pname, xy=(px, py), xytext=(px + ox, py + oy),
                    arrowprops=dict(arrowstyle="->", color="#78281f", lw=0.7),
                    fontsize=8.0, fontweight="bold", color="#78281f", ha=ha, va="center", zorder=14,
                    path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    add_scalebar(ax, sb_x0, sb_y0, length_km=30)
    add_compass(ax, 0.94, 0.90)

    # 左下角高程色带（调整刻度标签，杜绝2000m与2303m重叠）
    cbar_ax = fig.add_axes([0.08, 0.08, 0.24, 0.016])
    cbar = fig.colorbar(matplotlib.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cbar_ax, orientation="horizontal")
    cbar.set_ticks([10, 500, 1000, 1500, 2303])
    cbar.set_ticklabels(["10m", "500m", "1000m", "1500m", "2303m"])
    cbar_ax.tick_params(labelsize=7.2)
    cbar_ax.set_title("海拔高度 (米)", fontsize=8.0, pad=3, color="#2c3e50")

    ax.set_title("北京市地形地貌与“北京湾”山峦合抱图", fontsize=15, fontweight="bold", pad=12, color=C_TEXT)
    ax.text(0.5, 0.985, "Geomorphological Relief of Beijing: The 'Beijing Bay' Mountain Arc & Plains",
            transform=ax.transAxes, ha="center", va="top", fontsize=9.0, color="#7f8c8d")
    fig.text(0.5, 0.015, "数据源：AWS Terrarium / Copernicus GLO-30 DEM · 阿里云 DataV · 制作：《中国地理知识手册》",
             ha="center", va="bottom", fontsize=8.0, color="#7f8c8d")

    out_path = os.path.join(OUT_DIR, "fig01-00-1_北京市地形地貌与燕山太行合抱图.png")
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Overview Map 1 saved: {out_path}")

# -------------------------------------------------------------------------
# 图 2：北京市五大水系格局图（加载真实水网与水体图斑）
# -------------------------------------------------------------------------
def make_overview_map2():
    print("Generating Overview Map 2 (Five River Systems with Real GIS Hydrology)...")
    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    # 底图各区微淡色
    bj_districts.plot(ax=ax, facecolor="#fdfefe", edgecolor="#bdc3c7", lw=0.6, zorder=2)
    gpd.GeoSeries([bj_union], crs=ALBERS).boundary.plot(ax=ax, color="#2c3e50", lw=2.2, zorder=3)

    # 加载真实水系与水体面数据（全域密云/官厅/怀柔大水库真实GIS多边形）
    waterways_file = os.path.join(osm_dir, "waterways.shp")
    water_a_file = os.path.join(DATA_DIR, "transport", "hebei", "gis_osm_water_a_free_1.shp")

    if os.path.exists(waterways_file):
        bj_waterways = gpd.read_file(waterways_file).to_crs(ALBERS)
        bj_waterways = gpd.clip(bj_waterways, bj_union)
        bj_waterways.plot(ax=ax, color="#2980b9", lw=0.85, alpha=0.9, zorder=6)

    if os.path.exists(water_a_file):
        all_water = gpd.read_file(water_a_file).to_crs(ALBERS)
        bj_water = all_water.cx[bb[0]:bb[2], bb[1]:bb[3]]
        bj_water = gpd.clip(bj_water, bj_union)
        bj_water.plot(ax=ax, facecolor="#85c1e9", edgecolor="#2471a3", lw=0.5, alpha=0.95, zorder=7)

    # 标注五大水系流域骨架（错开图例框）
    river_systems = [
        ("【潮白河水系】\n(密云水库·潮河·白河·潮白河)", 116.85, 40.38, "#1b4f72"),
        ("【永定河水系】\n(官厅水库·永定河百里山峡·冲积扇)", 115.82, 39.95, "#154360"),
        ("【北运河水系】\n(温榆河·通惠河·清河·京杭大运河)", 116.55, 39.88, "#1f618d"),
        ("【大清河水系】\n(拒马河·十渡峡谷·大石河)", 115.80, 39.75, "#2471a3"), # 抬高纬度，完全脱离左下角图例框
        ("【蓟运河水系】\n(泃河·洳河·金海湖)", 117.15, 40.25, "#2980b9")
    ]
    for rname, rlon, rlat, rcol in river_systems:
        rx, ry = to_alb(rlon, rlat)
        ax.text(rx, ry, rname, fontsize=8.8, fontweight="bold", color=rcol, ha="center", va="center", zorder=12,
                path_effects=[pe.withStroke(linewidth=3.0, foreground="white")])

    # 关键水库大水体（真实坐标注记）
    reservoirs = [
        ("密云水库 (华北最大·43.75亿m³)", 116.850, 40.500, 2000, 2000, "left"),
        ("官厅水库 (北京水域)", 115.760, 40.390, -2000, 2000, "right"),
        ("怀柔水库", 116.615, 40.315, 2000, -1500, "left"),
        ("十三陵水库", 116.265, 40.255, 2000, 1500, "left"),
        ("金海湖 (海子水库)", 117.340, 40.180, 2000, 1500, "left"),
        ("京密引水渠 (首都供水大动脉)", 116.300, 40.080, -2000, 1500, "right")
    ]
    for res_name, res_lon, res_lat, ox, oy, ha in reservoirs:
        rx, ry = to_alb(res_lon, res_lat)
        ax.plot(rx, ry, marker="o", color="#1b4f72", markersize=6.0, markeredgecolor="white", markeredgewidth=0.8, zorder=10)
        ax.annotate(res_name, xy=(rx, ry), xytext=(rx + ox, ry + oy),
                    arrowprops=dict(arrowstyle="->", color="#1b4f72", lw=0.6),
                    fontsize=7.8, fontweight="bold", color="#154360", ha=ha, va="center", zorder=11,
                    path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    add_scalebar(ax, sb_x0, sb_y0, length_km=30)
    add_compass(ax, 0.94, 0.90)

    leg_elements = [
        Line2D([0], [0], color="#2980b9", lw=1.5, label="干支流河道网络 (密云/官厅/运河水系)"),
        Patch(facecolor="#85c1e9", edgecolor="#2471a3", label="湖泊水库与蓄水水面 (密云水库/官厅等)"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#1b4f72", markersize=7, label="重点水库与引供水枢纽工程"),
        Patch(facecolor="none", edgecolor="#2c3e50", linewidth=1.8, label="北京市市级辖区边界")
    ]
    ax.legend(handles=leg_elements, loc="lower left", bbox_to_anchor=(0.04, 0.04), fontsize=7.8, framealpha=0.92,
              title="海河流域五大水系水网图例", title_fontsize=8.4)

    ax.set_title("北京市海河流域五大水系与地表水体格局图", fontsize=15, fontweight="bold", pad=12, color=C_TEXT)
    ax.text(0.5, 0.985, "Spatial Pattern of Five Major River Basins in Beijing (Haihe Basin)",
            transform=ax.transAxes, ha="center", va="top", fontsize=9.0, color="#7f8c8d")
    fig.text(0.5, 0.015, "数据源：北京市水务局 · 水利部海河水利委员会 · OpenStreetMap水系 · 制作：《中国地理知识手册》",
             ha="center", va="bottom", fontsize=8.0, color="#7f8c8d")

    out_path = os.path.join(OUT_DIR, "fig01-00-2_北京市五大水系格局图.png")
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Overview Map 2 saved: {out_path}")

# -------------------------------------------------------------------------
# 图 3：北京市十六区空间格局与功能分区图
# -------------------------------------------------------------------------
def make_overview_map3():
    print("Generating Overview Map 3 (16 Districts & 4 Functional Zones)...")
    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    # 四大功能区填色
    zone_colors = {
        "首都功能核心区": "#fadbd8",   # 东城、西城 (淡红)
        "中心城区": "#d4efdf",         # 朝阳、海淀、丰台、石景山 (淡绿)
        "平原新城": "#d6eaf8",         # 通州、顺义、大兴、昌平、房山 (淡蓝)
        "生态涵养区": "#fcf3cf"        # 门头沟、平谷、怀柔、密云、延庆 (淡黄)
    }

    core_names = ["东城区", "西城区"]
    central_names = ["朝阳区", "海淀区", "丰台区", "石景山区"]
    plain_names = ["通州区", "顺义区", "大兴区", "昌平区", "房山区"]
    eco_names = ["门头沟区", "平谷区", "怀柔区", "密云区", "延庆区"]

    def get_color(name):
        if name in core_names:
            return zone_colors["首都功能核心区"]
        if name in central_names:
            return zone_colors["中心城区"]
        if name in plain_names:
            return zone_colors["平原新城"]
        return zone_colors["生态涵养区"]

    bj_districts["color"] = bj_districts["name"].map(get_color)
    bj_districts.plot(ax=ax, color=bj_districts["color"], edgecolor="#34495e", lw=1.2, zorder=3)
    gpd.GeoSeries([bj_union], crs=ALBERS).boundary.plot(ax=ax, color="#1c2833", lw=2.4, zorder=4)

    # 标注 16 个区名称（核心区精细引线径向外展，杜绝微小图斑文字重叠与跨区误认）
    for idx, row in bj_districts.iterrows():
        name = row["name"]
        center = row.geometry.centroid
        px, py = center.x, center.y

        if name == "东城区":
            tx, ty = px + 8000, py - 6000
            ax.annotate("东城区", xy=(px, py), xytext=(tx, ty),
                        arrowprops=dict(arrowstyle="->", color="#78281f", lw=0.8),
                        fontsize=8.5, fontweight="bold", color="#78281f", ha="left", va="top", zorder=15,
                        path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])
        elif name == "西城区":
            tx, ty = px - 8000, py + 6000
            ax.annotate("西城区", xy=(px, py), xytext=(tx, ty),
                        arrowprops=dict(arrowstyle="->", color="#78281f", lw=0.8),
                        fontsize=8.5, fontweight="bold", color="#78281f", ha="right", va="bottom", zorder=15,
                        path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])
        elif name == "石景山区":
            tx, ty = px - 7500, py - 4000
            ax.annotate("石景山区", xy=(px, py), xytext=(tx, ty),
                        arrowprops=dict(arrowstyle="->", color="#1c2833", lw=0.8),
                        fontsize=8.5, fontweight="bold", color="#1c2833", ha="right", va="top", zorder=15,
                        path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])
        elif name == "海淀区":
            ax.text(px - 1500, py + 3500, name, fontsize=9.5, fontweight="bold", color="#1c2833",
                    ha="center", va="center", zorder=10,
                    path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])
        elif name == "朝阳区":
            ax.text(px + 3500, py + 2000, name, fontsize=9.5, fontweight="bold", color="#1c2833",
                    ha="center", va="center", zorder=10,
                    path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])
        elif name == "丰台区":
            ax.text(px, py - 3500, name, fontsize=9.5, fontweight="bold", color="#1c2833",
                    ha="center", va="center", zorder=10,
                    path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])
        elif name == "房山区":
            ax.text(px - 2000, py + 7500, name, fontsize=9.5, fontweight="bold", color="#1c2833",
                    ha="center", va="center", zorder=10,
                    path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])
        else:
            ax.text(px, py, name, fontsize=9.5, fontweight="bold", color="#1c2833",
                    ha="center", va="center", zorder=10,
                    path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    add_scalebar(ax, sb_x0, sb_y0, length_km=30)
    add_compass(ax, 0.94, 0.90)

    leg_elements = [
        Patch(facecolor=zone_colors["首都功能核心区"], edgecolor="#34495e", label="首都功能核心区 (东城、西城)"),
        Patch(facecolor=zone_colors["中心城区"], edgecolor="#34495e", label="中心城区 (朝阳、海淀、丰台、石景山)"),
        Patch(facecolor=zone_colors["平原新城"], edgecolor="#34495e", label="平原新城 (城市副中心通州、顺义、大兴、昌平、房山)"),
        Patch(facecolor=zone_colors["生态涵养区"], edgecolor="#34495e", label="生态涵养区 (门头沟、平谷、怀柔、密云、延庆)"),
        Line2D([0], [0], color="#1c2833", lw=2.2, label="北京市市级边界")
    ]
    ax.legend(handles=leg_elements, loc="lower left", bbox_to_anchor=(0.04, 0.05), fontsize=8.2, framealpha=0.92,
              title="北京城市总体规划四大功能区", title_fontsize=8.8)

    ax.set_title("北京市十六区行政区划与四大功能分区空间格局图", fontsize=15, fontweight="bold", pad=12, color=C_TEXT)
    ax.text(0.5, 0.985, "Spatial Structure of 16 Districts & Four Functional Strategic Zones in Beijing",
            transform=ax.transAxes, ha="center", va="top", fontsize=9.0, color="#7f8c8d")
    fig.text(0.5, 0.015, "底图数据：自然资源部 / 阿里云 DataV (2021.5) · 制作：《中国地理知识手册》",
             ha="center", va="bottom", fontsize=8.0, color="#7f8c8d")

    out_path = os.path.join(OUT_DIR, "fig01-00-3_北京市十六区空间格局与功能分区图.png")
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Overview Map 3 saved: {out_path}")

# -------------------------------------------------------------------------
# 图 4：北京市综合交通骨架与枢纽网络图
# -------------------------------------------------------------------------
def make_overview_map4():
    print("Generating Overview Map 4 (Transportation Network & Dispersed Mega Hubs)...")
    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    bj_districts.plot(ax=ax, facecolor="#fdfefe", edgecolor="none", zorder=2)

    # 真实路网：四层绘制，secondary 用极淡细线打底。
    # 只画 motorway/expressway/primary 时，中心城区（六环内）只剩几条放射线，
    # 整片留白会被读成"路网缺失"；而真实路网密度恰恰集中在这里。
    if BJ_ROADS:
        mapkit.draw_roads(ax, BJ_ROADS,
                          order=("secondary", "primary", "expressway", "motorway"),
                          override={"secondary": dict(color="#b0bcc6", lw=0.40)})

    bj_districts.boundary.plot(ax=ax, color="#aab7b8", lw=0.5, zorder=5)
    gpd.GeoSeries([bj_union], crs=ALBERS).boundary.plot(ax=ax, color="#2c3e50", lw=2.2, zorder=6)

    # 关键综合交通超级枢纽（径向辐射外展排版，彻底消除城六区特等站文字叠压）
    hubs = [
        ("首都国际机场 (PEK·第一国门)", 116.587, 40.080, "airport", 25, 20, "left"),
        ("大兴国际机场 (PKX·新国门金凤)", 116.410, 39.510, "airport", -30, -25, "right"),
        ("北京西站 (京广高铁特等枢纽)", 116.320, 39.895, "rail", -35, 18, "right"),
        ("北京南站 (京沪高铁特等客运)", 116.378, 39.865, "rail", 18, -25, "left"),
        ("北京丰台站 (特等立体交通枢纽)", 116.315, 39.852, "rail", -35, -20, "right"),
        ("北京朝阳站 (京哈高铁特等始发)", 116.512, 39.948, "rail", 25, 18, "left"),
        ("清河站 (京张高铁特等枢纽)", 116.315, 40.033, "rail", -30, 18, "right"),
        ("城市副中心站 (亚洲最大地下综合枢纽)", 116.690, 39.905, "rail", 25, -18, "left")
    ]

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    # 骨干放射高速与环线指示文字
    corridor_labels = [
        ("G6京藏/G7京新高速通道", 116.10, 40.24, 45),
        ("G45大广高速(京承段)", 116.60, 40.30, 60),
        ("G1京哈高速走廊", 116.70, 39.85, 20),
        ("S3501大兴机场高速通道", 116.41, 39.68, 90),
        ("G4京港澳高速走廊", 116.12, 39.75, 45)
    ]

    # 图面零文字：枢纽与通道只画「符号 + 编号」，名称与含义统一进图外图例
    sl = mapkit.SymbolLabels(ax, fig)
    sl.reserve([(0.60, 0.0, 1.0, 0.12),    # 比例尺
                (0.86, 0.80, 1.0, 1.0)])   # 指北针
    for hname, hlon, hlat, htype, _ox, _oy, _ha in hubs:
        hx, hy = to_alb(hlon, hlat)
        kind = "airport" if htype == "airport" else "rail_hub"
        nm, nt = mapkit.split_note(hname)
        sl.add(hx, hy, nm, kind, note=nt,
               priority=0 if htype == "airport" else 1)

    for cname, clon, clat, rot in corridor_labels:
        cx_c, cy_c = to_alb(clon, clat)
        nm, nt = mapkit.split_note(cname)
        sl.add(cx_c, cy_c, nm, "corridor", note=nt)
    sym_type_h, sym_idx_h = sl.flush()

    add_scalebar(ax, sb_x0, sb_y0, length_km=30)
    add_compass(ax, 0.94, 0.90)

    # 符号含义由 SymbolLabels 统一给出，这里只留线型与边界，
    # 否则"民用运输机场"和"双枢纽超级国际机场"会在同一图例里出现两遍。
    leg_elements = []
    if BJ_ROADS:
        # 四层都画了，图例四层都要列（此前只画三层、图例也过滤掉省道）
        leg_elements += mapkit.road_legend_handles(BJ_ROADS)
    leg_elements += [
        Patch(facecolor="none", edgecolor="#2c3e50", linewidth=2.0, label="北京市市级辖区边界")
    ]
    # 图例移到图幅外下方：原先 bbox_to_anchor=(0.04, 0.05) 落在图内左下角，
    # 正好盖住西南部路网与丰台站、大兴机场注记。
    leg = mapkit.stacked_legends(ax, [
        dict(handles=leg_elements + sym_type_h, title="线型与符号含义",
             ncol=3, fontsize=7.6, title_fontsize=8.4),
        dict(handles=sym_idx_h, title="图上编号对照（编号标注于符号旁）",
             ncol=2, fontsize=7.6, title_fontsize=8.4),
    ], top=-0.010, gap=0.014)

    ax.set_title("北京市综合立体交通骨架与超级枢纽网络图", fontsize=15, fontweight="bold", pad=12, color=C_TEXT)
    ax.text(0.5, 0.985, "Comprehensive Transportation Network & Mega Aviation/Railway Hubs of Beijing",
            transform=ax.transAxes, ha="center", va="top", fontsize=9.0, color="#7f8c8d")
    mapkit.footer_below_legend(
        ax, leg,
        "数据源：中国民用航空局 · 中国国家铁路集团 · 北京市交通委员会 · 制作：《中国地理知识手册》",
        fontsize=8.0)

    out_path = os.path.join(OUT_DIR, "fig01-00-4_北京市综合交通骨架与枢纽网络图.png")
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Overview Map 4 saved: {out_path}")

# -------------------------------------------------------------------------
# 图 5：北京市经济总量与空间夜光演进图
# -------------------------------------------------------------------------
def make_overview_map5():
    print("Generating Overview Map 5 (Nightlight & GDP History)...")
    bj_annual_nl = nl_clean_df.groupby("year")["sum"].sum().reset_index()

    gdp_data = {
        2000: 3161.7,
        2005: 6969.5,
        2010: 14113.6,
        2015: 23014.6,
        2020: 36102.6,
        2022: 41610.9,
        2023: 43760.7,
        2024: 47560.2
    }
    years_gdp = sorted(gdp_data.keys())
    values_gdp = [gdp_data[y] for y in years_gdp]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5.2), dpi=DPI)
    fig.patch.set_facecolor("white")

    # 子图 1：夜间灯光（严格针对真实 1986—2013 DMSP-OLS 数据序列）
    ax1.set_facecolor("#fafbfc")
    years_nl = bj_annual_nl["year"].values
    sum_nl = bj_annual_nl["sum"].values

    ax1.plot(years_nl, sum_nl, color="#e67e22", lw=2.4, marker="o", markersize=4.5, label="全市夜光辐射总量 (sum)")
    ax1.fill_between(years_nl, sum_nl, color="#fdebd0", alpha=0.5)

    ax1.annotate("1990年：北京亚运会\n开启超大城市空间现代化", xy=(1990, 102682), xytext=(1988, 175000),
                 arrowprops=dict(arrowstyle="->", color="#c0392b", lw=1.0),
                 fontsize=8.0, color="#922b21", fontweight="bold",
                 bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#e6b0aa", alpha=0.9))

    ax1.annotate("2001年：申奥成功\n启动奥运场馆与首都新空间", xy=(2001, 235577), xytext=(1995, 290000),
                 arrowprops=dict(arrowstyle="->", color="#c0392b", lw=1.0),
                 fontsize=8.0, color="#922b21", fontweight="bold",
                 bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#e6b0aa", alpha=0.9))

    ax1.annotate("2008年：北京夏季奥运会\n奥林匹克中心区与首都机场T3", xy=(2008, 323755), xytext=(2001, 385000),
                 arrowprops=dict(arrowstyle="->", color="#c0392b", lw=1.0),
                 fontsize=8.0, color="#922b21", fontweight="bold",
                 bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#e6b0aa", alpha=0.9))

    ax1.set_title("北京市夜间灯光辐射总值历史变化 (1986—2013)", fontsize=11.5, fontweight="bold", color=C_TEXT, pad=10)
    ax1.set_xlabel("年份 (Year)", fontsize=9.2)
    ax1.set_ylabel("夜间灯光辐射总量 (nW/cm²/sr)", fontsize=9.2)
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.set_xlim(1985, 2014)
    ax1.set_ylim(0, 460000)

    # 子图 2：GDP 演进 (2000—2024)
    ax2.set_facecolor("#fafbfc")
    bars = ax2.bar([str(y) for y in years_gdp], values_gdp, color="#2980b9", width=0.6, label="北京市 GDP (亿元)")
    bars[-2].set_color("#c0392b") # 2023
    bars[-1].set_color("#27ae60") # 2024

    for b in bars:
        h = b.get_height()
        ax2.text(b.get_x() + b.get_width()/2., h + 600, f"{int(h):d}",
                 ha="center", va="bottom", fontsize=7.8, color="#2c3e50")

    ax2.annotate("2024年GDP达4.75万亿\n迈向5万亿元全国第一梯队", xy=(7, 47560.2), xytext=(5.0, 53000),
                 arrowprops=dict(arrowstyle="->", color="#27ae60", lw=1.2),
                 fontsize=8.2, color="#196f3d", fontweight="bold",
                 bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#27ae60", alpha=0.9))

    ax2.set_title("北京市地区生产总值（现价 GDP）跨越历程 (2000—2024)", fontsize=11.5, fontweight="bold", color=C_TEXT, pad=10)
    ax2.set_xlabel("年份 (Year)", fontsize=9.2)
    ax2.set_ylabel("地区生产总值 (亿元)", fontsize=9.2)
    ax2.grid(True, axis="y", linestyle="--", alpha=0.5)
    ax2.set_ylim(0, 60000)

    fig.suptitle("北京市空间经济活力演进：遥感夜光与 GDP 历史大跨越",
                 fontsize=13.5, fontweight="bold", color=C_TEXT, y=0.98)
    fig.text(0.5, 0.015, "数据来源：夜间灯光遥感数据 · 国家统计局《中国城市统计年鉴》· 北京市统计局 · 制作：《中国地理知识手册》",
             ha="center", fontsize=8.0, color="#7f8c8d")

    plt.tight_layout(rect=[0, 0.04, 1, 0.94])
    out_path = os.path.join(OUT_DIR, "fig01-00-5_北京市经济总量与空间夜光演进图.png")
    fig.savefig(out_path, dpi=DPI)
    plt.close(fig)
    print(f"Overview Map 5 saved: {out_path}")

if __name__ == "__main__":
    make_overview_map1()
    make_overview_map2()
    make_overview_map3()
    make_overview_map4()
    make_overview_map5()
    print("All 5 Beijing Municipal Overview figures successfully generated!")
