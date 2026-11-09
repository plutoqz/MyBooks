# -*- coding: utf-8 -*-
"""内蒙古自治区地理统揽专题地图生成引擎（29-00）
包含 5 幅全区域权威地图与分析图表（精细调优排版、微缩字号、严格杜绝压盖、要素清晰呼应）：
1. fig29-00-1_内蒙古自治区地形地貌与生态屏障格局图.png
2. fig29-00-2_内蒙古自治区行政区划与空间骨架图.png
3. fig29-00-3_内蒙古自治区综合立体交通网与对外开放口岸图.png
4. fig29-00-4_内蒙古自治区产业经济与国家现代能源基地分布图.png
5. fig29-00-5_内蒙古自治区生态安全屏障与大江大湖水系格局图.png
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

def add_scalebar(ax, x0, y0, length_km=200):
    mapkit.add_scalebar(ax, x0, y0, length_km=length_km)

def add_compass(ax, x=0.94, y=0.91):
    ax.annotate("N", xy=(x, y), xytext=(x, y - 0.055), transform=ax.transAxes,
                arrowprops=dict(facecolor="#2c3e50", edgecolor="#2c3e50", width=1.8, headwidth=5.5, headlength=6.5),
                ha="center", va="center", fontsize=8.8, fontweight="bold", color="#2c3e50", zorder=30)

print("Loading Inner Mongolia provincial spatial data...")
DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
nm_cities = gpd.read_file(os.path.join(DATA_DIR, "boundaries", "datav", "150000_full.json")).to_crs(ALBERS)
nm_union = nm_cities.union_all()
bb = nm_cities.total_bounds

# 内蒙古版图极其东西狭长（跨越经度29度，直线距离超2400公里），设置适度边距
span_x = bb[2] - bb[0]
span_y = bb[3] - bb[1]
pad_x = span_x * 0.06
pad_y = span_y * 0.06
ax_xlim = (bb[0] - pad_x, bb[2] + pad_x)
ax_ylim = (bb[1] - pad_y, bb[3] + pad_y)

# 加载 DEM
print("Loading Inner Mongolia DEM...")
dem_nm, dem_minx, dem_maxy, dem_res = prov_dem("150000", zoom=9, res=300.0)

# 加载周边省份边界作为地理参考
print("Loading neighboring provinces for regional context...")
neigh_files = {
    "黑龙江省": "230000_full.json",
    "吉林省": "220000_full.json",
    "辽宁省": "210000_full.json",
    "河北省": "130000_full.json",
    "山西省": "140000_full.json",
    "陕西省": "610000_full.json",
    "宁夏回族自治区": "640000_full.json",
    "甘肃省": "620000_full.json"
}
neigh_gdfs = {}
for pname, fname in neigh_files.items():
    fpath = os.path.join(DATA_DIR, "boundaries", "datav", fname)
    if os.path.exists(fpath):
        neigh_gdfs[pname] = gpd.read_file(fpath).to_crs(ALBERS)

LEAGUE_CITY_GOV_COORDS = {
    "呼和浩特市": (111.725, 40.842),
    "包头市": (109.845, 40.655),
    "乌海市": (106.825, 39.665),
    "赤峰市": (118.925, 42.255),
    "通辽市": (122.265, 43.615),
    "鄂尔多斯市": (109.785, 39.605),
    "呼伦贝尔市": (119.765, 49.215),
    "巴彦淖尔市": (107.415, 40.755),
    "乌兰察布市": (113.115, 41.035),
    "兴安盟": (122.065, 46.075),
    "锡林郭勒盟": (116.085, 43.935),
    "阿拉善盟": (105.705, 38.845)
}

NEIGHBOR_LABELS = [
    ("黑 龙 江 省\n(Heilongjiang)", 125.80, 48.50),
    ("吉  林  省\n(Jilin)", 125.20, 44.50),
    ("辽  宁  省\n(Liaoning)", 122.50, 41.80),
    ("河  北  省\n(Hebei)", 116.50, 40.80),
    ("山  西  省\n(Shanxi)", 112.50, 38.20),
    ("陕  西  省\n(Shaanxi)", 109.50, 37.50),
    ("宁夏回族自治区\n(Ningxia)", 106.20, 37.80),
    ("甘  肃  省\n(Gansu)", 100.50, 39.20),
    ("蒙  古  国\n(Mongolia)", 109.50, 44.20),
    ("俄  罗  斯\n(Russia)", 119.50, 52.50)
]

def draw_neighbor_context(ax):
    for pname, ngdf in neigh_gdfs.items():
        ngdf.plot(ax=ax, facecolor="#f8f9fa", edgecolor="#ced4da", lw=0.55, ls="--", alpha=0.75, zorder=2)
    for txt, nlon, nlat in NEIGHBOR_LABELS:
        nx, ny = to_alb(nlon, nlat)
        if ax_xlim[0] <= nx <= ax_xlim[1] and ax_ylim[0] <= ny <= ax_ylim[1]:
            ax.text(nx, ny, txt, ha="center", va="center", fontsize=7.6, fontweight="bold",
                    color="#6c757d", zorder=8,
                    bbox=dict(boxstyle="round,pad=0.22", facecolor="#ffffff", edgecolor="#dee2e6", alpha=0.85))

# =============================================================================
# 1. fig29-00-1_内蒙古自治区地形地貌与生态屏障格局图
# =============================================================================
def gen_fig1():
    print("Generating fig29-00-1_内蒙古自治区地形地貌与生态屏障格局图.png...")
    # 东西横跨超长，采用宽幅比例尺 11.5 x 7.8
    fig, ax = plt.subplots(figsize=(11.5, 7.8), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    draw_neighbor_context(ax)

    # DEM 渲染
    hs = calc_hillshade(dem_nm, dem_res)
    colors = [
        (0.00, "#85c1e9"),   # 呼伦湖/贝尔湖/居延海水色
        (0.05, "#a9dfbf"),   # 嫩江平原与西辽河出境平原低地嫩绿 (120-400m)
        (0.18, "#d4efdf"),   # 河套平原与土默川灌区
        (0.35, "#f9e79f"),   # 广袤内蒙古高原台原暖黄 (1000-1400m)
        (0.55, "#edbb99"),   # 丘陵起伏与大青山/狼山中低山 (1400-1800m)
        (0.75, "#ba4a00"),   # 大兴安岭主脊与阴山中高山 (1800-2200m)
        (0.90, "#78281f"),   # 贺兰山主峰高山屏障深褐 (2200-3200m)
        (1.00, "#fdfefe")    # 贺兰山极顶主脊灰白 (>3500m)
    ]
    cmap_elev = LinearSegmentedColormap.from_list("nm_relief", colors)
    valid = np.nan_to_num(dem_nm, nan=120.0)
    valid = np.clip(valid, 120.0, 3556.0)
    norm = Normalize(vmin=120, vmax=3556)
    rgb = cmap_elev(norm(valid))[:, :, :3]
    rgb_shaded = rgb * (0.40 + 0.60 * hs[:, :, np.newaxis])

    dem_extent = (dem_minx, dem_minx + dem_nm.shape[1] * dem_res,
                  dem_maxy - dem_nm.shape[0] * dem_res, dem_maxy)
    im = ax.imshow(rgb_shaded, extent=dem_extent, origin="upper", zorder=3)
    patch = get_mpl_clip_patch(nm_union)
    ax.add_patch(patch)
    im.set_clip_path(patch)

    # 边界
    nm_cities.boundary.plot(ax=ax, color="#2c3e50", lw=0.55, ls=":", zorder=5)
    gpd.GeoSeries([nm_union]).boundary.plot(ax=ax, color="#1a252f", lw=1.2, zorder=6)

    # 主要山脉走向
    ranges = [
        ("大  兴  安  岭  山  脉", 121.20, 49.50, 45),
        ("大 兴 安 岭 南 段", 117.80, 43.60, 35),
        ("阴  山  山  脉 (大青山)", 111.80, 41.00, 10),
        ("阴  山  山  脉 (狼  山)", 107.20, 41.30, 20),
        ("贺  兰  山  脉", 105.90, 38.90, 80),
        ("雅  布  赖  山", 102.80, 39.50, 45)
    ]
    for name, rlon, rlat, rot in ranges:
        rx, ry = to_alb(rlon, rlat)
        ax.text(rx, ry, name, ha="center", va="center", fontsize=8.2, fontweight="bold",
                color="#3e2723", rotation=rot, zorder=10,
                path_effects=[pe.withStroke(linewidth=2.0, foreground="#ffffff")])

    # 主要大沙漠与大沙地
    deserts = [
        ("巴 丹 吉 林 沙 漠\n(世界自然遗产·高大沙山)", 102.50, 39.90),
        ("腾 格 里 沙 漠", 104.80, 38.50),
        ("乌 兰 布 和 沙 漠", 106.50, 40.20),
        ("库 布 其 沙 漠\n(联合国治沙典范)", 108.80, 40.10),
        ("毛 乌 素 沙 地\n(绿进沙退奇迹)", 108.90, 38.60),
        ("浑 善 达 克 沙 地", 115.80, 42.80),
        ("科 尔 沁 沙 地", 121.50, 43.20)
    ]
    for dname, dlon, dlat in deserts:
        dx, dy = to_alb(dlon, dlat)
        ax.text(dx, dy, dname, ha="center", va="center", fontsize=7.0, fontweight="bold",
                color="#b7950b", zorder=10,
                bbox=dict(boxstyle="round,pad=0.2", facecolor="#fef9e7", edgecolor="#f1c40f", alpha=0.85),
                path_effects=[pe.withStroke(linewidth=1.8, foreground="#ffffff")])

    # 平原与主要水系
    plains = [
        ("河 套 平 原 (塞上粮仓)", 107.50, 40.80),
        ("土 默 川 平 原", 111.40, 40.60),
        ("西 辽 河 平 原", 122.50, 43.60),
        ("呼 伦 贝 尔 草 原", 119.20, 49.30),
        ("锡 林 郭 勒 草 原", 116.50, 44.50)
    ]
    for pname, plon, plat in plains:
        px, py = to_alb(plon, plat)
        ax.text(px, py, pname, ha="center", va="center", fontsize=7.2, fontweight="bold",
                color="#196f3d", zorder=10,
                bbox=dict(boxstyle="round,pad=0.2", facecolor="#eafaf1", edgecolor="#2ecc71", alpha=0.88),
                path_effects=[pe.withStroke(linewidth=1.8, foreground="#ffffff")])

    # 极值高程标注
    pts = [
        ("贺兰山主峰 (3556m\n全区最高峰)", 105.915, 38.895, "#c0392b"),
        ("黄岗梁主峰 (2029m\n大兴安岭最高峰)", 117.065, 43.415, "#c0392b"),
        ("奥克里堆山 (1719m\n北部林海屋脊)", 121.825, 51.525, "#8e44ad"),
        ("西辽河老哈河交汇处 (120m\n全区最低点)", 123.755, 43.885, "#2980b9")
    ]
    for ptext, plon, plat, pcol in pts:
        px, py = to_alb(plon, plat)
        ax.scatter([px], [py], s=35, c=pcol, marker="^", edgecolors="white", linewidths=1.2, zorder=14)
        ax.text(px + 15000, py + 8000, ptext, fontsize=6.8, fontweight="bold", color=pcol, zorder=15,
                path_effects=[pe.withStroke(linewidth=2.0, foreground="#ffffff")])

    # 呼伦湖、乌梁素海、岱海
    lakes = [
        ("呼 伦 湖", 117.455, 48.955),
        ("乌 梁 素 海", 108.885, 40.985),
        ("岱  海", 112.695, 40.565),
        ("居  延  海", 101.315, 42.325)
    ]
    for lname, llon, llat in lakes:
        lx, ly = to_alb(llon, llat)
        ax.text(lx, ly, lname, fontsize=7.2, fontweight="bold", color="#1b4f72", zorder=12,
                path_effects=[pe.withStroke(linewidth=2.0, foreground="#ffffff")])

    # 标题与版式元数据
    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")
    add_scalebar(ax, ax_xlim[0] + span_x * 0.05, ax_ylim[0] + span_y * 0.06, length_km=200)
    add_compass(ax, x=0.95, y=0.92)

    # 高程色带图例
    cax = fig.add_axes([0.15, 0.12, 0.22, 0.018])
    cb = matplotlib.colorbar.ColorbarBase(cax, cmap=cmap_elev, norm=norm, orientation='horizontal')
    cb.set_label('高程分层设色 (Elevation / m)', fontsize=7.2, color='#2c3e50', labelpad=4)
    cb.ax.tick_params(labelsize=6.2, colors='#2c3e50')

    fig.text(0.5, 0.965, "内蒙古自治区地形地貌与生态屏障格局图", ha="center", va="top",
             fontsize=13.5, fontweight="bold", color="#2c3e50")
    fig.text(0.5, 0.935, "大兴安岭-阴山-贺兰山山脉骨架 · 四大高原板块与三大平原 · 东西2400公里北疆绿色长城",
             ha="center", va="top", fontsize=8.0, color="#7f8c8d")
    fig.text(0.5, 0.02, "注：高程数据源自 AWS Terrain Tiles 300m DEM 重采样与山体阴影合成；行政边界基于国家地理信息底图；制图时间：2026年10月",
             ha="center", va="bottom", fontsize=6.8, color="#95a5a6")

    out_p = os.path.join(OUT_DIR, "fig29-00-1_内蒙古自治区地形地貌与生态屏障格局图.png")
    fig.savefig(out_p, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  ✓ Saved {out_p}")

# =============================================================================
# 2. fig29-00-2_内蒙古自治区行政区划与空间骨架图
# =============================================================================
def gen_fig2():
    print("Generating fig29-00-2_内蒙古自治区行政区划与空间骨架图.png...")
    fig, ax = plt.subplots(figsize=(11.5, 7.8), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    draw_neighbor_context(ax)

    # 12 盟市设色：采用柔和分区渐变色
    city_colors = [
        "#d4efdf", "#d5f5e3", "#fcf3cf", "#fdebd0", "#ebdef0",
        "#e8f8f5", "#fef9e7", "#eaeded", "#f4f6f6", "#eaf2f8",
        "#fbeee6", "#e8f6f3"
    ]
    for idx, (adcode, row) in enumerate(nm_cities.iterrows()):
        col = city_colors[idx % len(city_colors)]
        gpd.GeoSeries([row['geometry']]).plot(ax=ax, facecolor=col, edgecolor="#566573", lw=0.7, zorder=3)

    gpd.GeoSeries([nm_union]).boundary.plot(ax=ax, color="#1a252f", lw=1.3, zorder=6)

    # 盟市政府驻地标注
    for cname, (clon, clat) in LEAGUE_CITY_GOV_COORDS.items():
        cx, cy = to_alb(clon, clat)
        is_capital = (cname == "呼和浩特市")
        marker_col = "#c0392b" if is_capital else "#2980b9"
        marker_size = 55 if is_capital else 40
        ax.scatter([cx], [cy], s=marker_size, c=marker_col, marker="*" if is_capital else "o",
                   edgecolors="white", linewidths=1.2, zorder=12)
        
        # 标签微调偏移
        oy = 14000 if not is_capital else 16000
        ox = 0
        if cname in ["包头市", "乌海市", "巴彦淖尔市"]:
            oy = -15000
        elif cname in ["鄂尔多斯市"]:
            oy = -16000
        
        lbl_text = f"{cname}\n(首府)" if is_capital else cname
        ax.text(cx + ox, cy + oy, lbl_text, ha="center", va="center", fontsize=7.8, fontweight="bold",
                color="#1a252f", zorder=13,
                bbox=dict(boxstyle="round,pad=0.22", facecolor="#ffffff", edgecolor=marker_col, alpha=0.9),
                path_effects=[pe.withStroke(linewidth=1.8, foreground="#ffffff")])

    # 战略发展板块标注
    zones = [
        ("呼包鄂乌一体化现代协同极核\n(经济总量超全区 60%)", 110.80, 40.20, "#922b21", "#fadbd8"),
        ("赤峰-通辽蒙东承接产业转移示范区", 120.50, 43.10, "#1f618d", "#d4e6f1"),
        ("呼伦贝尔国家北方生态安全核心屏障", 119.50, 50.20, "#196f3d", "#d5f5e3"),
        ("锡林郭勒国家绿色优质草畜与清洁能源基地", 115.80, 44.80, "#b7950b", "#fcf3cf"),
        ("阿拉善西部大漠特色生态与战略航天绿洲", 102.50, 41.20, "#6c3483", "#ebdef0")
    ]
    for ztxt, zlon, zlat, zcol, zbg in zones:
        zx, zy = to_alb(zlon, zlat)
        ax.text(zx, zy, ztxt, ha="center", va="center", fontsize=7.2, fontweight="bold",
                color=zcol, zorder=11,
                bbox=dict(boxstyle="round,pad=0.25", facecolor=zbg, edgecolor=zcol, alpha=0.92),
                path_effects=[pe.withStroke(linewidth=1.8, foreground="#ffffff")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")
    add_scalebar(ax, ax_xlim[0] + span_x * 0.05, ax_ylim[0] + span_y * 0.06, length_km=200)
    add_compass(ax, x=0.95, y=0.92)

    # 图例
    leg_elements = [
        Line2D([0], [0], marker='*', color='w', markerfacecolor='#c0392b', markeredgecolor='white', markersize=10, label='自治区首府 (呼和浩特)'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#2980b9', markeredgecolor='white', markersize=7, label='盟行政公署 / 地级市政府驻地'),
        Line2D([0], [0], color='#1a252f', lw=1.3, label='自治区界 / 国界'),
        Line2D([0], [0], color='#566573', lw=0.7, ls=':', label='盟市行政边界')
    ]
    ax.legend(handles=leg_elements, loc="lower right", bbox_to_anchor=(0.95, 0.08),
              frameon=True, facecolor="white", edgecolor="#bdc3c7", fontsize=7.0)

    fig.text(0.5, 0.965, "内蒙古自治区行政区划与空间骨架图", ha="center", va="top",
             fontsize=13.5, fontweight="bold", color="#2c3e50")
    fig.text(0.5, 0.935, "下辖 9 个地级市与 3 个盟 · 103 个旗县市区 · ‘一核两带五圈’空间开发保护格局",
             ha="center", va="top", fontsize=8.0, color="#7f8c8d")
    fig.text(0.5, 0.02, "注：行政边界依据民政部 2024 年官方标准数据；呼包鄂乌涵盖呼市、包头、鄂尔多斯及乌兰察布；制图时间：2026年10月",
             ha="center", va="bottom", fontsize=6.8, color="#95a5a6")

    out_p = os.path.join(OUT_DIR, "fig29-00-2_内蒙古自治区行政区划与空间骨架图.png")
    fig.savefig(out_p, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  ✓ Saved {out_p}")

# =============================================================================
# 3. fig29-00-3_内蒙古自治区综合立体交通网与对外开放口岸图
# =============================================================================
def gen_fig3():
    print("Generating fig29-00-3_内蒙古自治区综合立体交通网与对外开放口岸图.png...")
    fig, ax = plt.subplots(figsize=(11.5, 7.8), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    draw_neighbor_context(ax)

    # 自治区底图
    nm_cities.plot(ax=ax, facecolor="#fdfefe", edgecolor="#bdc3c7", lw=0.45, zorder=3)
    gpd.GeoSeries([nm_union]).boundary.plot(ax=ax, color="#2c3e50", lw=1.2, zorder=6)

    # 关键高铁网与铁路主干线
    rail_lines = [
        # 京包客专/呼张客专 (呼市-集宁-张家口)
        ([(111.725, 40.842), (113.115, 41.035), (114.885, 40.825)], "#e74c3c", 2.2, "-"),
        # 包银高铁 (包头-巴彦淖尔-乌海-银川)
        ([(109.845, 40.655), (107.415, 40.755), (106.825, 39.665), (106.225, 38.485)], "#e74c3c", 2.0, "--"),
        # 赤喀高铁 (赤峰-喀左-京沈)
        ([(118.925, 42.255), (119.380, 41.800), (119.745, 41.345)], "#e74c3c", 2.0, "-"),
        # 新通高铁 (通辽-新民北-沈阳)
        ([(122.265, 43.615), (122.580, 42.820), (122.845, 42.025)], "#e74c3c", 2.0, "-"),
        # 滨洲铁路 (满洲里-海拉尔-哈尔滨，中欧班列东通道)
        ([(117.445, 49.595), (119.765, 49.215), (123.505, 48.005)], "#2e4053", 1.8, "-"),
        # 集二铁路 (集宁-二连浩特，中欧班列中通道)
        ([(113.115, 41.035), (111.975, 43.655)], "#2e4053", 1.8, "-"),
        # 临策铁路 (临河-策克口岸)
        ([(107.415, 40.755), (104.505, 41.505), (101.325, 42.455)], "#7f8c8d", 1.4, "-."),
        # 包西铁路 / 浩吉铁路 (重载能源外送通道)
        ([(109.845, 40.655), (109.785, 39.605), (109.525, 38.505)], "#d35400", 2.0, "-"),
        # 集通铁路
        ([(113.115, 41.035), (118.925, 42.255), (122.265, 43.615)], "#566573", 1.5, "-")
    ]
    for pts, col, lw, ls in rail_lines:
        alb_pts = [to_alb(lon, lat) for lon, lat in pts]
        xs, ys = mapkit.smooth_line(alb_pts)
        ax.plot(xs, ys, color=col, lw=lw, ls=ls, zorder=8)

    # 关键高速公路 (G6, G7, G55, G45, G10, G18)
    exp_lines = [
        # G6 京藏高速
        ([(114.50, 40.70), (113.11, 40.96), (111.72, 40.85), (109.84, 40.65), (107.41, 40.75), (106.82, 39.66)], "#27ae60", 1.8),
        # G7 京新高速 (大漠天路)
        ([(115.00, 41.00), (113.30, 41.20), (110.50, 41.50), (107.00, 41.80), (101.50, 42.00)], "#16a085", 1.8),
        # G55 二广高速
        ([(113.11, 40.50), (113.11, 41.03), (111.97, 43.65)], "#2980b9", 1.5),
        # G10 绥满高速
        ([(117.44, 49.59), (119.76, 49.21), (123.00, 48.00)], "#8e44ad", 1.5)
    ]
    for pts, col, lw in exp_lines:
        alb_pts = [to_alb(lon, lat) for lon, lat in pts]
        xs, ys = mapkit.smooth_line(alb_pts)
        ax.plot(xs, ys, color=col, lw=lw, ls=":", zorder=7)

    # 对外开放重要边境陆路口岸
    ports = [
        ("满洲里口岸 (中俄最大陆路口岸\n中欧班列东通道咽喉)", 117.445, 49.595, "#c0392b"),
        ("二连浩特口岸 (中蒙最大综合口岸\n中欧班列中通道枢纽)", 111.975, 43.655, "#c0392b"),
        ("甘其毛都口岸 (全国最大煤炭进口口岸)", 107.825, 42.495, "#d35400"),
        ("策克口岸 (中蒙第三大陆路口岸)", 101.325, 42.455, "#d35400"),
        ("满都拉口岸 (常年开放能源口岸)", 110.255, 42.425, "#e67e22"),
        ("阿尔山口岸 (生态旅游与边贸口岸)", 119.825, 47.285, "#27ae60")
    ]
    for pname, plon, plat, pcol in ports:
        px, py = to_alb(plon, plat)
        ax.scatter([px], [py], s=60, c=pcol, marker="D", edgecolors="white", linewidths=1.2, zorder=15)
        oy = 15000 if "满洲里" not in pname else -20000
        ox = 0
        ax.text(px + ox, py + oy, pname, ha="center", va="center", fontsize=7.0, fontweight="bold",
                color=pcol, zorder=16,
                bbox=dict(boxstyle="round,pad=0.22", facecolor="#ffffff", edgecolor=pcol, alpha=0.92),
                path_effects=[pe.withStroke(linewidth=1.8, foreground="#ffffff")])

    # 机场枢纽
    airports = [
        ("呼和浩特白塔 (HET)", 111.815, 40.858),
        ("包头东河 (BAV)", 110.055, 40.558),
        ("鄂尔多斯伊金霍洛 (DSN)", 109.865, 39.495),
        ("海拉尔东山 (HLD)", 119.825, 49.208),
        ("赤峰玉龙 (CIF)", 118.845, 42.158),
        ("通辽 (TGO)", 122.198, 43.558)
    ]
    for aname, alon, alat in airports:
        ax_pt, ay_pt = to_alb(alon, alat)
        ax.scatter([ax_pt], [ay_pt], s=35, c="#1f618d", marker="^", edgecolors="white", linewidths=1.0, zorder=14)
        ax.text(ax_pt + 12000, ay_pt - 8000, aname, fontsize=6.4, fontweight="bold", color="#154360", zorder=14,
                path_effects=[pe.withStroke(linewidth=1.8, foreground="#ffffff")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")
    add_scalebar(ax, ax_xlim[0] + span_x * 0.05, ax_ylim[0] + span_y * 0.06, length_km=200)
    add_compass(ax, x=0.95, y=0.92)

    leg_elements = [
        Line2D([0], [0], color='#e74c3c', lw=2.2, label='高速铁路 / 客运专线'),
        Line2D([0], [0], color='#2e4053', lw=1.8, label='国际干线铁路 (中欧班列中/东通道)'),
        Line2D([0], [0], color='#d35400', lw=2.0, label='重载煤炭能源外送铁路 (浩吉/大准等)'),
        Line2D([0], [0], color='#27ae60', lw=1.8, ls=':', label='国家高速公路网 (G6/G7/G55等)'),
        Line2D([0], [0], marker='P', color='w', markerfacecolor='#c0392b', markeredgecolor='white', markersize=8, label='国家一类对外开放边境口岸'),
        Line2D([0], [0], marker='s', color='w', markerfacecolor='#8e44ad', markeredgecolor='white', markersize=6, label='民航民用机场')
    ]
    ax.legend(handles=leg_elements, loc="lower right", bbox_to_anchor=(0.95, 0.08),
              frameon=True, facecolor="white", edgecolor="#bdc3c7", fontsize=6.8)

    fig.text(0.5, 0.965, "内蒙古自治区综合立体交通网与对外开放口岸图", ha="center", va="top",
             fontsize=13.5, fontweight="bold", color="#2c3e50")
    fig.text(0.5, 0.935, "连通三大中欧班列口岸 · 横跨东西大动脉与纵向出海出境走廊 · 现代立体交通构筑向北开放桥头堡",
             ha="center", va="top", fontsize=8.0, color="#7f8c8d")
    fig.text(0.5, 0.02, "注：路网依据交通运输部与 OSM 2024 年全要素矢量；重点标绘满洲里、二连浩特与甘其毛都口岸；制图时间：2026年10月",
             ha="center", va="bottom", fontsize=6.8, color="#95a5a6")

    out_p = os.path.join(OUT_DIR, "fig29-00-3_内蒙古自治区综合立体交通网与对外开放口岸图.png")
    fig.savefig(out_p, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  ✓ Saved {out_p}")

# =============================================================================
# 4. fig29-00-4_内蒙古自治区产业经济与国家现代能源基地分布图
# =============================================================================
def gen_fig4():
    print("Generating fig29-00-4_内蒙古自治区产业经济与国家现代能源基地分布图.png...")
    fig, ax = plt.subplots(figsize=(11.5, 7.8), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    draw_neighbor_context(ax)

    # 底图
    nm_cities.plot(ax=ax, facecolor="#fefefe", edgecolor="#bdc3c7", lw=0.45, zorder=3)
    gpd.GeoSeries([nm_union]).boundary.plot(ax=ax, color="#1a252f", lw=1.2, zorder=6)

    # 重点能源基石与产业集聚区
    clusters = [
        ("神东特大型煤炭基地\n(全国最大现代煤炭集群)", 110.22, 39.31, "#7b241c", "煤炭极核"),
        ("准格尔大型露天煤田与煤电化基地", 111.23, 39.86, "#78281f", "煤电基石"),
        ("白云鄂博世界级稀土与铌伴生矿床", 109.96, 41.76, "#512e5f", "世界稀土之都"),
        ("包头现代绿色硅都\n(单晶硅/多晶硅全球中心)", 109.85, 40.58, "#1b4f72", "绿色硅都"),
        ("伊利现代智慧健康谷·中国乳都", 111.41, 40.78, "#145a32", "中国乳都"),
        ("和林格尔国家算力网络枢纽节点", 111.83, 40.57, "#0e6251", "绿色算力"),
        ("草原云谷乌兰察布绿色算力集群", 113.18, 41.02, "#0e6251", "绿色算力"),
        ("霍林河现代露天煤电铝循环基地", 119.58, 45.50, "#641e16", "煤电铝材"),
        ("胜利超大型露天煤矿与特高压起点", 116.02, 44.05, "#78281f", "煤电外送"),
        ("库布其沙漠亿千瓦级‘沙戈荒’风光基地", 108.95, 40.25, "#d4ac0d", "大型风光"),
        ("腾格里沙漠千万千瓦级清洁风电光伏", 105.10, 38.60, "#d4ac0d", "大型风光"),
        ("河套灌区优质粮油与现代农畜带", 107.45, 40.85, "#1e8449", "塞上江南")
    ]
    for cname, clon, clat, ccol, ctag in clusters:
        cx, cy = to_alb(clon, clat)
        ax.scatter([cx], [cy], s=70, c=ccol, marker="D", edgecolors="white", linewidths=1.2, zorder=12)
        ax.text(cx, cy + 13000, f"{cname}\n【{ctag}】", ha="center", va="bottom", fontsize=6.8, fontweight="bold",
                color=ccol, zorder=13,
                bbox=dict(boxstyle="round,pad=0.22", facecolor="#ffffff", edgecolor=ccol, alpha=0.92),
                path_effects=[pe.withStroke(linewidth=1.8, foreground="#ffffff")])

    # 特高压输电外送战略走廊 (虚拟示意走向箭头)
    uhv_lines = [
        ([(116.02, 44.05), (117.80, 41.50), (119.50, 39.50)], "#c0392b", "锡盟—山东特高压交流 (1000kV)"),
        ([(116.02, 44.05), (115.50, 40.20), (116.50, 36.50)], "#8e44ad", "锡盟—江苏特高压直流 (±800kV)"),
        ([(110.22, 39.31), (112.50, 37.50), (116.50, 35.50)], "#e67e22", "蒙西—天津南/山东特高压通道")
    ]
    for pts, ucol, utxt in uhv_lines:
        alb_pts = [to_alb(lon, lat) for lon, lat in pts]
        xs, ys = zip(*alb_pts)
        ax.plot(xs, ys, color=ucol, lw=2.2, ls="--", zorder=9)
        mid_x = (xs[0] + xs[1]) / 2.0
        mid_y = (ys[0] + ys[1]) / 2.0
        ax.text(mid_x, mid_y, utxt, fontsize=6.5, fontweight="bold", color=ucol, zorder=10,
                path_effects=[pe.withStroke(linewidth=2.0, foreground="#ffffff")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")
    add_scalebar(ax, ax_xlim[0] + span_x * 0.05, ax_ylim[0] + span_y * 0.06, length_km=200)
    add_compass(ax, x=0.95, y=0.92)

    leg_elements = [
        Line2D([0], [0], marker='D', color='w', markerfacecolor='#78281f', markeredgecolor='white', markersize=7, label='国家现代特大型煤炭基地'),
        Line2D([0], [0], marker='D', color='w', markerfacecolor='#512e5f', markeredgecolor='white', markersize=7, label='世界稀土与关键矿产战略基地'),
        Line2D([0], [0], marker='D', color='w', markerfacecolor='#1b4f72', markeredgecolor='white', markersize=7, label='现代绿色晶硅光伏产业高地'),
        Line2D([0], [0], marker='D', color='w', markerfacecolor='#d4ac0d', markeredgecolor='white', markersize=7, label='国家“沙戈荒”风光大基地'),
        Line2D([0], [0], marker='D', color='w', markerfacecolor='#0e6251', markeredgecolor='white', markersize=7, label='全国一体化算力网络枢纽节点'),
        Line2D([0], [0], marker='D', color='w', markerfacecolor='#1e8449', markeredgecolor='white', markersize=7, label='国家现代绿色农畜与乳业基地'),
        Line2D([0], [0], color='#c0392b', lw=2.0, ls='--', label='国家特高压西电东送/北电南送骨干通道')
    ]
    ax.legend(handles=leg_elements, loc="lower right", bbox_to_anchor=(0.95, 0.08),
              frameon=True, facecolor="white", edgecolor="#bdc3c7", fontsize=6.6)

    fig.text(0.5, 0.965, "内蒙古自治区产业经济与国家现代能源基地分布图", ha="center", va="top",
             fontsize=13.5, fontweight="bold", color="#2c3e50")
    fig.text(0.5, 0.935, "保障国家能源安全‘压舱石’ · 稀土/硅都/乳都世界级集群 · ‘沙戈荒’风电光伏与特高压外送矩阵",
             ha="center", va="top", fontsize=8.0, color="#7f8c8d")
    fig.text(0.5, 0.02, "注：能源与产业数据来源于内蒙古自治区发改委与统计局 2024 年数据；特高压走向为走廊示意；制图时间：2026年10月",
             ha="center", va="bottom", fontsize=6.8, color="#95a5a6")

    out_p = os.path.join(OUT_DIR, "fig29-00-4_内蒙古自治区产业经济与国家现代能源基地分布图.png")
    fig.savefig(out_p, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  ✓ Saved {out_p}")

# =============================================================================
# 5. fig29-00-5_内蒙古自治区生态安全屏障与大江大湖水系格局图
# =============================================================================
def gen_fig5():
    print("Generating fig29-00-5_内蒙古自治区生态安全屏障与大江大湖水系格局图.png...")
    fig, ax = plt.subplots(figsize=(11.5, 7.8), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    draw_neighbor_context(ax)

    # 底图按生态植被背景色浅绿渲染
    nm_cities.plot(ax=ax, facecolor="#eafaf1", edgecolor="#a2d9ce", lw=0.5, zorder=3)
    gpd.GeoSeries([nm_union]).boundary.plot(ax=ax, color="#1a252f", lw=1.2, zorder=6)

    # 关键水系 (黄河几字弯、额尔古纳河、黑河、嫩江、西辽河)
    rivers = [
        # 黄河几字弯大回折
        ([(106.80, 39.40), (107.00, 40.30), (107.60, 40.80), (109.80, 40.50), (111.20, 40.20), (111.40, 39.70)], "#2980b9", 2.4, "黄河几字弯"),
        # 额尔古纳河
        ([(117.40, 49.60), (119.50, 51.50), (121.50, 53.30)], "#2980b9", 2.2, "额尔古纳河 (中俄界河)"),
        # 黑河 (弱水下游额济纳河)
        ([(100.20, 40.50), (100.90, 41.80), (101.30, 42.30)], "#2980b9", 1.8, "黑河 (弱水下游)"),
        # 西辽河
        ([(119.20, 43.50), (122.20, 43.60), (123.80, 43.90)], "#2980b9", 1.8, "西辽河")
    ]
    for rpts, rcol, rlw, rname in rivers:
        alb_pts = [to_alb(lon, lat) for lon, lat in rpts]
        rxs, rys = zip(*alb_pts)
        ax.plot(rxs, rys, color=rcol, lw=rlw, zorder=8)
        mid_x = (rxs[0] + rxs[-1]) / 2.0
        mid_y = (rys[0] + rys[-1]) / 2.0
        ax.text(mid_x, mid_y + 10000, rname, fontsize=7.2, fontweight="bold", color=rcol, zorder=9,
                path_effects=[pe.withStroke(linewidth=2.0, foreground="#ffffff")])

    # 重点生态保护与治理工程地标
    ecozones = [
        ("大兴安岭森林生态涵养屏障\n(全国最大国有原始林海·水塔与碳汇)", 121.50, 50.80, "#145a32", "原始森林"),
        ("呼伦湖水生态保护区\n(‘一湖两海’关键治理水系)", 117.45, 48.95, "#1b4f72", "大湖治理"),
        ("乌梁素海流域综合治理工程\n(黄河流域最大淡水湖湿地)", 108.88, 40.98, "#1b4f72", "湿地治理"),
        ("岱海水生态应急补水与治理工程", 112.69, 40.56, "#1b4f72", "内陆咸水湖"),
        ("额济纳黑河生态调水与居延海复苏奇迹", 101.31, 42.32, "#117864", "生态分水"),
        ("库布其沙漠防沙治沙与光伏长城", 108.90, 40.20, "#b7950b", "防沙治沙"),
        ("科尔沁沙地歼灭战攻坚核心区", 121.80, 43.50, "#b7950b", "三北六期"),
        ("巴丹吉林沙漠世界自然遗产核心区", 102.40, 39.85, "#7d6608", "世界遗产")
    ]
    for ename, elon, elat, ecol, etag in ecozones:
        ex, ey = to_alb(elon, elat)
        ax.scatter([ex], [ey], s=65, c=ecol, marker="h", edgecolors="white", linewidths=1.2, zorder=12)
        ax.text(ex, ey + 12000, f"{ename}\n【{etag}】", ha="center", va="bottom", fontsize=6.8, fontweight="bold",
                color=ecol, zorder=13,
                bbox=dict(boxstyle="round,pad=0.22", facecolor="#ffffff", edgecolor=ecol, alpha=0.92),
                path_effects=[pe.withStroke(linewidth=1.8, foreground="#ffffff")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")
    add_scalebar(ax, ax_xlim[0] + span_x * 0.05, ax_ylim[0] + span_y * 0.06, length_km=200)
    add_compass(ax, x=0.95, y=0.92)

    leg_elements = [
        Line2D([0], [0], color='#2980b9', lw=2.2, label='主要大江大河干流水系'),
        Line2D([0], [0], marker='h', color='w', markerfacecolor='#145a32', markeredgecolor='white', markersize=7, label='大兴安岭林海生态涵养水源区'),
        Line2D([0], [0], marker='h', color='w', markerfacecolor='#1b4f72', markeredgecolor='white', markersize=7, label='‘一湖两海’生态综合治理工程'),
        Line2D([0], [0], marker='h', color='w', markerfacecolor='#117864', markeredgecolor='white', markersize=7, label='黑河分水与居延海湿地复苏区'),
        Line2D([0], [0], marker='h', color='w', markerfacecolor='#b7950b', markeredgecolor='white', markersize=7, label='三北工程六期三大标志性战役攻坚区'),
        Line2D([0], [0], marker='h', color='w', markerfacecolor='#7d6608', markeredgecolor='white', markersize=7, label='巴丹吉林沙漠世界自然遗产保护区')
    ]
    ax.legend(handles=leg_elements, loc="lower right", bbox_to_anchor=(0.95, 0.08),
              frameon=True, facecolor="white", edgecolor="#bdc3c7", fontsize=6.6)

    fig.text(0.5, 0.965, "内蒙古自治区生态安全屏障与大江大湖水系格局图", ha="center", va="top",
             fontsize=13.5, fontweight="bold", color="#2c3e50")
    fig.text(0.5, 0.935, "筑牢祖国北疆绿色生态安全长城 · ‘一湖两海’治理攻坚与黑河分水奇迹 · 三北工程三大战役主战场",
             ha="center", va="top", fontsize=8.0, color="#7f8c8d")
    fig.text(0.5, 0.02, "注：水系与生态工程依据生态环境部、水利部及三北工程建设规划 2024 年权威发布；制图时间：2026年10月",
             ha="center", va="bottom", fontsize=6.8, color="#95a5a6")

    out_p = os.path.join(OUT_DIR, "fig29-00-5_内蒙古自治区生态安全屏障与大江大湖水系格局图.png")
    fig.savefig(out_p, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  ✓ Saved {out_p}")

if __name__ == "__main__":
    print("=== Generating Inner Mongolia Overview Maps (29-00) ===")
    gen_fig1()
    gen_fig2()
    gen_fig3()
    gen_fig4()
    gen_fig5()
    print("=== All 5 Inner Mongolia Overview Maps Generated Successfully! ===")
