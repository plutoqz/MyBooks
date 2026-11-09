# -*- coding: utf-8 -*-
"""新疆维吾尔自治区地理统揽专题地图生成引擎（32-00）
包含 5 幅全区域权威地图与分析图表（精细调优排版、微缩字号、严格杜绝压盖、要素清晰呼应）：
1. fig32-00-1_新疆维吾尔自治区地形地貌与三山夹两盆格局图.png
2. fig32-00-2_新疆维吾尔自治区行政区划与四大板块城镇空间骨架图.png
3. fig32-00-3_新疆维吾尔自治区综合立体交通网与亚欧陆桥走廊图.png
4. fig32-00-4_新疆维吾尔自治区现代产业体系与国家三基地一通道布局图.png
5. fig32-00-5_新疆维吾尔自治区生态安全屏障与内陆流域水系图.png
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

def add_scalebar(ax, x0, y0, length_km=200):
    mapkit.add_scalebar(ax, x0, y0, length_km=length_km)

def add_compass(ax, x=0.94, y=0.92):
    ax.annotate("N", xy=(x, y), xytext=(x, y - 0.055), transform=ax.transAxes,
                arrowprops=dict(facecolor="#2c3e50", edgecolor="#2c3e50", width=1.8, headwidth=5.5, headlength=6.5),
                ha="center", va="center", fontsize=8.8, fontweight="bold", color="#2c3e50", zorder=30)

print("Loading Xinjiang provincial spatial data...")
DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
xj_prov = gpd.read_file(os.path.join(DATA_DIR, "boundaries", "datav", "650000_full.json")).to_crs(ALBERS)
xj_union = xj_prov.union_all()
bb = xj_prov.total_bounds

span_x = bb[2] - bb[0]
span_y = bb[3] - bb[1]
pad_x = span_x * 0.05
pad_y = span_y * 0.05
ax_xlim = (bb[0] - pad_x, bb[2] + pad_x)
ax_ylim = (bb[1] - pad_y, bb[3] + pad_y)

# 加载并降采样 DEM 提高制图效率与清晰度
print("Loading Xinjiang DEM...")
dem_data = np.load(os.path.join(DATA_DIR, "dem", "province", "650000_z9.npz"))
step = 2
dem_raw = dem_data['dem'][::step, ::step]
dem_res = float(dem_data['res']) * step
dem_minx = float(dem_data['minx'])
dem_maxy = float(dem_data['maxy'])
print(f"Downsampled DEM shape: {dem_raw.shape}, res: {dem_res}m")

# =============================================================================
# 1. 地形地貌与三山夹两盆格局图 (fig32-00-1)
# =============================================================================
def gen_fig1():
    print("Generating fig32-00-1 (Topography)...")
    fig, ax = plt.subplots(figsize=(12.0, 9.2), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    hs = calc_hillshade(dem_raw, dem_res)
    colors = [
        (0.00, "#2980b9"),   # 艾丁湖极低洼地深蓝
        (0.02, "#a9dfbf"),   # 盆地边缘绿洲暖绿
        (0.12, "#f9e79f"),   # 塔里木/准噶尔沙漠戈壁暖黄
        (0.28, "#edbb99"),   # 山前台地缓坡
        (0.48, "#ba4a00"),   # 天山/昆仑/阿尔泰中高山
        (0.70, "#78281f"),   # 极高山雪线
        (1.00, "#fdfefe")    # 乔戈里峰极顶白
    ]
    cmap = LinearSegmentedColormap.from_list("xj_elev", colors, N=256)
    norm = Normalize(vmin=-160.0, vmax=8600.0)

    valid = np.nan_to_num(dem_raw, nan=-160.0)
    valid = np.clip(valid, -160.0, 8600.0)
    rgb = cmap(norm(valid))[:, :, :3]
    rgb_shaded = rgb * (0.42 + 0.58 * hs[:, :, np.newaxis])

    dem_extent = (dem_minx, dem_minx + dem_raw.shape[1] * dem_res,
                  dem_maxy - dem_raw.shape[0] * dem_res, dem_maxy)
    im = ax.imshow(rgb_shaded, extent=dem_extent, origin="upper", zorder=3)
    patch = get_mpl_clip_patch(xj_union)
    ax.add_patch(patch)
    im.set_clip_path(patch)

    xj_prov.boundary.plot(ax=ax, color="#34495e", lw=0.6, ls=":", zorder=5)
    gpd.GeoSeries([xj_union]).boundary.plot(ax=ax, color="#1a252f", lw=1.6, zorder=6)

    # 地理核心宏观骨架标注（三山夹两盆）
    macro_labels = [
        ("阿 尔 泰 山 脉 (北 疆 冰 雪 生 态 屏 障)", 88.5, 48.0, -18, 11.5, "#1b4f72"),
        ("准 噶 尔 盆 地 (古 尔 班 通 古 特 沙 漠)", 87.0, 45.2, 0, 12.0, "#7d6608"),
        ("天 山 山 脉 (横 贯 中 部 · 地 理 宏 伟 分 水 岭)", 83.5, 42.8, -12, 13.0, "#78281f"),
        ("塔 里 木 盆 地 (塔 克 拉 玛 干 大 沙 漠)", 83.5, 39.0, 0, 13.0, "#935116"),
        ("昆 仑 山 脉 · 阿 尔 金 山 脉 (万 山 之 祖)", 82.0, 36.5, 8, 12.0, "#1b4f72"),
        ("帕 米 尔 高 原 (万 山 汇 聚 之 极)", 75.2, 38.8, 45, 10.5, "#4a235a"),
        ("伊 犁 河 谷 (塞 外 江 南 湿 润 走 廊)", 81.8, 43.6, 15, 10.5, "#145a32"),
        ("吐 鲁 番 盆 地 (深 陷 火 洲 极 低 洼 地)", 89.4, 42.8, 0, 10.5, "#c0392b"),
        ("哈 密 盆 地 (新 疆 东 大 门)", 93.6, 42.6, 0, 10.0, "#7d6608")
    ]
    for text, lon, lat, rot, sz, col in macro_labels:
        x, y = to_alb(lon, lat)
        ax.text(x, y, text, fontsize=sz, fontweight="bold", color=col, rotation=rot,
                ha="center", va="center", zorder=12,
                path_effects=[pe.withStroke(linewidth=2.8, foreground="#ffffff")])

    # 极值点与地标
    extremes = [
        ("乔戈里峰 K2 8611m (世界第二高峰/新疆极巅)", 76.515, 35.885, "^", "#b03a2e", (120, 80), "left"),
        ("托木尔峰 7443m (天山最高峰)", 80.125, 42.045, "^", "#b03a2e", (-120, 80), "right"),
        ("友谊峰 4374m (阿尔泰山最高峰)", 87.820, 49.140, "^", "#b03a2e", (100, -60), "left"),
        ("艾丁湖 -154.31m (中国陆地最低点/世界第二洼地)", 89.260, 42.660, "v", "#2980b9", (120, -70), "left"),
        ("博格达峰 5445m (乌鲁木齐天山地标)", 88.280, 43.790, "^", "#78281f", (110, 60), "left"),
        ("慕士塔格峰 7509m (帕米尔冰山之父)", 75.115, 38.275, "^", "#78281f", (-120, -70), "right")
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

    add_scalebar(ax, ax_xlim[0] + span_x * 0.08, ax_ylim[0] + span_y * 0.08, length_km=200)
    add_compass(ax, 0.94, 0.92)

    cax = ax.inset_axes([0.08, 0.16, 0.02, 0.28])
    cb = plt.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cax, orientation="vertical")
    cb.set_label("高程 Elevation (m)", fontsize=7.2, color="#2c3e50")
    cb.ax.tick_params(labelsize=6.5, length=2.0)

    ax.set_title("新疆维吾尔自治区地形地貌与三山夹两盆格局图", fontsize=13.0, fontweight="bold", pad=20, color=C_TEXT)
    ax.text(0.5, 1.008, "Geomorphic Framework & 'Three Mountains Clamping Two Basins' in Xinjiang",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=8.0, color="#7f8c8d")
    fig.text(0.5, 0.015, "数据源：AWS Terrain GLO-30 30m DEM · 投影：Albers 等积圆锥 · 制作：《中国地理知识手册》",
             ha="center", va="bottom", fontsize=7.0, color="#7f8c8d")

    out_p = os.path.join(OUT_DIR, "fig32-00-1_新疆维吾尔自治区地形地貌与三山夹两盆格局图.png")
    fig.savefig(out_p, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_p}")

# =============================================================================
# 2. 行政区划与四大板块城镇空间骨架图 (fig32-00-2)
# =============================================================================
def gen_fig2():
    print("Generating fig32-00-2 (Administrative Framework)...")
    fig, ax = plt.subplots(figsize=(12.0, 9.2), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    PALETTE = [
        "#f9ebea", "#fef5e7", "#fef9e7", "#eafaf1", "#e8f8f5",
        "#ebf5fb", "#eaf2f8", "#f4ecf7", "#fdedec", "#f5eef8",
        "#e8f6f3", "#fcf3cf", "#d5f5e3", "#d6eaf8"
    ]
    xj_prov["color"] = [PALETTE[i % len(PALETTE)] for i in range(len(xj_prov))]
    xj_prov.plot(ax=ax, color=xj_prov["color"], edgecolor="#7f8c8d", lw=0.7, zorder=3)
    gpd.GeoSeries([xj_union]).boundary.plot(ax=ax, color="#1a252f", lw=1.8, zorder=6)

    # 标注地州名称
    for idx, row in xj_prov.iterrows():
        name = row["name"]
        center = row.geometry.representative_point()
        cx, cy = center.x, center.y
        # 针对地级市/主要地州做清晰标注
        ax.text(cx, cy, name, fontsize=7.5, fontweight="bold", color="#1a5276",
                ha="center", va="center", zorder=12,
                path_effects=[pe.withStroke(linewidth=2.0, foreground="#ffffff")])

    # 四大区域板块宏观标识
    plate_labels = [
        ("天山北坡经济带核心都市区", 86.8, 44.4, "#78281f"),
        ("北疆阿勒泰-塔城-博州-伊犁边境生态与口岸带", 83.5, 46.5, "#145a32"),
        ("东疆吐哈盆地综合能源与陆港走廊", 91.5, 42.8, "#7d6608"),
        ("南疆环塔里木盆地绿洲与中巴经济走廊", 80.5, 38.5, "#935116")
    ]
    for ptext, plon, plat, pcol in plate_labels:
        px, py = to_alb(plon, plat)
        ax.text(px, py, ptext, fontsize=9.2, fontweight="bold", color=pcol,
                ha="center", va="center", zorder=15,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#ffffff", edgecolor=pcol, alpha=0.92))

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    add_scalebar(ax, ax_xlim[0] + span_x * 0.08, ax_ylim[0] + span_y * 0.08, length_km=200)
    add_compass(ax, 0.94, 0.92)

    ax.set_title("新疆维吾尔自治区行政区划与四大板块城镇空间骨架图", fontsize=13.0, fontweight="bold", pad=20, color=C_TEXT)
    ax.text(0.5, 1.008, "Administrative Structure & Four Major Regional Frameworks in Xinjiang",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=8.0, color="#7f8c8d")
    fig.text(0.5, 0.015, "数据源：自然资源部标准地图与 DataV 行政矢量 · 制作：《中国地理知识手册》",
             ha="center", va="bottom", fontsize=7.0, color="#7f8c8d")

    out_p = os.path.join(OUT_DIR, "fig32-00-2_新疆维吾尔自治区行政区划与四大板块城镇空间骨架图.png")
    fig.savefig(out_p, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_p}")

# =============================================================================
# 3. 综合立体交通网与亚欧陆桥走廊图 (fig32-00-3)
# =============================================================================
def gen_fig3():
    print("Generating fig32-00-3 (Transport Corridor)...")
    fig, ax = plt.subplots(figsize=(12.0, 9.2), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    xj_prov.plot(ax=ax, facecolor="#fdfefe", edgecolor="#bdc3c7", lw=0.7, zorder=3)
    gpd.GeoSeries([xj_union]).boundary.plot(ax=ax, color="#2c3e50", lw=1.6, zorder=5)

    # 1. 兰新高铁 (进疆客专)
    lx_pts = [(94.5, 42.5), (93.5, 42.85), (89.1, 43.0), (87.53, 43.855)]
    lx_x, lx_y = mapkit.smooth_line([to_alb(p[0], p[1]) for p in lx_pts])
    ax.plot(lx_x, lx_y,
            color="#c0392b", lw=2.6, ls="-", zorder=8, label="兰新高铁客专 (入疆客运大通道)")

    # 2. 北疆铁路与新亚欧大陆桥 (乌鲁木齐-奎屯-精河-阿拉山口/霍尔果斯)
    bj_pts = [(87.53, 43.855), (86.06, 44.32), (84.9, 44.45), (82.57, 45.18)]
    bj_x, bj_y = mapkit.smooth_line([to_alb(p[0], p[1]) for p in bj_pts])
    ax.plot(bj_x, bj_y,
            color="#2980b9", lw=2.4, ls="-", zorder=8, label="新亚欧大陆桥 / 北疆铁路 (阿拉山口口岸)")

    # 3. 精伊霍铁路 (通往霍尔果斯)
    jh_pts = [(82.9, 44.6), (81.28, 43.96), (80.42, 44.20)]
    jh_x, jh_y = mapkit.smooth_line([to_alb(p[0], p[1]) for p in jh_pts])
    ax.plot(jh_x, jh_y,
            color="#16a085", lw=2.2, ls="--", zorder=8, label="精伊霍铁路 (霍尔果斯国际陆港)")

    # 4. 环塔里木盆地铁路闭环 (世界首条沙漠环线铁路)
    hl_pts = [
        (88.75, 43.19), (86.18, 41.74), (82.96, 41.72), (80.26, 41.17),
        (76.05, 39.49), (79.92, 37.11), (82.7, 36.8), (85.5, 38.1),
        (88.18, 39.04), (86.18, 41.74)
    ]
    hl_x, hl_y = mapkit.smooth_line([to_alb(p[0], p[1]) for p in hl_pts])
    ax.plot(hl_x, hl_y,
            color="#d35400", lw=2.2, ls="-", zorder=8, label="环塔里木盆地铁路闭环 (南疆线+和若线+格库线)")

    # 5. 格库铁路 (青海格尔木至库尔勒第三出疆通道)
    gk_pts = [(91.0, 38.0), (88.18, 39.04), (86.18, 41.74)]
    gk_x, gk_y = mapkit.smooth_line([to_alb(p[0], p[1]) for p in gk_pts])
    ax.plot(gk_x, gk_y,
            color="#8e44ad", lw=2.2, ls=":", zorder=8, label="格库铁路 (第三出疆大通道)")

    # 6. 京新高速 (G7 穿越大漠)
    g7_pts = [(94.0, 43.5), (89.5, 44.5), (87.5, 44.0)]
    g7_x, g7_y = mapkit.smooth_line([to_alb(p[0], p[1]) for p in g7_pts])
    ax.plot(g7_x, g7_y,
            color="#f39c12", lw=2.0, ls="-", zorder=7, label="京新高速 (G7 大漠通途直通北京)")

    # 枢纽机场与口岸
    hubs = [
        ("乌鲁木齐地窝堡国际机场 (4F枢纽)", 87.47, 43.90, "^", "#1f618d"),
        ("喀什徕宁国际机场 (4E南疆枢纽)", 75.96, 39.54, "^", "#1f618d"),
        ("阿拉山口铁路国门口岸", 82.57, 45.18, "s", "#c0392b"),
        ("霍尔果斯国际陆港口岸", 80.42, 44.20, "s", "#c0392b"),
        ("红其拉甫国门口岸 (中巴走廊)", 75.40, 36.85, "s", "#c0392b")
    ]
    for hname, hlon, hlat, marker, col in hubs:
        hx, hy = to_alb(hlon, hlat)
        ax.plot(hx, hy, marker, color=col, markersize=6.0, zorder=15)
        ax.annotate(hname, xy=(hx, hy), xytext=(hx + 12000, hy + 8000),
                    fontsize=7.4, fontweight="bold", color=col, zorder=16,
                    path_effects=[pe.withStroke(linewidth=2.0, foreground="#ffffff")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    add_scalebar(ax, ax_xlim[0] + span_x * 0.08, ax_ylim[0] + span_y * 0.08, length_km=200)
    add_compass(ax, 0.94, 0.92)

    leg = ax.legend(loc="upper left", bbox_to_anchor=(0.04, 0.96), fontsize=7.6,
                    framealpha=0.92, facecolor="#ffffff", edgecolor="#bdc3c7")

    ax.set_title("新疆维吾尔自治区综合立体交通网与亚欧陆桥走廊图", fontsize=13.0, fontweight="bold", pad=20, color=C_TEXT)
    ax.text(0.5, 1.008, "Comprehensive Transportation Network & Eurasian Land-Bridge Corridors in Xinjiang",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=8.0, color="#7f8c8d")
    fig.text(0.5, 0.015, "数据源：新疆综合立体交通网规划纲要 · 制作：《中国地理知识手册》",
             ha="center", va="bottom", fontsize=7.0, color="#7f8c8d")

    out_p = os.path.join(OUT_DIR, "fig32-00-3_新疆维吾尔自治区综合立体交通网与亚欧陆桥走廊图.png")
    fig.savefig(out_p, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_p}")

# =============================================================================
# 4. 现代产业体系与国家三基地一通道布局图 (fig32-00-4)
# =============================================================================
def gen_fig4():
    print("Generating fig32-00-4 (Economy & Energy/Industry)...")
    fig, ax = plt.subplots(figsize=(12.0, 9.2), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    xj_prov.plot(ax=ax, facecolor="#f8f9fa", edgecolor="#95a5a6", lw=0.7, zorder=3)
    gpd.GeoSeries([xj_union]).boundary.plot(ax=ax, color="#2c3e50", lw=1.6, zorder=5)

    # 标志性重大现代产业项目与基地
    industries = [
        ("准东国家级现代煤电煤化工产业示范区 (3900亿吨整装煤田)", 89.20, 44.75, "s", "#c0392b", (120, 80), "left"),
        ("中石油塔里木油田 (我国陆上油气增储上产主力军)", 86.15, 41.75, "s", "#8e44ad", (100, 70), "left"),
        ("独山子石化千万吨炼油百万吨乙烯基地", 84.88, 44.33, "D", "#2980b9", (-140, 80), "right"),
        ("哈密千万千瓦级风光综合能源基地与特高压起点", 93.65, 42.80, "^", "#27ae60", (110, 60), "left"),
        ("中亚天然气管道与西气东输霍尔果斯首站", 80.42, 44.20, "o", "#e67e22", (-140, 70), "right"),
        ("阿克苏优质棉花与冰糖心苹果核心产业带", 80.25, 41.20, "o", "#f39c12", (-120, -70), "right"),
        ("喀什国家级经济开发区向西开放综合保税区", 75.98, 39.48, "s", "#154360", (-120, 80), "right"),
        ("和田优质玉石产业集群与丝绸印染", 79.95, 37.15, "o", "#196f3d", (100, -70), "left"),
        ("吐鲁番葡萄干与戈壁光热发电产业基地", 89.20, 42.90, "o", "#7d3c98", (100, -60), "left"),
        ("克拉玛依云计算产业园 (全国渲染算力高地)", 84.85, 45.55, "s", "#2471a3", (-120, 70), "right"),
        ("兵团石河子国家级现代农业与新材料基地", 86.05, 44.30, "s", "#16a085", (110, -60), "left")
    ]

    for iname, ilon, ilat, marker, mcolor, (ox, oy), side in industries:
        ix, iy = to_alb(ilon, ilat)
        ax.plot(ix, iy, marker, color=mcolor, markersize=7.0, zorder=12)
        ha = "left" if side == "left" else "right"
        ax.annotate(iname, xy=(ix, iy), xytext=(ix + ox * 1000, iy + oy * 1000),
                    arrowprops=dict(arrowstyle="->", color="#7f8c8d", lw=0.8),
                    fontsize=7.4, fontweight="bold", color="#1c2833", ha=ha, va="center", zorder=15,
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="#ffffff", edgecolor=mcolor, alpha=0.9))

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    add_scalebar(ax, ax_xlim[0] + span_x * 0.08, ax_ylim[0] + span_y * 0.08, length_km=200)
    add_compass(ax, 0.94, 0.92)

    ax.set_title("新疆维吾尔自治区现代产业体系与国家三基地一通道布局图", fontsize=13.0, fontweight="bold", pad=20, color=C_TEXT)
    ax.text(0.5, 1.008, "Modern Industrial Pattern & National Energy Strategic Hub in Xinjiang",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=8.0, color="#7f8c8d")
    fig.text(0.5, 0.015, "数据源：新疆维吾尔自治区十四五新型工业化发展规划 · 制作：《中国地理知识手册》",
             ha="center", va="bottom", fontsize=7.0, color="#7f8c8d")

    out_p = os.path.join(OUT_DIR, "fig32-00-4_新疆维吾尔自治区现代产业体系与国家三基地一通道布局图.png")
    fig.savefig(out_p, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_p}")

# =============================================================================
# 5. 生态安全屏障与内陆流域水系图 (fig32-00-5)
# =============================================================================
def gen_fig5():
    print("Generating fig32-00-5 (Ecology & Water Systems)...")
    fig, ax = plt.subplots(figsize=(12.0, 9.2), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    xj_prov.plot(ax=ax, facecolor="#f4f6f7", edgecolor="#a6acaf", lw=0.7, zorder=3)
    gpd.GeoSeries([xj_union]).boundary.plot(ax=ax, color="#1a252f", lw=1.6, zorder=5)

    # 1. 塔里木河干流 (阿克苏-沙雅-轮台-尉犁-台特玛湖)
    tr_pts = [
        (80.5, 40.5), (81.3, 40.5), (82.8, 41.2), (84.2, 41.2), (85.8, 41.0),
        (86.5, 40.5), (88.0, 39.5)
    ]
    ax.plot([to_alb(p[0], p[1])[0] for p in tr_pts], [to_alb(p[0], p[1])[1] for p in tr_pts],
            color="#2980b9", lw=3.2, ls="-", zorder=8, label="塔里木河干流 (中国最长内陆河 2179km)")

    # 2. 额尔齐斯河 (中国唯一注入北冰洋河流)
    eq_pts = [(89.5, 47.5), (87.5, 47.6), (86.0, 47.7)]
    ax.plot([to_alb(p[0], p[1])[0] for p in eq_pts], [to_alb(p[0], p[1])[1] for p in eq_pts],
            color="#1abc9c", lw=2.4, ls="-", zorder=8, label="额尔齐斯河 (唯一北冰洋外流水系)")

    # 3. 伊犁河干流 (水量最丰沛国际河流)
    yl_pts = [(82.5, 43.6), (81.3, 43.85), (80.2, 44.0)]
    ax.plot([to_alb(p[0], p[1])[0] for p in yl_pts], [to_alb(p[0], p[1])[1] for p in yl_pts],
            color="#2471a3", lw=2.4, ls="-", zorder=8, label="伊犁河干支流 (塞外江南丰沛水网)")

    # 核心大湖与湿地
    lakes = [
        ("博斯腾湖 (全国最大内陆淡水湖)", 86.85, 41.98),
        ("赛里木湖 (大西洋眼泪高山明珠)", 81.16, 44.60),
        ("喀纳斯湖 (阿尔泰山高山冰川湖)", 87.05, 48.75),
        ("艾比湖 (准噶尔盆地积水中心)", 82.95, 44.90),
        ("艾丁湖 (-154m 极低含盐洼地)", 89.26, 42.66),
        ("罗布泊荒漠 (昔日大湖现为盐原)", 90.30, 40.50)
    ]
    for lname, llon, llat in lakes:
        lx, ly = to_alb(llon, llat)
        ax.plot(lx, ly, "o", color="#1f618d", markersize=5.5, zorder=14)
        ax.annotate(lname, xy=(lx, ly), xytext=(lx + 10000, ly - 6000),
                    fontsize=7.2, fontweight="bold", color="#154360", zorder=15,
                    path_effects=[pe.withStroke(linewidth=1.8, foreground="#ffffff")])

    # 生态屏障保护区示意
    # 阿尔泰山天然林水源涵养区
    ax.text(to_alb(88.0, 48.3)[0], to_alb(88.0, 48.3)[1], "阿尔泰山水源涵养林与生物多样性保护区",
            fontsize=7.6, fontweight="bold", color="#145a32", ha="center", va="center", zorder=12,
            path_effects=[pe.withStroke(linewidth=2.0, foreground="#ffffff")])
    # 天山中央森林草原屏障
    ax.text(to_alb(84.0, 43.1)[0], to_alb(84.0, 43.1)[1], "天山雪岭云杉与高山草甸生态安全屏障",
            fontsize=8.0, fontweight="bold", color="#145a32", ha="center", va="center", zorder=12,
            path_effects=[pe.withStroke(linewidth=2.0, foreground="#ffffff")])
    # 昆仑山水源涵养与防沙屏障
    ax.text(to_alb(82.0, 36.8)[0], to_alb(82.0, 36.8)[1], "昆仑山-阿尔金山高寒荒漠生态屏障",
            fontsize=8.0, fontweight="bold", color="#145a32", ha="center", va="center", zorder=12,
            path_effects=[pe.withStroke(linewidth=2.0, foreground="#ffffff")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    add_scalebar(ax, ax_xlim[0] + span_x * 0.08, ax_ylim[0] + span_y * 0.08, length_km=200)
    add_compass(ax, 0.94, 0.92)

    leg = ax.legend(loc="upper left", bbox_to_anchor=(0.04, 0.96), fontsize=7.6,
                    framealpha=0.92, facecolor="#ffffff", edgecolor="#bdc3c7")

    ax.set_title("新疆维吾尔自治区生态安全屏障与内陆流域水系图", fontsize=13.0, fontweight="bold", pad=20, color=C_TEXT)
    ax.text(0.5, 1.008, "Ecological Security Barriers & Inland Drainage Basins in Xinjiang",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=8.0, color="#7f8c8d")
    fig.text(0.5, 0.015, "数据源：新疆水资源公报与生态保护红线图 · 制作：《中国地理知识手册》",
             ha="center", va="bottom", fontsize=7.0, color="#7f8c8d")

    out_p = os.path.join(OUT_DIR, "fig32-00-5_新疆维吾尔自治区生态安全屏障与内陆流域水系图.png")
    fig.savefig(out_p, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_p}")

if __name__ == "__main__":
    gen_fig1()
    gen_fig2()
    gen_fig3()
    gen_fig4()
    gen_fig5()
    print("\n✓ All 5 Xinjiang provincial overview figures generated successfully!")
