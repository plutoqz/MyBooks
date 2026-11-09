# -*- coding: utf-8 -*-
"""宁夏回族自治区地理统揽专题地图生成引擎（31-00）
包含 5 幅全区域权威地图与分析图表（精细调优排版、微缩字号、严格杜绝压盖、要素清晰呼应）：
1. fig31-00-1_宁夏回族自治区地形地貌与贺兰六盘地理屏障图.png
2. fig31-00-2_宁夏回族自治区行政区划与沿黄城镇带空间格局图.png
3. fig31-00-3_宁夏回族自治区综合立体交通网与丝路物流通道图.png
4. fig31-00-4_宁夏回族自治区现代产业体系与宁东能源算力基地图.png
5. fig31-00-5_宁夏回族自治区生态安全格局与引黄灌溉水系图.png
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

def add_scalebar(ax, x0, y0, length_km=60):
    mapkit.add_scalebar(ax, x0, y0, length_km=length_km)

def add_compass(ax, x=0.92, y=0.94):
    ax.annotate("N", xy=(x, y), xytext=(x, y - 0.05), transform=ax.transAxes,
                arrowprops=dict(facecolor="#2c3e50", edgecolor="#2c3e50", width=1.8, headwidth=5.5, headlength=6.5),
                ha="center", va="center", fontsize=8.8, fontweight="bold", color="#2c3e50", zorder=30)

print("Loading Ningxia provincial spatial data...")
DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
nx_cities = gpd.read_file(os.path.join(DATA_DIR, "boundaries", "datav", "640000_full.json")).to_crs(ALBERS)
nx_union = nx_cities.union_all()
bb = nx_cities.total_bounds

# 视口与中心计算：宁夏呈南北纵长形态
span_x = bb[2] - bb[0]
span_y = bb[3] - bb[1]
pad_x = span_x * 0.08
pad_y = span_y * 0.05
ax_xlim = (bb[0] - pad_x, bb[2] + pad_x)
ax_ylim = (bb[1] - pad_y, bb[3] + pad_y)

# 加载 DEM
print("Loading Ningxia DEM...")
dem_nx, dem_minx, dem_maxy, dem_res = prov_dem("640000", zoom=9, res=250.0)

# =============================================================================
# 1. 地形地貌与贺兰六盘地理屏障图 (fig31-00-1)
# =============================================================================
def gen_fig1():
    print("Generating fig31-00-1 (Topography)...")
    fig, ax = plt.subplots(figsize=(9.2, 12.0), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    hs = calc_hillshade(dem_nx, dem_res)
    colors = [
        (0.00, "#a9dfbf"),   # 惠农/黄河出境谷地暖绿
        (0.12, "#d4efdf"),   # 银川平原冲积绿洲
        (0.28, "#f9e79f"),   # 中部干旱带/黄土丘陵暖黄
        (0.50, "#edbb99"),   # 丘陵中山棕褐
        (0.72, "#ba4a00"),   # 贺兰/六盘中高山深褐
        (0.90, "#873600"),   # 高山岩石峰脊
        (1.00, "#fdfefe")    # 极顶白
    ]
    cmap = LinearSegmentedColormap.from_list("nx_elev", colors, N=256)
    norm = Normalize(vmin=800.0, vmax=3600.0)

    valid = np.nan_to_num(dem_nx, nan=800.0)
    valid = np.clip(valid, 800.0, 3600.0)
    rgb = cmap(norm(valid))[:, :, :3]
    rgb_shaded = rgb * (0.42 + 0.58 * hs[:, :, np.newaxis])

    dem_extent = (dem_minx, dem_minx + dem_nx.shape[1] * dem_res,
                  dem_maxy - dem_nx.shape[0] * dem_res, dem_maxy)
    im = ax.imshow(rgb_shaded, extent=dem_extent, origin="upper", zorder=3)
    patch = get_mpl_clip_patch(nx_union)
    ax.add_patch(patch)
    im.set_clip_path(patch)

    nx_cities.boundary.plot(ax=ax, color="#34495e", lw=0.6, ls=":", zorder=5)
    gpd.GeoSeries([nx_union]).boundary.plot(ax=ax, color="#1a252f", lw=1.5, zorder=6)

    # 地貌大单元与核心山脉标注
    macro_labels = [
        ("银 川 平 原 (引黄塞上江南)", 106.30, 38.60, 45, 11.5, "#145a32"),
        ("贺 兰 山 脉 (西北天然屏障)", 105.85, 38.65, 75, 11.5, "#78281f"),
        ("腾格里沙漠南侵阻隔带", 105.00, 37.60, 0, 9.8, "#935116"),
        ("卫 宁 平 原", 105.40, 37.45, 15, 9.5, "#145a32"),
        ("中 部 干 旱 带 丘 陵 荒 漠", 106.60, 37.25, 0, 11.0, "#7d6608"),
        ("罗 山 (中部干旱绿岛)", 106.31, 37.20, 0, 9.5, "#196f3d"),
        ("牛 首 山", 106.02, 37.81, 0, 8.8, "#4a235a"),
        ("香 山 峰 峦", 105.28, 37.15, 0, 8.8, "#4a235a"),
        ("六 盘 山 脉 (黄土高原生态绿岛)", 106.26, 35.62, 75, 11.0, "#196f3d"),
        ("西 海 固 黄 土 丘 陵 沟 壑 区", 105.80, 36.15, 0, 10.5, "#7d6608")
    ]
    for text, lon, lat, rot, sz, col in macro_labels:
        x, y = to_alb(lon, lat)
        ax.text(x, y, text, fontsize=sz, fontweight="bold", color=col, rotation=rot,
                ha="center", va="center", zorder=12,
                path_effects=[pe.withStroke(linewidth=2.8, foreground="#ffffff")])

    # 极值点与地标注记
    extremes = [
        ("贺兰山砂威坨 3556m (全区最高峰)", 105.860, 38.900, "^", "#b03a2e", (40, 10), "left"),
        ("六盘山米缸山 2942m (南部第一高峰)", 106.260, 35.620, "^", "#b03a2e", (40, -10), "left"),
        ("罗山主峰 2624m", 106.310, 37.200, "^", "#78281f", (35, 10), "left"),
        ("南华山主峰 2955m", 105.610, 36.420, "^", "#78281f", (-40, 10), "right"),
        ("惠农黄河出境点 869m (全区最低点)", 106.820, 39.360, "v", "#27ae60", (-45, 15), "right"),
        ("青铜峡水利枢纽峡口", 105.990, 37.890, "s", "#2980b9", (-40, -15), "right"),
        ("沙坡头麦草方格治沙地标", 104.990, 37.460, "*", "#d35400", (-45, 15), "right")
    ]
    for name, lon, lat, marker, mcolor, (ox, oy), side in extremes:
        px, py = to_alb(lon, lat)
        ax.plot(px, py, marker, color=mcolor, markersize=6.5, zorder=15)
        ha = "left" if side == "left" else "right"
        ax.annotate(name, xy=(px, py), xytext=(px + ox * 1000, py + oy * 1000),
                    arrowprops=dict(arrowstyle="-", color="#7f8c8d", lw=0.7),
                    fontsize=7.6, fontweight="bold", color="#1c2833", ha=ha, va="center", zorder=16,
                    path_effects=[pe.withStroke(linewidth=2.2, foreground="#ffffff")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    add_scalebar(ax, ax_xlim[0] + span_x * 0.08, ax_ylim[0] + span_y * 0.06, length_km=60)
    add_compass(ax, 0.90, 0.94)

    cax = ax.inset_axes([0.08, 0.12, 0.024, 0.22])
    cb = plt.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cax, orientation="vertical")
    cb.set_label("高程 Elevation (m)", fontsize=7.2, color="#2c3e50")
    cb.ax.tick_params(labelsize=6.5, length=2.0)

    ax.set_title("宁夏回族自治区地形地貌与贺兰六盘地理屏障图", fontsize=13.0, fontweight="bold", pad=20, color=C_TEXT)
    ax.text(0.5, 1.008, "Geomorphic Framework & Ecological Mountain Barriers of Ningxia Hui Autonomous Region",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=8.0, color="#7f8c8d")
    fig.text(0.5, 0.012, "数据源：AWS Terrain GLO-30 30m DEM · 投影：Albers 等积圆锥 · 制作：《中国地理知识手册》",
             ha="center", va="bottom", fontsize=7.0, color="#7f8c8d")

    out_p = os.path.join(OUT_DIR, "fig31-00-1_宁夏回族自治区地形地貌与贺兰六盘地理屏障图.png")
    fig.savefig(out_p, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_p}")

# =============================================================================
# 2. 行政区划与沿黄城镇带空间格局图 (fig31-00-2)
# =============================================================================
def gen_fig2():
    print("Generating fig31-00-2 (Administrative Divisions)...")
    fig, ax = plt.subplots(figsize=(9.2, 12.0), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    PALETTE = ["#fcf3cf", "#d5f5e3", "#d6eaf8", "#fdedec", "#ebf5fb"]
    nx_cities["color"] = [PALETTE[i % len(PALETTE)] for i in range(len(nx_cities))]
    nx_cities.plot(ax=ax, color=nx_cities["color"], edgecolor="#7f8c8d", lw=0.9, zorder=3)
    gpd.GeoSeries([nx_union]).boundary.plot(ax=ax, color="#1a252f", lw=1.8, zorder=6)

    # 绘制区县级边界细线（如果存在各市 _full.json）
    for adcode in ["640100", "640200", "640300", "640400", "640500"]:
        cp = os.path.join(DATA_DIR, "boundaries", "datav", f"{adcode}_full.json")
        if os.path.exists(cp):
            try:
                cgdf = gpd.read_file(cp).to_crs(ALBERS)
                cgdf.boundary.plot(ax=ax, color="#95a5a6", lw=0.5, ls="--", zorder=4)
                for _, r in cgdf.iterrows():
                    dname = r.get("name", "")
                    if dname and dname not in ["市辖区"]:
                        pt = r.geometry.representative_point()
                        ax.text(pt.x, pt.y, dname, fontsize=6.8, color="#566573", ha="center", va="center",
                                zorder=10, path_effects=[pe.withStroke(linewidth=1.8, foreground="#ffffff")])
            except Exception:
                pass

    # 标注 5 个地级市中心与核心能级
    city_labels = [
        ("银川市 (自治区首府·塞上湖城)", 106.230, 38.487, "#78281f", 10.0),
        ("石嘴山市 (工业新高地·沙湖之城)", 106.383, 39.013, "#1a5276", 9.2),
        ("吴忠市 (塞上江南名城·滩羊之乡)", 106.198, 37.997, "#196f3d", 9.2),
        ("中卫市 (沙漠水城·西部云基地)", 105.190, 37.515, "#7d6608", 9.2),
        ("固原市 (六盘山绿色屏障·红色重镇)", 106.285, 36.005, "#6c3483", 9.2)
    ]
    for cname, clon, clat, col, fsz in city_labels:
        cx, cy = to_alb(clon, clat)
        ax.plot(cx, cy, "o", color=col, markersize=5.5, zorder=14)
        ax.text(cx, cy + 5000, cname, fontsize=fsz, fontweight="bold", color=col,
                ha="center", va="bottom", zorder=15,
                path_effects=[pe.withStroke(linewidth=2.5, foreground="#ffffff")])

    # 沿黄城镇带走廊示意
    ax.annotate("宁夏沿黄城市群核心发展轴", xy=to_alb(106.25, 38.25), xytext=to_alb(107.0, 38.5),
                arrowprops=dict(facecolor="#2980b9", edgecolor="#2980b9", width=1.5, headwidth=5),
                fontsize=8.5, fontweight="bold", color="#1b4f72", zorder=18,
                path_effects=[pe.withStroke(linewidth=2.2, foreground="#ffffff")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    add_scalebar(ax, ax_xlim[0] + span_x * 0.08, ax_ylim[0] + span_y * 0.06, length_km=60)
    add_compass(ax, 0.90, 0.94)

    ax.set_title("宁夏回族自治区行政区划与沿黄城镇带空间格局图", fontsize=13.0, fontweight="bold", pad=20, color=C_TEXT)
    ax.text(0.5, 1.008, "Administrative Divisions & Urban Agglomeration Along the Yellow River in Ningxia (5 Prefecture-level Cities)",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=8.0, color="#7f8c8d")
    fig.text(0.5, 0.012, "数据源：民政部行政区划代码与自然资源部标准矢量 · 制作：《中国地理知识手册》",
             ha="center", va="bottom", fontsize=7.0, color="#7f8c8d")

    out_p = os.path.join(OUT_DIR, "fig31-00-2_宁夏回族自治区行政区划与沿黄城镇带空间格局图.png")
    fig.savefig(out_p, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_p}")

# =============================================================================
# 3. 综合立体交通网与丝路物流通道图 (fig31-00-3)
# =============================================================================
def gen_fig3():
    print("Generating fig31-00-3 (Transport Corridor)...")
    fig, ax = plt.subplots(figsize=(9.2, 12.0), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    nx_cities.plot(ax=ax, facecolor="#fdfefe", edgecolor="#bdc3c7", lw=0.7, zorder=3)
    gpd.GeoSeries([nx_union]).boundary.plot(ax=ax, color="#2c3e50", lw=1.6, zorder=5)

    # 1. 银西高铁 (银川-吴忠-庆阳-西安)
    yx_pts = [(106.185, 38.495), (106.250, 37.980), (106.600, 37.300), (107.335, 36.565)]
    yx_x, yx_y = mapkit.smooth_line([to_alb(p[0], p[1]) for p in yx_pts])
    ax.plot(yx_x, yx_y,
            color="#c0392b", lw=2.6, ls="-", zorder=8, label="银西高铁 (南下关中客运专线)")

    # 2. 银兰高铁 (银川-中卫-兰州)
    yl_pts = [(106.185, 38.495), (106.250, 37.980), (105.710, 37.480), (105.210, 37.490), (104.750, 37.150)]
    yl_x, yl_y = mapkit.smooth_line([to_alb(p[0], p[1]) for p in yl_pts])
    ax.plot(yl_x, yl_y,
            color="#e74c3c", lw=2.4, ls="--", zorder=8, label="银兰高铁 (连接甘宁两区省会)")

    # 3. 包兰铁路 / 包银高铁 (包头-惠农-石嘴山-银川-中卫)
    bl_pts = [(106.770, 39.235), (106.365, 39.025), (106.185, 38.495), (106.060, 38.010), (105.210, 37.490), (104.990, 37.460)]
    bl_x, bl_y = mapkit.smooth_line([to_alb(p[0], p[1]) for p in bl_pts])
    ax.plot(bl_x, bl_y,
            color="#2980b9", lw=2.2, ls="-", zorder=7, label="包兰铁路 / 包银高铁 (沿黄国家铁路干线)")

    # 4. 宝中铁路 (中卫-固原-平凉-宝鸡)
    bz_pts = [(105.210, 37.490), (105.680, 36.850), (106.295, 36.020), (106.330, 35.500)]
    bz_x, bz_y = mapkit.smooth_line([to_alb(p[0], p[1]) for p in bz_pts])
    ax.plot(bz_x, bz_y,
            color="#27ae60", lw=2.0, ls="-.", zorder=7, label="宝中铁路 (跨越六盘山南北干线)")

    # 5. 太中银铁路 (经盐池通达华北)
    tzy_pts = [(107.500, 37.800), (107.405, 37.785), (106.500, 38.050), (106.185, 38.495)]
    tzy_x, tzy_y = mapkit.smooth_line([to_alb(p[0], p[1]) for p in tzy_pts])
    ax.plot(tzy_x, tzy_y,
            color="#8e44ad", lw=2.0, ls=":", zorder=7, label="太中银铁路 (西煤东运与东西客货通道)")

    # 高速公路网主要通道 (京藏高速 G6 / 青银高速 G20 / 福银高速 G70)
    g6_pts = [(106.78, 39.25), (106.56, 38.98), (106.21, 38.36), (106.15, 37.98), (105.75, 37.52)]
    g6_x, g6_y = mapkit.smooth_line([to_alb(p[0], p[1]) for p in g6_pts])
    ax.plot(g6_x, g6_y,
            color="#f39c12", lw=1.6, ls="-", zorder=6, label="京藏高速 (G6 国家高速骨干)")

    # 枢纽机场与高铁特等站标注
    airports = [
        ("银川河东国际机场 (4E级干线枢纽)", 106.395, 38.322),
        ("中卫沙坡头机场 (4C级生态旅游)", 105.155, 37.575),
        ("固原六盘山机场 (4C级高高原机场)", 106.220, 36.075)
    ]
    for aname, alon, alat in airports:
        ax_pt, ay_pt = to_alb(alon, alat)
        ax.plot(ax_pt, ay_pt, "^", color="#1f618d", markersize=7.0, zorder=15)
        ax.annotate(aname, xy=(ax_pt, ay_pt), xytext=(ax_pt + 6000, ay_pt + 4000),
                    fontsize=7.4, fontweight="bold", color="#4a235a", zorder=16,
                    path_effects=[pe.withStroke(linewidth=2.0, foreground="#ffffff")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    add_scalebar(ax, ax_xlim[0] + span_x * 0.08, ax_ylim[0] + span_y * 0.06, length_km=60)
    add_compass(ax, 0.90, 0.94)

    leg = ax.legend(loc="upper left", bbox_to_anchor=(0.03, 0.98), fontsize=7.4,
                    framealpha=0.92, facecolor="#ffffff", edgecolor="#bdc3c7")

    ax.set_title("宁夏回族自治区综合立体交通网与丝路物流通道图", fontsize=13.0, fontweight="bold", pad=20, color=C_TEXT)
    ax.text(0.5, 1.008, "Comprehensive Transportation Network & Logistics Hubs of Ningxia",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=8.0, color="#7f8c8d")
    fig.text(0.5, 0.012, "数据源：宁夏综合立体交通网规划纲要 · 制作：《中国地理知识手册》",
             ha="center", va="bottom", fontsize=7.0, color="#7f8c8d")

    out_p = os.path.join(OUT_DIR, "fig31-00-3_宁夏回族自治区综合立体交通网与丝路物流通道图.png")
    fig.savefig(out_p, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_p}")

# =============================================================================
# 4. 现代产业体系与宁东能源算力基地图 (fig31-00-4)
# =============================================================================
def gen_fig4():
    print("Generating fig31-00-4 (Economy & Energy/Computing)...")
    fig, ax = plt.subplots(figsize=(9.2, 12.0), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    nx_cities.plot(ax=ax, facecolor="#f8f9fa", edgecolor="#95a5a6", lw=0.7, zorder=3)
    gpd.GeoSeries([nx_union]).boundary.plot(ax=ax, color="#2c3e50", lw=1.6, zorder=5)

    # 标志性重大现代产业项目与基地
    industries = [
        ("国家级宁东能源化工基地 (400万吨级现代煤制油)", 106.620, 38.180, "s", "#c0392b", (35, 15), "left"),
        ("中卫‘西部云基地’ (全国一体化算力网络国家枢纽节点)", 105.150, 37.580, "s", "#8e44ad", (-40, 25), "right"),
        ("贺兰山东麓葡萄酒百里产业廊道 (国家地理标志)", 105.990, 38.520, "o", "#922b21", (-40, -15), "right"),
        ("盐池滩羊核心产区 (中国滩羊之乡·国宴地标羊肉)", 107.380, 37.850, "o", "#d35400", (30, -15), "left"),
        ("中宁枸杞核心产业园 (中国枸杞之乡·红宝名牌)", 105.670, 37.470, "o", "#b03a2e", (35, 10), "left"),
        ("石嘴山先进材料高新技术基地 (单晶硅与特种锂电)", 106.420, 39.040, "D", "#2980b9", (35, 15), "left"),
        ("吴忠中国早茶文化街区与现代绿色奶业集群", 106.210, 38.005, "o", "#27ae60", (35, -15), "left"),
        ("红寺堡全国最大易地生态移民葡萄种植示范带", 106.180, 37.450, "s", "#16a085", (35, -15), "left"),
        ("彭阳旱作梯田水土保持与红梅杏生态农业基地", 106.620, 35.830, "o", "#f39c12", (30, 15), "left"),
        ("西吉马铃薯国家原种繁育基地 (中国马铃薯之乡)", 105.730, 35.960, "o", "#7d6608", (-40, -15), "right")
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

    add_scalebar(ax, ax_xlim[0] + span_x * 0.08, ax_ylim[0] + span_y * 0.06, length_km=60)
    add_compass(ax, 0.90, 0.94)

    ax.set_title("宁夏回族自治区现代产业体系与宁东能源算力基地图", fontsize=13.0, fontweight="bold", pad=20, color=C_TEXT)
    ax.text(0.5, 1.008, "Modern Industrial Pattern, Clean Energy Base & Computing Hub of Ningxia",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=8.0, color="#7f8c8d")
    fig.text(0.5, 0.012, "数据源：宁夏回族自治区‘十四五’现代产业体系规划 · 制作：《中国地理知识手册》",
             ha="center", va="bottom", fontsize=7.0, color="#7f8c8d")

    out_p = os.path.join(OUT_DIR, "fig31-00-4_宁夏回族自治区现代产业体系与宁东能源算力基地图.png")
    fig.savefig(out_p, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_p}")

# =============================================================================
# 5. 生态安全格局与引黄灌溉水系图 (fig31-00-5)
# =============================================================================
def gen_fig5():
    print("Generating fig31-00-5 (Ecology & Irrigation)...")
    fig, ax = plt.subplots(figsize=(9.2, 12.0), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    nx_cities.plot(ax=ax, facecolor="#f4f6f7", edgecolor="#a6acaf", lw=0.7, zorder=3)
    gpd.GeoSeries([nx_union]).boundary.plot(ax=ax, color="#1a252f", lw=1.6, zorder=5)

    # 1. 黄河主干流贯穿 (中卫黑山峡-沙坡头-青铜峡-银川-石嘴山惠农)
    yr_pts = [
        (104.750, 37.380), (104.990, 37.460), (105.190, 37.515), (105.650, 37.500),
        (105.990, 37.890), (106.050, 37.950), (106.180, 38.050), (106.310, 38.300),
        (106.450, 38.650), (106.700, 39.100), (106.820, 39.360)
    ]
    ax.plot([to_alb(p[0], p[1])[0] for p in yr_pts], [to_alb(p[0], p[1])[1] for p in yr_pts],
            color="#2980b9", lw=3.8, ls="-", zorder=8, label="黄河干流 (流经宁夏397公里)")

    # 2. 引黄古灌区干渠 (秦渠 / 汉渠 / 唐徕渠 / 惠农渠)
    tl_pts = [(105.990, 37.890), (106.100, 38.200), (106.230, 38.500), (106.510, 38.950)]
    ax.plot([to_alb(p[0], p[1])[0] for p in tl_pts], [to_alb(p[0], p[1])[1] for p in tl_pts],
            color="#1abc9c", lw=2.0, ls="-", zorder=7, label="唐徕渠 / 汉延渠 (两千年世界灌溉工程遗产)")

    hn_pts = [(106.050, 37.950), (106.250, 38.350), (106.650, 39.150)]
    ax.plot([to_alb(p[0], p[1])[0] for p in hn_pts], [to_alb(p[0], p[1])[1] for p in hn_pts],
            color="#16a085", lw=1.8, ls="--", zorder=7, label="惠农渠 / 秦渠 / 汉渠")

    # 3. 主要支流：清水河 / 苦水河 / 泾河源
    qs_pts = [(106.260, 36.150), (106.050, 36.650), (105.800, 37.100), (105.660, 37.420)]
    ax.plot([to_alb(p[0], p[1])[0] for p in qs_pts], [to_alb(p[0], p[1])[1] for p in qs_pts],
            color="#5dade2", lw=1.8, ls="-.", zorder=7, label="清水河 (向北汇入黄河)")

    jh_pts = [(106.310, 35.460), (106.350, 35.350)]
    ax.plot([to_alb(p[0], p[1])[0] for p in jh_pts], [to_alb(p[0], p[1])[1] for p in jh_pts],
            color="#2471a3", lw=2.0, ls="-", zorder=7, label="泾河源头 (向南涵养关中八水)")

    # 核心生态安全屏障区 (多边形/椭圆示意)
    # 贺兰山生态屏障
    hl_poly = [(105.75, 38.40), (105.95, 38.40), (106.00, 39.10), (105.80, 39.10)]
    hl_alb = [to_alb(p[0], p[1]) for p in hl_poly]
    ax.add_patch(Polygon(hl_alb, facecolor="#27ae60", alpha=0.25, edgecolor="#1e8449", lw=1.5, zorder=4))
    ax.text(to_alb(105.88, 38.75)[0], to_alb(105.88, 38.75)[1], "贺兰山国家级生态屏障\n(阻截腾格里沙漠与西北寒风)",
            fontsize=7.8, fontweight="bold", color="#145a32", ha="center", va="center", zorder=12,
            path_effects=[pe.withStroke(linewidth=2.0, foreground="#ffffff")])

    # 六盘山生态屏障
    lp_poly = [(106.10, 35.35), (106.40, 35.35), (106.40, 35.80), (106.10, 35.80)]
    lp_alb = [to_alb(p[0], p[1]) for p in lp_poly]
    ax.add_patch(Polygon(lp_alb, facecolor="#27ae60", alpha=0.25, edgecolor="#1e8449", lw=1.5, zorder=4))
    ax.text(to_alb(106.25, 35.58)[0], to_alb(106.25, 35.58)[1], "六盘山高原生态绿岛\n(黄土高原水源涵养屏障)",
            fontsize=7.8, fontweight="bold", color="#145a32", ha="center", va="center", zorder=12,
            path_effects=[pe.withStroke(linewidth=2.0, foreground="#ffffff")])

    # 罗山干旱绿岛
    ro_poly = [(106.20, 37.10), (106.42, 37.10), (106.42, 37.30), (106.20, 37.30)]
    ro_alb = [to_alb(p[0], p[1]) for p in ro_poly]
    ax.add_patch(Polygon(ro_alb, facecolor="#27ae60", alpha=0.25, edgecolor="#1e8449", lw=1.2, zorder=4))
    ax.text(to_alb(106.31, 37.20)[0], to_alb(106.31, 37.20)[1], "罗山荒漠生态绿岛",
            fontsize=7.2, fontweight="bold", color="#145a32", ha="center", va="center", zorder=12,
            path_effects=[pe.withStroke(linewidth=2.0, foreground="#ffffff")])

    # 名胜湖泊湿地
    lakes = [
        ("沙湖生态旅游区 (5A)", 106.375, 38.790),
        ("阅海国家湿地公园", 106.210, 38.530),
        ("星海湖城市湿地", 106.400, 39.030),
        ("青铜峡水利枢纽", 105.990, 37.890),
        ("沙坡头麦草方格治沙带", 104.990, 37.460)
    ]
    for lname, llon, llat in lakes:
        lx, ly = to_alb(llon, llat)
        ax.plot(lx, ly, "o", color="#2980b9", markersize=5.0, zorder=14)
        ax.annotate(lname, xy=(lx, ly), xytext=(lx + 5000, ly - 3000),
                    fontsize=7.0, fontweight="bold", color="#1b4f72", zorder=15,
                    path_effects=[pe.withStroke(linewidth=1.8, foreground="#ffffff")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    add_scalebar(ax, ax_xlim[0] + span_x * 0.08, ax_ylim[0] + span_y * 0.06, length_km=60)
    add_compass(ax, 0.90, 0.94)

    leg = ax.legend(loc="upper left", bbox_to_anchor=(0.03, 0.98), fontsize=7.4,
                    framealpha=0.92, facecolor="#ffffff", edgecolor="#bdc3c7")

    ax.set_title("宁夏回族自治区生态安全格局与引黄灌溉水系图", fontsize=13.0, fontweight="bold", pad=20, color=C_TEXT)
    ax.text(0.5, 1.008, "Ecological Security Framework & Yellow River Irrigation System in Ningxia",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=8.0, color="#7f8c8d")
    fig.text(0.5, 0.012, "数据源：宁夏生态保护红线与水利发展规划 · 制作：《中国地理知识手册》",
             ha="center", va="bottom", fontsize=7.0, color="#7f8c8d")

    out_p = os.path.join(OUT_DIR, "fig31-00-5_宁夏回族自治区生态安全格局与引黄灌溉水系图.png")
    fig.savefig(out_p, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_p}")

if __name__ == "__main__":
    gen_fig1()
    gen_fig2()
    gen_fig3()
    gen_fig4()
    gen_fig5()
    print("\n✓ All 5 Ningxia provincial overview figures generated successfully!")
