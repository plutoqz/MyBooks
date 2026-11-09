# -*- coding: utf-8 -*-
"""山西省地理统揽专题地图生成引擎（04-00）
包含 5 幅全省域权威地图与分析图表（精细调优排版、微缩字号、严格杜绝压盖、要素清晰呼应）：
1. fig04-00-1_山西省地形地貌与表里山河格局图.png
2. fig04-00-2_山西省行政区划与空间骨架图.png
3. fig04-00-3_山西省综合立体交通网与能源大通道图.png
4. fig04-00-4_山西省产业经济与综合能源基地分布图.png
5. fig04-00-5_山西省生态安全屏障与自然水系格局图.png
"""
import os
import sys
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import Rectangle, Patch, PathPatch, Polygon
from matplotlib.path import Path
from matplotlib.lines import Line2D
from matplotlib.colors import LinearSegmentedColormap, Normalize
from pyproj import Transformer

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, r"D:\code\Ideas\MyBooks\中国地理知识手册\scripts")
from style import ALBERS, C_TEXT, DATA, DPI, FIGURES, setup
from prov_pipeline import prov_dem
import mapkit

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

def add_scalebar(ax, x0, y0, length_km=100):
    mapkit.add_scalebar(ax, x0, y0, length_km=length_km)

def add_compass(ax, x=0.94, y=0.92):
    ax.annotate("N", xy=(x, y), xytext=(x, y - 0.055), transform=ax.transAxes,
                arrowprops=dict(facecolor="#2c3e50", edgecolor="#2c3e50", width=1.8, headwidth=5.5, headlength=6.5),
                ha="center", va="center", fontsize=8.8, fontweight="bold", color="#2c3e50", zorder=30)

print("Loading Shanxi provincial spatial data...")
DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
sx_cities = gpd.read_file(os.path.join(DATA_DIR, "boundaries", "datav", "140000_full.json")).to_crs(ALBERS)
sx_union = sx_cities.union_all()
bb = sx_cities.total_bounds

# 视口与中心计算：山西呈南北长条形，适度扩展四周留白
cx = (bb[0] + bb[2]) / 2.0
cy = (bb[1] + bb[3]) / 2.0
span_x = bb[2] - bb[0]
span_y = bb[3] - bb[1]

# 设定视口缓冲
pad_x = span_x * 0.12
pad_y = span_y * 0.08
ax_xlim = (bb[0] - pad_x, bb[2] + pad_x)
ax_ylim = (bb[1] - pad_y, bb[3] + pad_y)

# 加载 DEM
print("Loading Shanxi DEM...")
dem_sx, dem_minx, dem_maxy, dem_res = prov_dem("140000", zoom=9, res=300.0)

# 加载邻接省份边界作为地理背景参考
print("Loading neighboring provinces for regional context...")
neigh_files = {
    "河北省": "130000_full.json",
    "陕西省": "610000_full.json",
    "河南省": "410000_full.json",
    "内蒙古自治区": "150000_full.json",
    "北京市": "110000_full.json"
}
neigh_gdfs = {}
for pname, fname in neigh_files.items():
    fpath = os.path.join(DATA_DIR, "boundaries", "datav", fname)
    if os.path.exists(fpath):
        neigh_gdfs[pname] = gpd.read_file(fpath).to_crs(ALBERS)

# 11 地级市政府驻地权威坐标
CITY_GOV_COORDS = {
    "太原市": (112.549, 37.857),
    "大同市": (113.295, 40.090),
    "阳泉市": (113.583, 37.861),
    "长治市": (113.116, 36.195),
    "晋城市": (112.851, 35.497),
    "朔州市": (112.433, 39.331),
    "晋中市": (112.753, 37.687),
    "运城市": (111.007, 35.026),
    "忻州市": (112.733, 38.416),
    "临汾市": (111.517, 36.084),
    "吕梁市": (111.134, 37.524)
}

# 邻近省份行政标注位置
NEIGHBOR_LABELS = [
    ("陕  西  省\n(Shaanxi)", 109.40, 36.80),
    ("河  北  省\n(Hebei)", 115.00, 38.20),
    ("河  南  省\n(Henan)", 112.80, 34.60),
    ("内蒙古自治区\n(Inner Mongolia)", 111.80, 40.85)
]

def draw_neighbor_context(ax):
    """绘制邻接省份底色与文字"""
    for pname, ngdf in neigh_gdfs.items():
        ngdf.plot(ax=ax, facecolor="#f4f6f7", edgecolor="#bdc3c7", lw=0.6, ls="--", alpha=0.7, zorder=2)
    for txt, nlon, nlat in NEIGHBOR_LABELS:
        nx, ny = to_alb(nlon, nlat)
        if ax_xlim[0] <= nx <= ax_xlim[1] and ax_ylim[0] <= ny <= ax_ylim[1]:
            ax.text(nx, ny, txt, ha="center", va="center", fontsize=8.0, fontweight="bold",
                    color="#7f8c8d", zorder=8,
                    bbox=dict(boxstyle="round,pad=0.25", facecolor="#ffffff", edgecolor="#d5dbdb", alpha=0.85))

# =============================================================================
# 1. fig04-00-1_山西省地形地貌与表里山河格局图
# =============================================================================
def gen_fig1():
    print("Generating fig04-00-1_山西省地形地貌与表里山河格局图.png...")
    fig, ax = plt.subplots(figsize=(9.6, 11.2), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    draw_neighbor_context(ax)

    # DEM 渲染
    hs = calc_hillshade(dem_sx, dem_res)
    colors = [
        (0.00, "#a8c878"),   # 运城/临汾低平原嫩绿
        (0.12, "#cce09b"),
        (0.25, "#e8d696"),   # 浅丘陵与盆地暖黄
        (0.45, "#d2b48c"),   # 黄土高原台原与中山棕褐
        (0.68, "#a0785a"),   # 太行/吕梁高中山深褐
        (0.85, "#8b6548"),
        (1.00, "#f5f5f5")    # 五台山北台叶斗峰灰白
    ]
    cmap_elev = LinearSegmentedColormap.from_list("shanxi_relief", colors)
    valid = np.nan_to_num(dem_sx, nan=180.0)
    valid = np.clip(valid, 180.0, 3062.0)
    norm = Normalize(vmin=180, vmax=3062)
    rgb = cmap_elev(norm(valid))[:, :, :3]
    rgb_shaded = rgb * (0.42 + 0.58 * hs[:, :, np.newaxis])

    dem_extent = (dem_minx, dem_minx + dem_sx.shape[1] * dem_res,
                  dem_maxy - dem_sx.shape[0] * dem_res, dem_maxy)
    im = ax.imshow(rgb_shaded, extent=dem_extent, origin="upper", zorder=3)
    patch = get_mpl_clip_patch(sx_union)
    ax.add_patch(patch)
    im.set_clip_path(patch)

    # 绘制山西省界与各市分界
    sx_cities.boundary.plot(ax=ax, color="#2c3e50", lw=0.6, ls=":", zorder=5)
    gpd.GeoSeries([sx_union]).boundary.plot(ax=ax, color="#1a252f", lw=1.3, zorder=6)

    # 主要山脉走向注记
    ranges = [
        ("太  行  山  脉", 113.80, 37.30, 75),
        ("吕  梁  山  脉", 111.35, 37.60, 76),
        ("中  条  山  脉", 111.55, 35.10, 15),
        ("太  岳  山  脉", 112.10, 36.70, 48),
        ("北 岳 恒 山", 113.75, 39.75, -15),
        ("五  台  山", 113.55, 39.05, 30),
        ("管  涔  山", 111.95, 38.85, 45)
    ]
    for name, rlon, rlat, rot in ranges:
        rx, ry = to_alb(rlon, rlat)
        ax.text(rx, ry, name, ha="center", va="center", fontsize=8.8, fontweight="bold",
                color="#4a3b32", rotation=rot, zorder=10,
                path_effects=[pe.withStroke(linewidth=2.2, foreground="#ffffff")])

    # 六大断陷裂谷盆地注记（“三晋走廊”）
    basins = [
        ("大 同 盆 地\n(950-1100m)", 113.35, 40.05),
        ("忻 定 盆 地\n(600-800m)", 112.80, 38.55),
        ("太 原 盆 地 (晋中盆地)\n(760-820m)", 112.45, 37.45),
        ("临 汾 盆 地\n(380-500m)", 111.50, 36.10),
        ("运 城 盆 地\n(320-450m)", 111.00, 35.15),
        ("上 党 盆 地 (长治盆地)\n(900-1050m)", 113.10, 36.25)
    ]
    for bname, blon, blat in basins:
        bx, by = to_alb(blon, blat)
        ax.text(bx, by, bname, ha="center", va="center", fontsize=7.2, fontweight="bold",
                color="#784212", zorder=10,
                bbox=dict(boxstyle="round,pad=0.2", facecolor="#fef9e7", edgecolor="#f39c12", alpha=0.88),
                path_effects=[pe.withStroke(linewidth=1.8, foreground="#ffffff")])

    # 著名山峰与极值注记（精心校准偏移引线）
    peaks = [
        ("五台山北台叶斗峰 (3061.1m·华北屋脊·最高峰)", 113.585, 39.055, 40, 25, "left"),
        ("恒山天峰岭 (2016m·北岳名山)", 113.725, 39.645, 35, 18, "left"),
        ("关帝山孝文山 (2831m·吕梁山主峰)", 111.505, 37.755, -45, 20, "right"),
        ("芦芽山 (2744m·汾河源头)", 111.905, 38.745, -45, 18, "right"),
        ("太岳山牛角鞍 (2541m)", 112.085, 36.685, -40, -18, "right"),
        ("中条山历山舜王坪 (2358m)", 111.895, 35.405, 35, 15, "left"),
        ("娄烦云顶山 (2772m)", 111.835, 38.225, -40, 18, "right"),
        ("芮城西陌村黄河滩地 (180.0m·全省最低点)", 110.285, 34.615, 30, -22, "left")
    ]
    for pname, plon, plat, ox, oy, ha in peaks:
        px, py = to_alb(plon, plat)
        marker_color = "#b03a2e" if "最低点" not in pname else "#1e8449"
        marker_symbol = "^" if "最低点" not in pname else "v"
        ax.plot(px, py, marker_symbol, color=marker_color, markersize=6.2, zorder=11)
        ax.annotate(pname, xy=(px, py), xytext=(ox, oy), textcoords="offset points",
                    fontsize=6.8, fontweight="bold", color="#78281f" if "最低点" not in pname else "#145a32",
                    ha=ha, va="center", zorder=12,
                    path_effects=[pe.withStroke(linewidth=2.0, foreground="#ffffff")],
                    arrowprops=dict(arrowstyle="->", color=marker_color, lw=0.6))

    # 水系节点与特殊地貌
    water_nodes = [
        ("晋陕黄河大峡谷", 110.55, 37.35, "center", "center", 85),
        ("黄河壶口瀑布 (5A)", 110.45, 36.15, "right", "center", 0),
        ("偏关老牛湾 (黄河入晋/长城握手)", 111.45, 39.60, "left", "bottom", 0),
        ("运城七彩盐湖", 110.98, 35.00, "center", "top", 0),
        ("汾河水库", 111.85, 38.10, "right", "center", 0)
    ]
    for wname, wlon, wlat, wha, wva, wrot in water_nodes:
        wx, wy = to_alb(wlon, wlat)
        ax.text(wx, wy, wname, ha=wha, va=wva, rotation=wrot, fontsize=7.2, color="#1b4f72",
                fontweight="bold", style="italic", zorder=11,
                path_effects=[pe.withStroke(linewidth=2.0, foreground="#ffffff")])

    # 标题与排版
    ax.set_title("山西省地形地貌与表里山河格局图", fontsize=13.0, fontweight="bold", color=C_TEXT, pad=20)
    ax.text(0.5, 1.015, "Topography, Geomorphology and \"Inside & Outside Mountains-Rivers\" of Shanxi",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=8.0, color="#555555")

    # 罗盘与比例尺
    add_compass(ax, x=0.94, y=0.92)
    add_scalebar(ax, ax_xlim[0] + (ax_xlim[1] - ax_xlim[0]) * 0.05, ax_ylim[0] + (ax_ylim[1] - ax_ylim[0]) * 0.035, length_km=100)

    # 高程图例
    cax = ax.inset_axes([0.05, 0.08, 0.025, 0.22])
    cb = plt.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap_elev), cax=cax, orientation="vertical")
    cb.set_label("高程 Elevation (m)", fontsize=6.8, color="#2c3e50")
    cb.ax.tick_params(labelsize=6.0, length=2.2)

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")
    out_path = os.path.join(OUT_DIR, "fig04-00-1_山西省地形地貌与表里山河格局图.png")
    plt.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close()
    print(f"Saved: {out_path}")

# =============================================================================
# 2. fig04-00-2_山西省行政区划与空间骨架图
# =============================================================================
def gen_fig2():
    print("Generating fig04-00-2_山西省行政区划与空间骨架图.png...")
    fig, ax = plt.subplots(figsize=(9.6, 11.2), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    draw_neighbor_context(ax)

    # 11 地级市填色
    city_colors = {
        "太原市": "#fdedec",  # 省会淡红
        "大同市": "#fcf3cf",  # 晋北暖杏
        "朔州市": "#f9ebea",
        "忻州市": "#eafaf1",  # 晋北/华北屋脊淡绿
        "阳泉市": "#ebf5fb",  # 晋东淡蓝
        "晋中市": "#fef9e7",  # 晋商故里暖金
        "长治市": "#f5eef8",  # 上党高地淡紫
        "晋城市": "#e8f8f5",  # 晋东南淡青
        "临汾市": "#fef5e7",  # 尧都平阳浅橙
        "运城市": "#eaf2f8",  # 晋南盐湖天蓝
        "吕梁市": "#e8f6f3"   # 吕梁山原淡翠
    }

    for _, row in sx_cities.iterrows():
        cname = row.get("name", "")
        fc = city_colors.get(cname, "#f4f6f7")
        gpd.GeoSeries([row.geometry]).plot(ax=ax, facecolor=fc, edgecolor="#566573", lw=0.8, zorder=4)

    # 城市驻地引线与文字避让
    city_label_offsets = {
        "太原市": (22, 16, "left"),
        "大同市": (22, 16, "left"),
        "朔州市": (-24, 16, "right"),
        "忻州市": (22, 16, "left"),
        "阳泉市": (22, 12, "left"),
        "晋中市": (22, -14, "left"),
        "长治市": (22, 14, "left"),
        "晋城市": (22, -14, "left"),
        "临汾市": (-22, -14, "right"),
        "运城市": (-22, -14, "right"),
        "吕梁市": (-22, 16, "right")
    }

    for cname, (clon, clat) in CITY_GOV_COORDS.items():
        cx_pt, cy_pt = to_alb(clon, clat)
        is_prov_cap = (cname == "太原市")
        marker = "s" if is_prov_cap else "o"
        mcolor = "#c0392b" if is_prov_cap else "#2980b9"
        msize = 7.8 if is_prov_cap else 5.5
        label_text = f"★ {cname}\n(省会极核)" if is_prov_cap else cname

        ax.plot(cx_pt, cy_pt, marker, color=mcolor, markersize=msize, markeredgecolor="white", markeredgewidth=0.8, zorder=12)
        ox, oy, ha = city_label_offsets.get(cname, (20, 15, "left"))
        ax.annotate(label_text, xy=(cx_pt, cy_pt), xytext=(ox, oy), textcoords="offset points",
                    ha=ha, va="center", fontsize=7.8 if not is_prov_cap else 8.5,
                    fontweight="bold", color="#78281f" if is_prov_cap else "#1a252f", zorder=13,
                    path_effects=[pe.withStroke(linewidth=2.2, foreground="#ffffff")],
                    arrowprops=dict(arrowstyle="-", color="#7f8c8d", lw=0.5))

    # 绘制全省“一群两区三圈”现代空间架构示意骨架
    # 太原都市圈 / 太忻一体化轴线
    ty_x, ty_y = to_alb(112.549, 37.857)
    xz_x, xz_y = to_alb(112.733, 38.416)
    jz_x, jz_y = to_alb(112.753, 37.687)
    dt_x, dt_y = to_alb(113.295, 40.090)
    lf_x, lf_y = to_alb(111.517, 36.084)
    yc_x, yc_y = to_alb(111.007, 35.026)
    cz_x, cz_y = to_alb(113.116, 36.195)
    jc_x, jc_y = to_alb(112.851, 35.497)

    # 发展走廊连线
    ax.plot([ty_x, xz_x], [ty_y, xz_y], color="#c0392b", lw=2.8, ls="--", alpha=0.7, zorder=9)
    ax.text((ty_x + xz_x)/2 + 10000, (ty_y + xz_y)/2, "太忻一体化经济区", fontsize=7.2, fontweight="bold",
            color="#900c3f", zorder=15, path_effects=[pe.withStroke(linewidth=1.8, foreground="#ffffff")])

    ax.plot([ty_x, jz_x], [ty_y, jz_y], color="#e67e22", lw=3.0, alpha=0.7, zorder=9)
    ax.text((ty_x + jz_x)/2 - 12000, (ty_y + jz_y)/2 - 12000, "太原—晋中同城核心圈", fontsize=7.2, fontweight="bold",
            color="#b9770e", zorder=15, ha="right", path_effects=[pe.withStroke(linewidth=1.8, foreground="#ffffff")])

    # 晋南城镇群与晋东南城镇圈标注
    ax.text((lf_x + yc_x)/2 + 15000, (lf_y + yc_y)/2, "晋南城镇圈 (临汾·运城)", fontsize=7.2, fontweight="bold",
            color="#1b4f72", zorder=15, path_effects=[pe.withStroke(linewidth=1.8, foreground="#ffffff")])
    ax.text((cz_x + jc_x)/2 + 15000, (cz_y + jc_y)/2, "晋东南城镇圈 (长治·晋城)", fontsize=7.2, fontweight="bold",
            color="#5b2c6f", zorder=15, path_effects=[pe.withStroke(linewidth=1.8, foreground="#ffffff")])
    ax.text(dt_x + 18000, dt_y - 12000, "晋北城镇圈 (大同副中心·朔州)", fontsize=7.2, fontweight="bold",
            color="#145a32", zorder=15, path_effects=[pe.withStroke(linewidth=1.8, foreground="#ffffff")])

    # 边界加粗
    gpd.GeoSeries([sx_union]).boundary.plot(ax=ax, color="#1a252f", lw=1.5, zorder=7)

    # 标题与排版
    ax.set_title("山西省行政区划与空间骨架图", fontsize=13.0, fontweight="bold", color=C_TEXT, pad=20)
    ax.text(0.5, 1.015, "Administrative Divisions and Spatial Framework of Shanxi Province",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=8.0, color="#555555")

    # 罗盘与比例尺
    add_compass(ax, x=0.94, y=0.92)
    add_scalebar(ax, ax_xlim[0] + (ax_xlim[1] - ax_xlim[0]) * 0.05, ax_ylim[0] + (ax_ylim[1] - ax_ylim[0]) * 0.035, length_km=100)

    # 图例
    legend_elements = [
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#c0392b", markeredgecolor="w", markersize=8, label="省会极核 (太原市)"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#2980b9", markeredgecolor="w", markersize=6.5, label="地级市行政中心 (10市)"),
        Line2D([0], [0], color="#c0392b", lw=2.2, ls="--", label="太忻一体化发展轴"),
        Line2D([0], [0], color="#e67e22", lw=2.2, label="太原—晋中同城化核心轴"),
        Patch(facecolor="#f4f6f7", edgecolor="#bdc3c7", linestyle="--", label="邻省接壤行政区")
    ]
    leg = ax.legend(handles=legend_elements, loc="lower right", fontsize=7.0, framealpha=0.92,
                    title="空间骨架图例", title_fontsize=7.6)
    leg.set_zorder(20)

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")
    out_path = os.path.join(OUT_DIR, "fig04-00-2_山西省行政区划与空间骨架图.png")
    plt.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close()
    print(f"Saved: {out_path}")

# =============================================================================
# 3. fig04-00-3_山西省综合立体交通网与能源大通道图
# =============================================================================
def gen_fig3():
    print("Generating fig04-00-3_山西省综合立体交通网与能源大通道图.png...")
    fig, ax = plt.subplots(figsize=(9.6, 11.2), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    draw_neighbor_context(ax)

    # 底图
    sx_cities.plot(ax=ax, facecolor="#fdfefe", edgecolor="#bdc3c7", lw=0.6, zorder=3)
    gpd.GeoSeries([sx_union]).boundary.plot(ax=ax, color="#2c3e50", lw=1.3, zorder=4)

    # 1. 四大重载能源铁路通道（高识别度深色实线与发端/出境节点）
    heavy_rails = [
        ("大秦铁路 (重载第一路·大同至秦皇岛港)", [(113.3, 40.1), (113.6, 40.0), (114.1, 40.2), (114.5, 40.3)], "#78281f", 3.0, "-"),
        ("朔黄铁路 (神池南至黄骅港)", [(111.9, 39.1), (112.4, 38.9), (113.2, 38.7), (113.8, 38.5)], "#922b21", 2.8, "-"),
        ("瓦日铁路 (晋中南通道·瓦塘至日照港)", [(111.0, 37.9), (111.4, 37.6), (112.0, 36.6), (112.8, 36.2), (113.5, 36.1)], "#641e16", 3.0, "-"),
        ("侯月铁路 (侯马至月山)", [(111.3, 35.6), (111.8, 35.5), (112.5, 35.4), (113.1, 35.3)], "#7b241c", 2.5, "-")
    ]
    for rname, rpts, rcolor, rlw, rls in heavy_rails:
        palb = [to_alb(p[0], p[1]) for p in rpts]
        xs, ys = mapkit.smooth_line(palb)
        ax.plot(xs, ys, color=rcolor, lw=rlw, ls=rls, zorder=6)
        # 沿线中点标注
        mid_idx = len(xs) // 2
        ax.text(xs[mid_idx], ys[mid_idx] + 7000, rname.split("(")[0].strip(),
                fontsize=7.2, fontweight="bold", color=rcolor, zorder=14,
                path_effects=[pe.withStroke(linewidth=2.0, foreground="#ffffff")])

    # 2. 核心高速铁路客运通道（双色虚线）
    hsr_lines = [
        ("大西客运专线 (大同-太原-西安)", [(113.3, 40.1), (112.4, 39.3), (112.7, 38.4), (112.5, 37.8), (112.7, 37.7), (111.5, 36.1), (111.0, 35.0), (110.3, 34.6)], "#1f618d", 2.5, "--"),
        ("郑太高速铁路 (太原-长治-晋城-郑州)", [(112.5, 37.8), (112.7, 37.7), (113.1, 36.2), (112.8, 35.5), (113.0, 35.2)], "#2874a6", 2.5, "--"),
        ("石太客运专线 (太原至石家庄)", [(112.5, 37.8), (113.1, 37.9), (113.6, 37.9), (114.2, 38.0)], "#1a5276", 2.5, "--")
    ]
    for hname, hpts, hcolor, hlw, hls in hsr_lines:
        palb = [to_alb(p[0], p[1]) for p in hpts]
        xs, ys = mapkit.smooth_line(palb)
        ax.plot(xs, ys, color=hcolor, lw=hlw, ls=hls, zorder=7)
        mid_idx = len(xs) // 2
        ax.text(xs[mid_idx] + 8000, ys[mid_idx] - 7000, hname.split("(")[0].strip(),
                fontsize=7.2, fontweight="bold", color=hcolor, zorder=14,
                path_effects=[pe.withStroke(linewidth=2.0, foreground="#ffffff")])

    # 3. 骨干高速公路通道（G55二广、G5京昆、G20青银、G59呼北）
    expressways = [
        ("G55 二广高速", [(113.3, 40.2), (112.7, 38.4), (112.5, 37.8), (113.1, 36.2), (112.8, 35.3)], "#d35400", 1.8),
        ("G5 京昆高速", [(113.8, 38.1), (112.5, 37.8), (111.8, 37.2), (111.5, 36.1), (110.5, 35.0)], "#e67e22", 1.8),
        ("G20 青银高速", [(113.8, 37.8), (112.5, 37.8), (111.8, 37.5), (111.1, 37.5)], "#f39c12", 1.6),
        ("G59 呼北高速 (沿黄走廊)", [(111.5, 39.5), (111.0, 38.2), (110.8, 37.1), (110.5, 35.5), (110.3, 34.6)], "#b9770e", 1.6)
    ]
    for ename, epts, ecolor, elw in expressways:
        palb = [to_alb(p[0], p[1]) for p in epts]
        xs, ys = mapkit.smooth_line(palb)
        ax.plot(xs, ys, color=ecolor, lw=elw, ls="-", alpha=0.85, zorder=5)

    # 4. 民用运输机场群与关键枢纽
    airports = [
        ("太原武宿国际机场 (4E/枢纽)", 112.628, 37.748, 25, -15, "left"),
        ("大同云冈机场 (4C)", 113.485, 40.065, 25, 12, "left"),
        ("运城张孝机场 (4E/关公)", 111.035, 35.115, 25, 12, "left"),
        ("长治王村机场 (4C)", 113.125, 36.245, 25, 12, "left"),
        ("临汾乔李机场 (4C)", 111.635, 36.135, 25, 12, "left"),
        ("忻州五台山机场 (4C)", 112.965, 38.595, 25, 12, "left"),
        ("吕梁大武机场 (4C)", 111.145, 37.675, -25, 12, "right")
    ]
    for aname, alon, alat, ox, oy, ha in airports:
        ax_pt, ay_pt = to_alb(alon, alat)
        ax.plot(ax_pt, ay_pt, "P", color="#c0392b" if "武宿" in aname else "#1f618d",
                markersize=7.5 if "武宿" in aname else 6.0, markeredgecolor="white", markeredgewidth=0.8, zorder=12)
        ax.annotate(aname, xy=(ax_pt, ay_pt), xytext=(ox, oy), textcoords="offset points",
                    ha=ha, va="center", fontsize=6.8, fontweight="bold",
                    color="#78281f" if "武宿" in aname else "#154360", zorder=13,
                    path_effects=[pe.withStroke(linewidth=2.0, foreground="#ffffff")],
                    arrowprops=dict(arrowstyle="->", color="#7f8c8d", lw=0.5))

    # 标题与排版
    ax.set_title("山西省综合立体交通网与能源大通道图", fontsize=13.0, fontweight="bold", color=C_TEXT, pad=20)
    ax.text(0.5, 1.015, "Integrated Multi-Modal Transport Network & Energy Corridors of Shanxi",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=8.0, color="#555555")

    # 罗盘与比例尺
    add_compass(ax, x=0.94, y=0.92)
    add_scalebar(ax, ax_xlim[0] + (ax_xlim[1] - ax_xlim[0]) * 0.05, ax_ylim[0] + (ax_ylim[1] - ax_ylim[0]) * 0.035, length_km=100)

    # 图例
    legend_elements = [
        Line2D([0], [0], color="#641e16", lw=3.0, label="国家重载能源铁路 (大秦/朔黄/瓦日/侯月)"),
        Line2D([0], [0], color="#1f618d", lw=2.5, ls="--", label="高速铁路与客运专线 (大西/郑太/石太)"),
        Line2D([0], [0], color="#d35400", lw=1.8, label="国家骨干高速公路 (G55/G5/G20/G59)"),
        Line2D([0], [0], marker="P", color="w", markerfacecolor="#c0392b", markersize=8, label="国际干线机场 (太原武宿)"),
        Line2D([0], [0], marker="P", color="w", markerfacecolor="#1f618d", markersize=6.5, label="区域支线运输机场 (6座)")
    ]
    leg = ax.legend(handles=legend_elements, loc="lower right", fontsize=7.0, framealpha=0.92,
                    title="综合交通图例", title_fontsize=7.6)
    leg.set_zorder(20)

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")
    out_path = os.path.join(OUT_DIR, "fig04-00-3_山西省综合立体交通网与能源大通道图.png")
    plt.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close()
    print(f"Saved: {out_path}")

# =============================================================================
# 4. fig04-00-4_山西省产业经济与综合能源基地分布图
# =============================================================================
def gen_fig4():
    print("Generating fig04-00-4_山西省产业经济与综合能源基地分布图.png...")
    fig, ax = plt.subplots(figsize=(9.6, 11.2), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    draw_neighbor_context(ax)

    # 11市 2024 年 GDP (现价，亿元)
    gdp_data = {
        "太原市": 5419.0,
        "吕梁市": 2643.0,
        "长治市": 2593.0,
        "晋中市": 2459.0,
        "临汾市": 2439.0,
        "晋城市": 2410.0,
        "运城市": 2191.0,
        "大同市": 1802.0,
        "忻州市": 1343.0,
        "朔州市": 1329.0,
        "阳泉市": 856.0
    }
    norm_gdp = Normalize(vmin=800, vmax=5500)
    cmap_gdp = plt.cm.YlOrRd

    for _, row in sx_cities.iterrows():
        cname = row.get("name", "")
        val = gdp_data.get(cname, 1500.0)
        color = cmap_gdp(norm_gdp(val))
        gpd.GeoSeries([row.geometry]).plot(ax=ax, facecolor=color, edgecolor="#5d6d7e", lw=0.8, alpha=0.85, zorder=4)

    # 标注各市 2024 GDP 核心标签
    city_gdp_offsets = {
        "太原市": (112.50, 37.90),
        "大同市": (113.30, 40.10),
        "朔州市": (112.40, 39.35),
        "忻州市": (112.75, 38.50),
        "阳泉市": (113.55, 37.85),
        "晋中市": (112.75, 37.55),
        "长治市": (113.10, 36.35),
        "晋城市": (112.85, 35.50),
        "临汾市": (111.50, 36.15),
        "运城市": (111.00, 35.10),
        "吕梁市": (111.10, 37.40)
    }
    for cname, (glon, glat) in city_gdp_offsets.items():
        gx, gy = to_alb(glon, glat)
        val = gdp_data.get(cname, 1500.0)
        ax.text(gx, gy, f"{cname}\n{val:.1f} 亿元", ha="center", va="center",
                fontsize=7.2, fontweight="bold", color="#1a252f", zorder=13,
                path_effects=[pe.withStroke(linewidth=2.0, foreground="#ffffff")])

    # 关键能源基地与特色制造产业极核
    energy_tech_bases = [
        ("大同弱粘动力煤基地与绿色算力港", 113.20, 40.20, "energy", -35, 18, "right"),
        ("平朔安太堡露天煤矿 (中国最大露天煤矿)", 112.35, 39.50, "energy", -35, 18, "right"),
        ("太钢不锈高端手撕钢基地", 112.58, 38.00, "tech", 35, 15, "left"),
        ("晋中吉利甲醇新能源汽车工厂", 112.70, 37.65, "tech", 35, -15, "left"),
        ("离柳优质炼焦煤基地 (吕梁)", 111.00, 37.55, "energy", -35, 15, "right"),
        ("汾阳杏花村清香汾酒白酒之都", 111.75, 37.25, "ind", 35, 12, "left"),
        ("沁水百亿方煤层气与无烟煤示范基地", 112.70, 35.70, "energy", 35, -15, "left"),
        ("潞安煤基高端费托合成油与合成蜡", 113.05, 36.20, "tech", 35, 15, "left"),
        ("定襄国家级锻造法兰产业集群", 112.95, 38.50, "ind", 35, 15, "left"),
        ("阳泉华阳钠离子电池全产业链基地", 113.60, 37.95, "tech", 35, 15, "left"),
        ("运城大运新能源汽车工业园", 111.05, 35.15, "tech", -35, -15, "right")
    ]
    style_dict = {
        "energy": ("#78281f", "s", 6.8, "国家综合能源基地 (煤炭/煤层气)"),
        "tech": ("#1f618d", "D", 6.8, "先进制造与高新产业 (特钢/甲醇汽车/算力)"),
        "ind": ("#196f3d", "o", 6.5, "国家地理标志与特色优势集群 (汾酒/法兰)")
    }

    for bname, blon, blat, btype, ox, oy, ha in energy_tech_bases:
        bx, by = to_alb(blon, blat)
        mcolor, msym, msize, _ = style_dict[btype]
        ax.plot(bx, by, msym, color=mcolor, markersize=msize, markeredgecolor="white", markeredgewidth=0.7, zorder=12)
        ax.annotate(bname, xy=(bx, by), xytext=(ox, oy), textcoords="offset points",
                    ha=ha, va="center", fontsize=6.8, fontweight="bold", color=mcolor, zorder=14,
                    path_effects=[pe.withStroke(linewidth=2.0, foreground="#ffffff")],
                    arrowprops=dict(arrowstyle="->", color=mcolor, lw=0.6))

    gpd.GeoSeries([sx_union]).boundary.plot(ax=ax, color="#1a252f", lw=1.3, zorder=7)

    # 标题与排版
    ax.set_title("山西省产业经济与综合能源基地分布图", fontsize=13.0, fontweight="bold", color=C_TEXT, pad=20)
    ax.text(0.5, 1.015, "Industrial Economy & National Comprehensive Energy Bases in Shanxi",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=8.0, color="#555555")

    # 罗盘与比例尺
    add_compass(ax, x=0.94, y=0.92)
    add_scalebar(ax, ax_xlim[0] + (ax_xlim[1] - ax_xlim[0]) * 0.05, ax_ylim[0] + (ax_ylim[1] - ax_ylim[0]) * 0.035, length_km=100)

    # GDP 色带图例
    cax = ax.inset_axes([0.05, 0.08, 0.025, 0.22])
    cb = plt.colorbar(plt.cm.ScalarMappable(norm=norm_gdp, cmap=cmap_gdp), cax=cax, orientation="vertical")
    cb.set_label("2024 年 GDP (亿元)", fontsize=6.8, color="#2c3e50")
    cb.ax.tick_params(labelsize=6.0, length=2.2)

    # 要素图例
    legend_elements = [
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#78281f", markersize=7.5, label="国家重点能源保供基地"),
        Line2D([0], [0], marker="D", color="w", markerfacecolor="#1f618d", markersize=7.0, label="先进制造与战略新兴产业"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#196f3d", markersize=6.5, label="特色优势与非遗产业集群")
    ]
    leg = ax.legend(handles=legend_elements, loc="lower right", fontsize=7.0, framealpha=0.92,
                    title="产业类型图例", title_fontsize=7.6)
    leg.set_zorder(20)

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")
    out_path = os.path.join(OUT_DIR, "fig04-00-4_山西省产业经济与综合能源基地分布图.png")
    plt.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close()
    print(f"Saved: {out_path}")

# =============================================================================
# 5. fig04-00-5_山西省生态安全屏障与自然水系格局图
# =============================================================================
def gen_fig5():
    print("Generating fig04-00-5_山西省生态安全屏障与自然水系格局图.png...")
    fig, ax = plt.subplots(figsize=(9.6, 11.2), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    draw_neighbor_context(ax)

    # 底色与省界
    sx_cities.plot(ax=ax, facecolor="#f4f6f7", edgecolor="#bdc3c7", lw=0.6, zorder=3)
    gpd.GeoSeries([sx_union]).boundary.plot(ax=ax, color="#2c3e50", lw=1.3, zorder=4)

    # 1. 黄河流域与海河流域两大分水岭示意边界 (大致沿太行山西侧山脊与大同/忻州界线展布)
    watershed_line = [
        (114.2, 40.4), (113.8, 39.8), (113.5, 39.1), (112.8, 38.3),
        (112.7, 37.3), (113.0, 36.5), (113.2, 35.8), (113.4, 35.3)
    ]
    w_pts = [to_alb(p[0], p[1]) for p in watershed_line]
    ax.plot([p[0] for p in w_pts], [p[1] for p in w_pts], color="#7d3c98", lw=2.2, ls="-.", zorder=5)
    ax.text(w_pts[4][0] + 8000, w_pts[4][1], "黄河 / 海河流域主分水岭\n(黄河 62.2% : 海河 37.8%)",
            fontsize=7.2, fontweight="bold", color="#5b2c6f", zorder=15,
            bbox=dict(boxstyle="round,pad=0.2", facecolor="#f4ecf7", edgecolor="#af7ac5", alpha=0.9),
            path_effects=[pe.withStroke(linewidth=1.8, foreground="#ffffff")])

    # 2. 骨干河流水系走向（黄河、汾河、桑干河、滹沱河、清浊漳河、沁河）
    river_paths = [
        ("黄河 (晋陕大峡谷段·出境 180m)", [(111.45, 39.60), (110.85, 38.50), (110.45, 37.50), (110.45, 36.15), (110.35, 35.10), (110.28, 34.60), (111.50, 34.70)], "#1a5276", 3.2),
        ("汾河 (三晋母亲河·全长 716km)", [(111.90, 38.80), (112.00, 38.10), (112.50, 37.85), (112.35, 37.40), (111.85, 36.80), (111.50, 36.10), (111.20, 35.60), (110.40, 35.50)], "#2980b9", 2.6),
        ("桑干河 (永定河正源)", [(112.35, 39.40), (113.00, 39.70), (113.60, 40.00), (114.20, 40.30)], "#2471a3", 2.0),
        ("滹沱河", [(113.60, 39.20), (113.00, 38.70), (112.70, 38.40), (113.40, 38.20), (113.80, 38.10)], "#2471a3", 2.0),
        ("沁河", [(112.20, 36.80), (112.30, 36.20), (112.60, 35.70), (112.75, 35.20)], "#2980b9", 2.0),
        ("浊漳河", [(112.80, 36.50), (113.10, 36.30), (113.50, 36.20), (113.80, 36.15)], "#2471a3", 2.0)
    ]
    for rname, rpts, rcolor, rlw in river_paths:
        palb = [to_alb(p[0], p[1]) for p in rpts]
        xs, ys = mapkit.smooth_line(palb)
        ax.plot(xs, ys, color=rcolor, lw=rlw, ls="-", zorder=6)
        mid_idx = len(xs) // 2
        ax.text(xs[mid_idx] + 6000, ys[mid_idx] + 4000, rname.split("(")[0].strip(),
                fontsize=7.2, fontweight="bold", color=rcolor, zorder=14,
                path_effects=[pe.withStroke(linewidth=1.8, foreground="#ffffff")])

    # 3. 超级引水工程：万家寨引黄入晋工程（南干线入太原汾河水库、北干线入大同平旺水库）
    wjz_pt = (111.45, 39.58)  # 万家寨
    ty_res_pt = (111.85, 38.10) # 汾河水库
    dt_res_pt = (113.15, 40.05) # 大同
    wjz_alb = to_alb(wjz_pt[0], wjz_pt[1])
    ty_alb = to_alb(ty_res_pt[0], ty_res_pt[1])
    dt_alb = to_alb(dt_res_pt[0], dt_res_pt[1])

    # 绘制引黄输水管线（青色虚线带箭头）
    ax.plot([wjz_alb[0], ty_alb[0]], [wjz_alb[1], ty_alb[1]], color="#117864", lw=2.2, ls=":", zorder=8)
    ax.plot([wjz_alb[0], dt_alb[0]], [wjz_alb[1], dt_alb[1]], color="#117864", lw=2.2, ls=":", zorder=8)
    ax.text((wjz_alb[0] + ty_alb[0])/2 - 10000, (wjz_alb[1] + ty_alb[1])/2, "引黄入晋·南干线 (输水太原)",
            fontsize=6.8, fontweight="bold", color="#0e6251", zorder=15, ha="right",
            path_effects=[pe.withStroke(linewidth=1.8, foreground="#ffffff")])
    ax.text((wjz_alb[0] + dt_alb[0])/2, (wjz_alb[1] + dt_alb[1])/2 + 8000, "引黄入晋·北干线 (输水大同)",
            fontsize=6.8, fontweight="bold", color="#0e6251", zorder=15, ha="center",
            path_effects=[pe.withStroke(linewidth=1.8, foreground="#ffffff")])

    # 4. 生态安全屏障区标注
    eco_barriers = [
        ("太行山森林与水源涵养生态屏障", 113.70, 36.80),
        ("吕梁山水土保持与水源涵养屏障", 111.35, 37.85),
        ("塞外绿洲右玉生态修复示范区", 112.45, 40.00),
        ("中条山—历山森林生物多样性保护区", 111.85, 35.30),
        ("“一泓清水入黄河”汾河百里生态走廊", 112.00, 36.70)
    ]
    for bname, blon, blat in eco_barriers:
        bx, by = to_alb(blon, blat)
        ax.text(bx, by, bname, ha="center", va="center", fontsize=7.4, fontweight="bold",
                color="#196f3d", zorder=12,
                bbox=dict(boxstyle="round,pad=0.25", facecolor="#e8f8f5", edgecolor="#27ae60", alpha=0.9),
                path_effects=[pe.withStroke(linewidth=1.8, foreground="#ffffff")])

    # 5. 控制性水利枢纽与湿地水库
    water_hubs = [
        ("万家寨水利枢纽 (引黄龙头)", 111.45, 39.58, -30, 15, "right"),
        ("汾河水库 (太原水源地)", 111.85, 38.10, -30, 15, "right"),
        ("册田水库 (大同水源地)", 113.63, 40.01, 30, 15, "left"),
        ("漳泽水库 (长治水系核心)", 113.08, 36.32, 30, 15, "left"),
        ("后湾水库 (阳泉/晋中重要节点)", 113.38, 37.60, 30, 12, "left"),
        ("运城解池盐湖生态湿地", 110.98, 35.00, 30, -18, "left")
    ]
    for hname, hlon, hlat, ox, oy, ha in water_hubs:
        hx, hy = to_alb(hlon, hlat)
        ax.plot(hx, hy, "p", color="#117864", markersize=6.8, markeredgecolor="white", markeredgewidth=0.7, zorder=12)
        ax.annotate(hname, xy=(hx, hy), xytext=(ox, oy), textcoords="offset points",
                    ha=ha, va="center", fontsize=6.8, fontweight="bold", color="#0e6251", zorder=14,
                    path_effects=[pe.withStroke(linewidth=2.0, foreground="#ffffff")],
                    arrowprops=dict(arrowstyle="->", color="#117864", lw=0.6))

    # 标题与排版
    ax.set_title("山西省生态安全屏障与自然水系格局图", fontsize=13.0, fontweight="bold", color=C_TEXT, pad=20)
    ax.text(0.5, 1.015, "Ecological Security Barriers and Natural Hydrological Pattern of Shanxi",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=8.0, color="#555555")

    # 罗盘与比例尺
    add_compass(ax, x=0.94, y=0.92)
    add_scalebar(ax, ax_xlim[0] + (ax_xlim[1] - ax_xlim[0]) * 0.05, ax_ylim[0] + (ax_ylim[1] - ax_ylim[0]) * 0.035, length_km=100)

    # 图例
    legend_elements = [
        Line2D([0], [0], color="#1a5276", lw=3.0, label="黄河干流及主要支流 (汾河/沁河等)"),
        Line2D([0], [0], color="#2471a3", lw=2.0, label="海河流域骨干河流 (桑干河/滹沱河/漳河)"),
        Line2D([0], [0], color="#7d3c98", lw=2.2, ls="-.", label="黄河 / 海河流域主分水岭"),
        Line2D([0], [0], color="#117864", lw=2.2, ls=":", label="万家寨引黄入晋生命输水大通道"),
        Line2D([0], [0], marker="p", color="w", markerfacecolor="#117864", markersize=7.5, label="重点水利枢纽与大型水库湿地")
    ]
    leg = ax.legend(handles=legend_elements, loc="lower right", fontsize=7.0, framealpha=0.92,
                    title="水系生态图例", title_fontsize=7.6)
    leg.set_zorder(20)

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")
    out_path = os.path.join(OUT_DIR, "fig04-00-5_山西省生态安全屏障与自然水系格局图.png")
    plt.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close()
    print(f"Saved: {out_path}")

if __name__ == "__main__":
    gen_fig1()
    gen_fig2()
    gen_fig3()
    gen_fig4()
    gen_fig5()
    print("All 5 overview maps for Shanxi completed successfully!")
