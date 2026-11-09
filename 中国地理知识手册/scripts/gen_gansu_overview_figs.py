# -*- coding: utf-8 -*-
"""甘肃省地理统揽专题地图生成引擎（30-00）
包含 5 幅全省域权威地图与分析图表（精细调优排版、微缩字号、严格杜绝压盖、要素清晰呼应）：
1. fig30-00-1_甘肃省地形地貌与四大高原地理交汇格局图.png
2. fig30-00-2_甘肃省行政区划与城镇空间骨架图.png
3. fig30-00-3_甘肃省综合立体交通网与丝路大通道图.png
4. fig30-00-4_甘肃省产业经济与新能源绿色算力布局图.png
5. fig30-00-5_甘肃省生态安全屏障与三大内陆河水系格局图.png
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

def add_scalebar(ax, x0, y0, length_km=150):
    mapkit.add_scalebar(ax, x0, y0, length_km=length_km)

def add_compass(ax, x=0.94, y=0.92):
    ax.annotate("N", xy=(x, y), xytext=(x, y - 0.055), transform=ax.transAxes,
                arrowprops=dict(facecolor="#2c3e50", edgecolor="#2c3e50", width=1.8, headwidth=5.5, headlength=6.5),
                ha="center", va="center", fontsize=8.8, fontweight="bold", color="#2c3e50", zorder=30)

print("Loading Gansu provincial spatial data...")
DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
gs_cities = gpd.read_file(os.path.join(DATA_DIR, "boundaries", "datav", "620000_full.json")).to_crs(ALBERS)
gs_union = gs_cities.union_all()
bb = gs_cities.total_bounds

# 视口与中心计算：甘肃呈西北-东南狭长“玉如意”形态
span_x = bb[2] - bb[0]
span_y = bb[3] - bb[1]
pad_x = span_x * 0.06
pad_y = span_y * 0.06
ax_xlim = (bb[0] - pad_x, bb[2] + pad_x)
ax_ylim = (bb[1] - pad_y, bb[3] + pad_y)

# 加载 DEM
print("Loading Gansu DEM...")
dem_gs, dem_minx, dem_maxy, dem_res = prov_dem("620000", zoom=9, res=300.0)

# =============================================================================
# 1. 地形地貌与四大高原地理交汇格局图 (fig30-00-1)
# =============================================================================
def gen_fig1():
    print("Generating fig30-00-1 (Topography)...")
    fig, ax = plt.subplots(figsize=(12.0, 8.8), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    hs = calc_hillshade(dem_gs, dem_res)
    colors = [
        (0.00, "#a9dfbf"),   # 陇南河谷暖绿
        (0.10, "#d4efdf"),
        (0.25, "#f9e79f"),   # 河西走廊/黄土高原暖黄
        (0.45, "#edbb99"),   # 丘陵中山棕褐
        (0.68, "#ba4a00"),   # 祁连山中高山深褐
        (0.85, "#a04000"),   # 高寒雪线
        (1.00, "#fdfefe")    # 祁连冰川极顶白
    ]
    cmap = LinearSegmentedColormap.from_list("gs_elev", colors, N=256)
    norm = Normalize(vmin=500.0, vmax=5500.0)

    valid = np.nan_to_num(dem_gs, nan=500.0)
    valid = np.clip(valid, 500.0, 5500.0)
    rgb = cmap(norm(valid))[:, :, :3]
    rgb_shaded = rgb * (0.42 + 0.58 * hs[:, :, np.newaxis])

    dem_extent = (dem_minx, dem_minx + dem_gs.shape[1] * dem_res,
                  dem_maxy - dem_gs.shape[0] * dem_res, dem_maxy)
    im = ax.imshow(rgb_shaded, extent=dem_extent, origin="upper", zorder=3)
    patch = get_mpl_clip_patch(gs_union)
    ax.add_patch(patch)
    im.set_clip_path(patch)

    gs_cities.boundary.plot(ax=ax, color="#34495e", lw=0.6, ls=":", zorder=5)
    gpd.GeoSeries([gs_union]).boundary.plot(ax=ax, color="#1a252f", lw=1.5, zorder=6)

    # 地理四大交汇单元与核心山脉大地貌标注
    macro_labels = [
        ("青 藏 高 原 东 北 缘", 101.5, 34.2, 0, 11.5, "#78281f"),
        ("黄 土 高 原 陇 中 / 陇 东", 106.5, 36.0, 0, 11.5, "#7d6608"),
        ("内 蒙 古 高 原 南 缘", 101.8, 39.8, 0, 11.0, "#935116"),
        ("河 西 走 廊 千 里 绿 洲", 98.8, 39.5, -28, 12.0, "#145a32"),
        ("祁 连 山 脉 (坚实固体水库)", 99.2, 38.6, -26, 11.0, "#1b4f72"),
        ("阿尔金山脉东段", 93.2, 39.2, -15, 9.5, "#1b4f72"),
        ("马 衔 山", 104.0, 35.7, 0, 8.5, "#4a235a"),
        ("六 盘 山", 106.3, 35.5, 75, 8.8, "#4a235a"),
        ("西 秦 岭 / 白龙江大峡谷", 104.8, 33.2, 0, 9.5, "#145a32"),
        ("子 午 岭 林 区", 108.3, 36.2, 80, 8.8, "#145a32")
    ]
    for text, lon, lat, rot, sz, col in macro_labels:
        x, y = to_alb(lon, lat)
        ax.text(x, y, text, fontsize=sz, fontweight="bold", color=col, rotation=rot,
                ha="center", va="center", zorder=12,
                path_effects=[pe.withStroke(linewidth=2.8, foreground="#ffffff")])

    # 极值点注记
    extremes = [
        ("团结峰 5808m (甘肃全省最高峰)", 97.355, 38.515, "^", "#b03a2e", (180, 110), "right"),
        ("文县白龙江出境处 550m (全省最低点)", 105.385, 32.745, "v", "#27ae60", (160, -90), "right"),
        ("马踏飞燕雷台汉墓", 102.635, 37.945, "o", "#8e44ad", (140, 80), "left"),
        ("天下第一雄关·嘉峪关", 98.215, 39.815, "s", "#d35400", (-160, 90), "left"),
        ("世界文化遗产·敦煌莫高窟", 94.805, 40.045, "*", "#c0392b", (-180, 80), "left")
    ]
    for name, lon, lat, marker, mcolor, (ox, oy), side in extremes:
        px, py = to_alb(lon, lat)
        ax.plot(px, py, marker, color=mcolor, markersize=6.5, zorder=15)
        ha = "left" if side == "left" else "right"
        ax.annotate(name, xy=(px, py), xytext=(px + ox * 1000, py + oy * 1000),
                    arrowprops=dict(arrowstyle="-", color="#7f8c8d", lw=0.7),
                    fontsize=7.8, fontweight="bold", color="#1c2833", ha=ha, va="center", zorder=16,
                    path_effects=[pe.withStroke(linewidth=2.2, foreground="#ffffff")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    add_scalebar(ax, ax_xlim[0] + span_x * 0.08, ax_ylim[0] + span_y * 0.08, length_km=150)
    add_compass(ax, 0.94, 0.92)

    cax = ax.inset_axes([0.08, 0.16, 0.02, 0.28])
    cb = plt.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cax, orientation="vertical")
    cb.set_label("高程 Elevation (m)", fontsize=7.2, color="#2c3e50")
    cb.ax.tick_params(labelsize=6.5, length=2.0)

    ax.set_title("甘肃省地形地貌与四大高原地理交汇格局图", fontsize=13.0, fontweight="bold", pad=20, color=C_TEXT)
    ax.text(0.5, 1.008, "Geomorphic Framework & Crossroads of Four Plateaus in Gansu Province",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=8.0, color="#7f8c8d")
    fig.text(0.5, 0.015, "数据源：AWS Terrain GLO-30 30m DEM · 投影：Albers 等积圆锥 · 制作：《中国地理知识手册》",
             ha="center", va="bottom", fontsize=7.0, color="#7f8c8d")

    out_p = os.path.join(OUT_DIR, "fig30-00-1_甘肃省地形地貌与四大高原地理交汇格局图.png")
    fig.savefig(out_p, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_p}")

# =============================================================================
# 2. 行政区划与城镇空间骨架图 (fig30-00-2)
# =============================================================================
def gen_fig2():
    print("Generating fig30-00-2 (Administrative & Urban Framework)...")
    fig, ax = plt.subplots(figsize=(12.0, 8.8), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    # 14 市州配色底图
    PALETTE = [
        "#f9ebea", "#fef5e7", "#fef9e7", "#eafaf1", "#e8f8f5",
        "#ebf5fb", "#eaf2f8", "#f4ecf7", "#fdedec", "#f5eef8",
        "#e8f6f3", "#fcf3cf", "#d5f5e3", "#d6eaf8"
    ]
    gs_cities["color"] = [PALETTE[i % len(PALETTE)] for i in range(len(gs_cities))]
    gs_cities.plot(ax=ax, color=gs_cities["color"], edgecolor="#7f8c8d", lw=0.8, zorder=3)
    gpd.GeoSeries([gs_union]).boundary.plot(ax=ax, color="#1a252f", lw=1.8, zorder=6)

    # 标注 14 市州中心与名称
    for idx, row in gs_cities.iterrows():
        name = row["name"]
        center = row.geometry.representative_point()
        cx, cy = center.x, center.y
        ax.text(cx, cy, name, fontsize=8.8, fontweight="bold", color="#1a5276",
                ha="center", va="center", zorder=12,
                path_effects=[pe.withStroke(linewidth=2.2, foreground="#ffffff")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    add_scalebar(ax, ax_xlim[0] + span_x * 0.08, ax_ylim[0] + span_y * 0.08, length_km=150)
    add_compass(ax, 0.94, 0.92)

    ax.set_title("甘肃省行政区划与城镇空间骨架图", fontsize=13.0, fontweight="bold", pad=20, color=C_TEXT)
    ax.text(0.5, 1.008, "Administrative Divisions & Urban Spatial Hierarchy of Gansu Province (12 Cities & 2 Prefectures)",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=8.0, color="#7f8c8d")
    fig.text(0.5, 0.015, "数据源：自然资源部标准地图与阿里云 DataV 行政矢量 · 制作：《中国地理知识手册》",
             ha="center", va="bottom", fontsize=7.0, color="#7f8c8d")

    out_p = os.path.join(OUT_DIR, "fig30-00-2_甘肃省行政区划与城镇空间骨架图.png")
    fig.savefig(out_p, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_p}")

# =============================================================================
# 3. 综合立体交通网与丝路大通道图 (fig30-00-3)
# =============================================================================
def gen_fig3():
    print("Generating fig30-00-3 (Transport Corridor)...")
    fig, ax = plt.subplots(figsize=(12.0, 8.8), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    gs_cities.plot(ax=ax, facecolor="#fdfefe", edgecolor="#bdc3c7", lw=0.7, zorder=3)
    gpd.GeoSeries([gs_union]).boundary.plot(ax=ax, color="#2c3e50", lw=1.5, zorder=5)

    # 绘制主要干线走向 (连线关键节点示意骨架)
    # 兰新高铁 / 宝兰高铁
    hspeed_pts = [
        (105.865, 34.545), (104.605, 35.595), (103.745, 36.075), (103.625, 36.515),
        (102.685, 37.925), (101.425, 38.165), (100.425, 38.965), (98.315, 39.745),
        (98.535, 39.705), (97.045, 39.815), (95.505, 41.105)
    ]
    hx, hy = mapkit.smooth_line([to_alb(p[0], p[1]) for p in hspeed_pts])
    ax.plot(hx, hy, color="#c0392b", lw=2.5, ls="-", zorder=8, label="兰新高铁 / 宝兰高铁 (丝路客专)")

    # 银西高铁
    yx_pts = [(107.335, 36.565), (107.855, 36.035), (107.675, 35.755)]
    yx_x, yx_y = mapkit.smooth_line([to_alb(p[0], p[1]) for p in yx_pts])
    ax.plot(yx_x, yx_y,
            color="#e74c3c", lw=2.2, ls="--", zorder=8, label="银西高铁大通道")

    # 兰渝铁路 (向南出川)
    ly_pts = [(103.745, 36.075), (104.055, 34.425), (104.285, 34.225), (104.915, 33.385)]
    ly_x, ly_y = mapkit.smooth_line([to_alb(p[0], p[1]) for p in ly_pts])
    ax.plot(ly_x, ly_y,
            color="#27ae60", lw=2.2, ls="-", zorder=8, label="兰渝铁路 (南下陆海新通道)")

    # 敦格铁路 / 敦煌铁路
    dg_pts = [(95.505, 41.105), (94.775, 40.165), (94.335, 39.635)]
    dg_x, dg_y = mapkit.smooth_line([to_alb(p[0], p[1]) for p in dg_pts])
    ax.plot(dg_x, dg_y,
            color="#2980b9", lw=2.0, ls="-.", zorder=8, label="敦格铁路 / 敦煌铁路")

    # 机场枢纽标注
    airports = [
        ("中川国际机场 (4E级枢纽)", 103.625, 36.515),
        ("敦煌莫高国际机场 (4D)", 94.815, 40.165),
        ("嘉峪关酒泉机场 (4D)", 98.345, 39.855),
        ("庆阳西峰机场", 107.705, 35.805),
        ("金昌金川机场", 102.355, 38.545),
        ("张掖甘州机场", 100.675, 38.815),
        ("陇南成县机场", 105.795, 33.785),
        ("甘南夏河机场", 102.635, 34.815),
        ("天水麦积山机场", 105.865, 34.565)
    ]
    for aname, alon, alat in airports:
        ax_pt, ay_pt = to_alb(alon, alat)
        ax.plot(ax_pt, ay_pt, "^", color="#1f618d", markersize=7.0, zorder=15)
        ax.annotate(aname, xy=(ax_pt, ay_pt), xytext=(ax_pt + 8000, ay_pt + 6000),
                    fontsize=7.2, fontweight="bold", color="#4a235a", zorder=16,
                    path_effects=[pe.withStroke(linewidth=2.0, foreground="#ffffff")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    add_scalebar(ax, ax_xlim[0] + span_x * 0.08, ax_ylim[0] + span_y * 0.08, length_km=150)
    add_compass(ax, 0.94, 0.92)

    leg = ax.legend(loc="upper left", bbox_to_anchor=(0.04, 0.96), fontsize=7.8,
                    framealpha=0.92, facecolor="#ffffff", edgecolor="#bdc3c7")

    ax.set_title("甘肃省综合立体交通网与丝路大通道图", fontsize=13.0, fontweight="bold", pad=20, color=C_TEXT)
    ax.text(0.5, 1.008, "Comprehensive Transportation Network & Silk Road Corridors of Gansu Province",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=8.0, color="#7f8c8d")
    fig.text(0.5, 0.015, "数据源：甘肃省综合立体交通网规划纲要 · 制作：《中国地理知识手册》",
             ha="center", va="bottom", fontsize=7.0, color="#7f8c8d")

    out_p = os.path.join(OUT_DIR, "fig30-00-3_甘肃省综合立体交通网与丝路大通道图.png")
    fig.savefig(out_p, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_p}")

# =============================================================================
# 4. 现代产业经济与新能源绿色算力布局图 (fig30-00-4)
# =============================================================================
def gen_fig4():
    print("Generating fig30-00-4 (Economy & Clean Energy)...")
    fig, ax = plt.subplots(figsize=(12.0, 8.8), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    gs_cities.plot(ax=ax, facecolor="#f8f9fa", edgecolor="#95a5a6", lw=0.7, zorder=3)
    gpd.GeoSeries([gs_union]).boundary.plot(ax=ax, color="#2c3e50", lw=1.5, zorder=5)

    # 标志性重大现代产业项目
    industries = [
        ("全国一体化算力网络·国家数据中心甘肃庆阳集群", 107.685, 35.765, "s", "#8e44ad", (140, 80), "left"),
        ("酒泉千万千瓦级陆上风电大基地", 96.125, 40.455, "^", "#27ae60", (-160, 90), "left"),
        ("敦煌首航百兆瓦级熔盐塔式光热电站", 94.515, 40.215, "o", "#e67e22", (-180, -90), "left"),
        ("金川集团世界级镍钴精炼与新材料基地", 102.145, 38.485, "D", "#2980b9", (120, 80), "left"),
        ("酒钢集团宏丰碳钢薄板与高端不锈钢", 98.295, 39.805, "D", "#d35400", (-140, 90), "left"),
        ("白银有色稀土与铜铅锌循环经济园区", 104.155, 36.565, "D", "#16a085", (120, 80), "left"),
        ("兰州石化现代百万吨乙烯精细化工群", 103.615, 36.115, "s", "#c0392b", (-160, -90), "left"),
        ("天水华天科技全球集成电路封测基地", 105.765, 34.565, "s", "#154360", (120, -80), "left"),
        ("张掖全国最大国家级杂交玉米制种基地", 100.325, 39.155, "o", "#f39c12", (100, 70), "left"),
        ("定西‘中国薯都’与脱毒种薯全粉主食化", 104.625, 35.565, "o", "#d4ac0d", (120, 70), "left"),
        ("陇南武都‘中国油橄榄之乡’特级初榨基地", 104.925, 33.425, "o", "#196f3d", (120, -70), "left"),
        ("长庆油田陇东页岩油十亿吨级大油田", 107.725, 35.855, "^", "#78281f", (120, -70), "left")
    ]

    for iname, ilon, ilat, marker, mcolor, (ox, oy), side in industries:
        ix, iy = to_alb(ilon, ilat)
        ax.plot(ix, iy, marker, color=mcolor, markersize=7.0, zorder=12)
        ha = "left" if side == "left" else "right"
        ax.annotate(iname, xy=(ix, iy), xytext=(ix + ox * 1000, iy + oy * 1000),
                    arrowprops=dict(arrowstyle="->", color="#7f8c8d", lw=0.8),
                    fontsize=7.8, fontweight="bold", color="#1c2833", ha=ha, va="center", zorder=15,
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="#ffffff", edgecolor=mcolor, alpha=0.9))

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    add_scalebar(ax, ax_xlim[0] + span_x * 0.08, ax_ylim[0] + span_y * 0.08, length_km=150)
    add_compass(ax, 0.94, 0.92)

    ax.set_title("甘肃省现代产业经济与新能源绿色算力布局图", fontsize=13.0, fontweight="bold", pad=20, color=C_TEXT)
    ax.text(0.5, 1.008, "Industrial Layout, Renewable Energy & National Green Computing Hub of Gansu Province",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=8.0, color="#7f8c8d")
    fig.text(0.5, 0.015, "数据源：甘肃省国民经济和社会发展第十四个五年规划纲要 · 制作：《中国地理知识手册》",
             ha="center", va="bottom", fontsize=7.0, color="#7f8c8d")

    out_p = os.path.join(OUT_DIR, "fig30-00-4_甘肃省产业经济与新能源绿色算力布局图.png")
    fig.savefig(out_p, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_p}")

# =============================================================================
# 5. 生态安全屏障与三大内陆河水系格局图 (fig30-00-5)
# =============================================================================
def gen_fig5():
    print("Generating fig30-00-5 (Ecology & River Basins)...")
    fig, ax = plt.subplots(figsize=(12.0, 8.8), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    gs_cities.plot(ax=ax, facecolor="#fdfefe", edgecolor="#bdc3c7", lw=0.6, zorder=3)
    gpd.GeoSeries([gs_union]).boundary.plot(ax=ax, color="#1b4f72", lw=1.6, zorder=5)

    # 核心水系与生态工程
    eco_elements = [
        ("祁连山国家公园核心区 (河西固体水库)", 99.8, 38.7, "#1b4f72", 11.0),
        ("玛曲黄河首曲湿地 (黄河水源最大补给区)", 102.1, 33.9, "#154360", 9.8),
        ("民勤青土湖防沙生态林带 (阻隔双沙闭合)", 103.4, 38.9, "#196f3d", 9.5),
        ("白水江大熊猫国家级自然保护区", 104.8, 32.9, "#145a32", 9.5),
        ("石羊河流域绿洲带", 102.7, 38.3, "#2980b9", 9.5),
        ("黑河流域九次分水生态调水走廊", 100.2, 39.2, "#2471a3", 10.0),
        ("疏勒河古终端与敦煌西湖国家级湿地", 94.2, 40.2, "#2e86c1", 9.5),
        ("黄河干流 900 公里甘肃段峡谷与水库群", 103.5, 36.1, "#154360", 10.0),
        ("刘家峡大型水利枢纽水库", 103.32, 35.94, "#1f618d", 8.8)
    ]

    for ename, elon, elat, ecol, esz in eco_elements:
        ex, ey = to_alb(elon, elat)
        ax.plot(ex, ey, "o", color=ecol, markersize=5.5, zorder=12)
        ax.text(ex, ey + 8000, ename, fontsize=esz, fontweight="bold", color=ecol,
                ha="center", va="bottom", zorder=14,
                path_effects=[pe.withStroke(linewidth=2.5, foreground="#ffffff")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    add_scalebar(ax, ax_xlim[0] + span_x * 0.08, ax_ylim[0] + span_y * 0.08, length_km=150)
    add_compass(ax, 0.94, 0.92)

    ax.set_title("甘肃省生态安全屏障与三大内陆河水系格局图", fontsize=13.0, fontweight="bold", pad=20, color=C_TEXT)
    ax.text(0.5, 1.008, "Ecological Security Barriers & River Basin Systems of Gansu Province",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=8.0, color="#7f8c8d")
    fig.text(0.5, 0.015, "数据源：甘肃省水资源公报与祁连山国家公园规划 · 制作：《中国地理知识手册》",
             ha="center", va="bottom", fontsize=7.0, color="#7f8c8d")

    out_p = os.path.join(OUT_DIR, "fig30-00-5_甘肃省生态安全屏障与三大内陆河水系格局图.png")
    fig.savefig(out_p, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_p}")

if __name__ == "__main__":
    gen_fig1()
    gen_fig2()
    gen_fig3()
    gen_fig4()
    gen_fig5()
    print("\n✓ All 5 Gansu overview maps generated successfully!")
