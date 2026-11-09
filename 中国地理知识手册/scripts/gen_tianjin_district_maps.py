# -*- coding: utf-8 -*-
"""天津市各区分幅地图自动化生成引擎
支持 16 个区（120101 至 120119）：
1. fig{sec_id}-1_{name}行政区位图.png
2. fig{sec_id}-2_{name}地形地貌图.png
3. fig{sec_id}-3_{name}道路交通图.png
4. fig{sec_id}-4_{name}特色专题图.png
5. fig{sec_id}-5_{name}夜间灯光与经济发展演进图.png

严格遵循用户要求：整体字号调小 15-20%，杜绝文字压盖与边界切角。
"""
import os
import sys
import argparse
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
from rasterio.transform import from_origin
from rasterio.features import rasterize
from pyproj import Transformer

sys.path.insert(0, r"D:\code\Ideas\MyBooks\中国地理知识手册\scripts")
from style import ALBERS, C_TEXT, DATA, DPI, FIGURES, setup
from tianjin_district_configs import DISTRICT_CONFIGS
from prov_pipeline import prov_dem
import mapkit

setup()
OUT_DIR = FIGURES
os.makedirs(OUT_DIR, exist_ok=True)
_T = Transformer.from_crs("EPSG:4326", ALBERS, always_xy=True)

def to_alb(lon, lat):
    return _T.transform(lon, lat)

def is_clean_line(geom):
    """温和过滤：只剔除两点跨度 >2.2km 的孤立直线（OSM 拼接错误）。

    旧实现按相邻顶点间距整条丢弃要素，会误杀立交、隧道、跨河段等正常道路，
    导致路网断裂与主城区空洞。详见 mapkit.clean_lines。
    """
    if geom is None:
        return False
    if geom.geom_type == "LineString":
        coords = list(geom.coords)
        if len(coords) == 2:
            p1, p2 = coords[0], coords[1]
            dist_deg = ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**0.5
            if dist_deg > 0.022:
                return False
        return True
    elif geom.geom_type == "MultiLineString":
        return any(is_clean_line(part) for part in geom.geoms)
    return True

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

def add_scalebar(ax, x0, y0, length_km=5):
    mapkit.add_scalebar(ax, x0, y0, length_km=length_km)

def add_compass(ax, x=0.955, y=0.90):
    mapkit.add_compass(ax, x, y)

print("Loading base spatial layers for Tianjin...")
DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
tj_all = gpd.read_file(os.path.join(DATA_DIR, "boundaries", "datav", "120000_full.json")).to_crs(ALBERS)
dem_tj, dem_minx, dem_maxy, dem_res = prov_dem("120000", zoom=9, res=300.0)
osm_dir = os.path.join(DATA_DIR, "transport", "tianjin")
nl_clean_df = pd.read_csv(os.path.join(DATA_DIR, "tianjin_nightlight_clean.csv"))

# 加载全局矢量水系与路网以备裁剪
print("Reading Tianjin OSM shapefiles...")
roads_full = gpd.read_file(os.path.join(osm_dir, "gis_osm_roads_free_1.shp"))
rails_full = gpd.read_file(os.path.join(osm_dir, "gis_osm_railways_free_1.shp"))
waterways_full = gpd.read_file(os.path.join(osm_dir, "gis_osm_waterways_free_1.shp"))
water_a_full = gpd.read_file(os.path.join(osm_dir, "gis_osm_water_a_free_1.shp"))
print("Base spatial layers ready.")

def generate_district_maps(adcode):
    cfg = DISTRICT_CONFIGS.get(str(adcode))
    if not cfg:
        print(f"Error: ADCODE {adcode} not found in configs!")
        return

    sec_id = cfg["sec_id"]
    name = cfg["name"]
    en_name = cfg["en_name"]
    scale_km = cfg["scale_km"]
    print(f"\n==========================================")
    print(f"Generating maps for {sec_id} {name} ({en_name})...")
    print(f"==========================================")

    district = tj_all[tj_all["name"] == name]
    if len(district) == 0:
        district = tj_all[tj_all["adcode"] == int(adcode)]
    d_geom = district.geometry.iloc[0]
    db = district.total_bounds

    # 视口与中心计算：上方留出 8% 充裕空间，比例尺与图例互不干扰
    cx = (db[0] + db[2]) / 2.0
    cy = (db[1] + db[3]) / 2.0
    span_x = db[2] - db[0]
    span_y = db[3] - db[1]
    max_span = max(span_x, span_y)

    # 视口按辖区真实宽高比扩展，不再强制接近正方形。
    # 旧写法 half_span_x / half_span_y 都取自 max_span，和平、河西这类南北长条
    # 辖区会被塞进方框，左右各空掉三成画布；图例外置后浪费更明显。
    pad = max_span * 0.09
    ax_xlim = (db[0] - pad, db[2] + pad)
    ax_ylim = (db[1] - pad, db[3] + pad)

    # 画布随宽高比自适应，长边固定，短边按比例收，并设上下限防止退化
    _ar = (ax_ylim[1] - ax_ylim[0]) / max(ax_xlim[1] - ax_xlim[0], 1e-9)
    _w = 9.6 / _ar if _ar >= 1 else 9.6
    _w = max(5.6, min(9.6, _w))
    _h = min(10.8, _w * _ar)
    FIGSIZE = (_w, max(5.2, _h))

    # 比例尺位置：右下角
    sb_x0 = ax_xlim[0] + (ax_xlim[1] - ax_xlim[0]) * 0.64
    sb_y0 = ax_ylim[0] + (ax_ylim[1] - ax_ylim[0]) * 0.055

    # 裁剪 OSM 图层
    d_bounds_wgs = district.to_crs("EPSG:4326").total_bounds
    pad_wgs = 0.05
    bbox_wgs = (d_bounds_wgs[0] - pad_wgs, d_bounds_wgs[1] - pad_wgs, d_bounds_wgs[2] + pad_wgs, d_bounds_wgs[3] + pad_wgs)

    # 局部相交提取并转为 ALBERS 投影
    roads_clip = roads_full.cx[bbox_wgs[0]:bbox_wgs[2], bbox_wgs[1]:bbox_wgs[3]]
    rails_clip = rails_full.cx[bbox_wgs[0]:bbox_wgs[2], bbox_wgs[1]:bbox_wgs[3]]
    waterways_clip = waterways_full.cx[bbox_wgs[0]:bbox_wgs[2], bbox_wgs[1]:bbox_wgs[3]]
    water_a_clip = water_a_full.cx[bbox_wgs[0]:bbox_wgs[2], bbox_wgs[1]:bbox_wgs[3]]

    roads_osm = roads_clip.to_crs(ALBERS) if len(roads_clip) > 0 else gpd.GeoDataFrame(columns=roads_full.columns, geometry="geometry", crs=ALBERS)
    rails_osm = rails_clip.to_crs(ALBERS) if len(rails_clip) > 0 else gpd.GeoDataFrame(columns=rails_full.columns, geometry="geometry", crs=ALBERS)
    waterways_osm = waterways_clip.to_crs(ALBERS) if len(waterways_clip) > 0 else gpd.GeoDataFrame(columns=waterways_full.columns, geometry="geometry", crs=ALBERS)
    water_a_osm = water_a_clip.to_crs(ALBERS) if len(water_a_clip) > 0 else gpd.GeoDataFrame(columns=water_a_full.columns, geometry="geometry", crs=ALBERS)

    roads_d = gpd.clip(roads_osm, d_geom) if len(roads_osm) > 0 else roads_osm
    rails_d = gpd.clip(rails_osm, d_geom) if len(rails_osm) > 0 else rails_osm
    waterways_d = gpd.clip(waterways_osm, d_geom) if len(waterways_osm) > 0 else waterways_osm
    water_a_d = gpd.clip(water_a_osm, d_geom) if len(water_a_osm) > 0 else water_a_osm

    # 裁剪 DEM
    dx_pad, dy_pad = 2500.0, 2500.0
    x0, y0, x1, y1 = db[0] - dx_pad, db[1] - dy_pad, db[2] + dx_pad, db[3] + dy_pad
    c0 = max(0, int((x0 - dem_minx) / dem_res))
    c1 = min(dem_tj.shape[1], int((x1 - dem_minx) / dem_res) + 1)
    r0 = max(0, int((dem_maxy - y1) / dem_res))
    r1 = min(dem_tj.shape[0], int((dem_maxy - y0) / dem_res) + 1)

    sub_dem = dem_tj[r0:r1, c0:c1].copy()
    sub_minx = dem_minx + c0 * dem_res
    sub_maxy = dem_maxy - r0 * dem_res
    sub_extent = (sub_minx, sub_minx + sub_dem.shape[1] * dem_res,
                  sub_maxy - sub_dem.shape[0] * dem_res, sub_maxy)

    # =========================================================================
    # Map 1: 行政区位图
    # =========================================================================
    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    district.plot(ax=ax, facecolor="#f4f8fa", edgecolor="#1a5276", lw=2.2, zorder=3)
    if len(water_a_d) > 0:
        water_a_d.plot(ax=ax, facecolor="#d4e6f1", edgecolor="#a9cce3", lw=0.5, zorder=4)
    if len(waterways_d) > 0:
        waterways_d.plot(ax=ax, color="#7fb3d5", lw=1.2, zorder=5)

    # 图面零文字：地物只画「符号 + 编号」，名称与含义统一进图外图例。
    # 旧版是逐个 ox/oy 固定偏移 annotate，和平、河西这种 20 km² 的小区里
    # 十几条 12~18 字的地名无论如何错位都会互相压字。
    # 注意：SymbolLabels 依赖真实 xlim/ylim 换算像素距离，必须先定视口。
    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")
    sl = mapkit.SymbolLabels(ax, fig)
    sl.reserve([(0.50, 0.0, 1.0, 0.09),      # 比例尺
                (0.88, 0.84, 1.0, 1.0)])     # 指北针
    TJ_PLACE = {
        "gov":         ("*", "#c0392b", 11.0, "区政府驻地", 0),
        "town":        ("s", "#d35400", 6.4, "主要街镇", 1),
        "tech":        ("D", "#8e44ad", 6.4, "核心产业 / 园区", 2),
        # 交通枢纽改深蓝：旧 #c0392b 与街镇 #d35400 同为方块、dE 仅 25。
        "station":     ("s", "#1f618d", 6.6, "交通枢纽", 1),
        "scenic":      ("o", "#27ae60", 6.0, "历史名胜 / 生态文博", 3),
        "edu":         ("^", "#2980b9", 6.4, "教育科研机构", 2),
    }
    # 同标签同符号的类型合并成一个 kind：旧表 station/airport/port 三个
    # kind 三种颜色却都叫"交通枢纽"，图例出重复行、读者反而要多记两种
    # 颜色；合并后一个含义一种符号，图例只列一行。
    _KIND_ALIAS = {"subdistrict": "town", "industry": "tech",
                   "airport": "station", "port": "station", "eco": "scenic"}
    for pname, plon, plat, ox, oy, ptype in cfg["places_admin"]:
        px, py = to_alb(plon, plat)
        ptype = _KIND_ALIAS.get(ptype, ptype)
        mkr, col, msz, klab, pri = TJ_PLACE.get(
            ptype, ("o", "#566573", 5.8, "其他地物", 4))
        k = ptype if ptype in TJ_PLACE else "_other"
        nm, nt = mapkit.split_note(pname)
        sl.add(px, py, nm, k, note=nt, priority=pri,
               marker=mkr, face=col, size=msz, kind_label=klab)
    sym_type_h, sym_idx_h = sl.flush()

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    add_scalebar(ax, sb_x0, sb_y0, length_km=scale_km)
    add_compass(ax, 0.94, 0.91)

    leg_elements = [Patch(facecolor="none", edgecolor="#1a5276", linewidth=1.8,
                          label=f"{name}辖区边界")]
    leg = mapkit.stacked_legends(ax, [
        dict(handles=leg_elements + sym_type_h, title="符号含义",
             ncol=3, fontsize=7.0, title_fontsize=7.8),
        dict(handles=sym_idx_h, title="图上编号对照（编号标注于符号旁）",
             ncol=2, fontsize=7.0, title_fontsize=7.8),
    ], top=-0.010, gap=0.014)

    # 右上角天津市域鹰眼图
    inset_ax = fig.add_axes([0.74, 0.72, 0.22, 0.22])
    tj_all.plot(ax=inset_ax, facecolor="#f2f4f4", edgecolor="#bdc3c7", lw=0.6)
    district.plot(ax=inset_ax, facecolor="#c0392b", edgecolor="#78281f", lw=1.2)
    inset_ax.set_aspect("equal")
    inset_ax.axis("off")
    inset_ax.text(0.5, 0.02, f"{name}在全市的位置", transform=inset_ax.transAxes,
                  ha="center", fontsize=7.0, color="#2c3e50", fontweight="bold")

    ax.set_title(f"天津市{name}行政区划与区位图", fontsize=13.0, fontweight="bold", pad=24, color=C_TEXT)
    ax.text(0.5, 1.008, f"Administrative Boundary & Localities of {en_name}", transform=ax.transAxes,
            ha="center", va="bottom", fontsize=7.8, color="#7f8c8d")
    mapkit.footer_below_legend(
        ax, leg, "底图数据：自然资源部 / 阿里云 DataV · 审图号：GS(2021)6038号 · 制作：《中国地理知识手册》",
        fontsize=6.8)

    m1_path = os.path.join(OUT_DIR, f"fig{sec_id}-1_{name}行政区位图.png")
    fig.savefig(m1_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Map 1 saved: {m1_path}")

    # =========================================================================
    # Map 2: 地形地貌图
    # =========================================================================
    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    hs = calc_hillshade(sub_dem, dem_res)
    e_min, e_max = cfg["elev_range"]
    if e_max <= 50.0:
        # 低平原与洼淀区：使用嫩绿、黄绿到暖金阶梯
        colors = [
            (0.00, "#a8d8b9"),
            (0.25, "#c8e6c9"),
            (0.50, "#dce775"),
            (0.75, "#fff59d"),
            (1.00, "#ffe082")
        ]
        cmap = LinearSegmentedColormap.from_list(f"{name}_elev", colors, N=256)
        norm = Normalize(vmin=e_min, vmax=e_max)
    else:
        # 北部山地区（蓟州）：从平原绿、低山黄、中山橙到高山峰褐
        colors = [
            (0.00, "#a8d8b9"),
            (0.06, "#c8e6c9"),
            (0.15, "#ffd54f"),
            (0.35, "#ff8a65"),
            (0.65, "#a1887f"),
            (1.00, "#4e342e")
        ]
        cmap = LinearSegmentedColormap.from_list(f"{name}_elev", colors, N=256)
        norm = Normalize(vmin=0, vmax=e_max)

    rgba = cmap(norm(sub_dem))
    h_weight = 0.52
    hs_c = np.clip(hs, 0, 1)
    for i in range(3):
        rgba[..., i] = rgba[..., i] * (1.0 - h_weight + h_weight * hs_c)

    patch = get_mpl_clip_patch(d_geom)
    ax.add_patch(patch)
    im = ax.imshow(rgba, extent=sub_extent, origin="upper", interpolation="bilinear", zorder=2)
    im.set_clip_path(patch)

    district.boundary.plot(ax=ax, color="#1c2833", lw=2.0, zorder=5)
    if len(water_a_d) > 0:
        water_a_d.plot(ax=ax, facecolor="#a9cce3", edgecolor="#7fb3d5", lw=0.4, alpha=0.85, zorder=6)
    if len(waterways_d) > 0:
        waterways_d.plot(ax=ax, color="#2980b9", lw=1.2, zorder=7)

    for wname, wlon, wlat, rot in cfg["water_labels"]:
        wx, wy = to_alb(wlon, wlat)
        ax.text(wx, wy, wname, fontsize=7.2, color="#154360", fontweight="bold", rotation=rot,
                ha="center", va="center", zorder=8,
                path_effects=[pe.withStroke(linewidth=2.2, foreground="white")])

    # 山峰注记的偏移倍率（原定义在 Map 1 段，Map 1 改符号化后需在此重建）
    scale_mult = max(1.0, scale_km / 2.0)
    for pname, plon, plat, elev, ox, oy, ha in cfg["peaks"]:
        px, py = to_alb(plon, plat)
        tx, ty = px + ox * scale_mult, py + oy * scale_mult
        if elev > 400:
            ax.plot(px, py, marker="^", color="#78281f", markersize=7.5, markeredgecolor="white", markeredgewidth=0.8, zorder=10)
            ax.text(tx, ty, pname, fontsize=7.2, fontweight="bold", color="#641e16", ha=ha, va="center", zorder=11,
                    path_effects=[pe.withStroke(linewidth=2.2, foreground="white")])
        elif elev > 50:
            ax.plot(px, py, marker="^", color="#af601a", markersize=6.2, markeredgecolor="white", markeredgewidth=0.8, zorder=10)
            ax.text(tx, ty, pname, fontsize=7.0, fontweight="bold", color="#7e5109", ha=ha, va="center", zorder=11,
                    path_effects=[pe.withStroke(linewidth=2.2, foreground="white")])
        else:
            ax.text(tx, ty, pname, fontsize=7.0, color="#196f3d", ha=ha, va="center", zorder=11,
                    path_effects=[pe.withStroke(linewidth=2.2, foreground="white")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    add_scalebar(ax, sb_x0, sb_y0, length_km=scale_km)
    add_compass(ax, 0.94, 0.91)

    # 左下角高程色带
    cbar_ax = fig.add_axes([0.08, 0.08, 0.20, 0.015])
    cbar = fig.colorbar(matplotlib.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cbar_ax, orientation="horizontal")
    ticks = np.linspace(e_min, e_max, 5).astype(int)
    cbar.set_ticks(ticks)
    cbar.set_ticklabels([f"{t}m" for t in ticks])
    cbar_ax.tick_params(labelsize=6.8)
    cbar_ax.set_title("海拔高度 (米)", fontsize=7.2, pad=3, color="#2c3e50")

    ax.set_title(f"天津市{name}地形地貌与水系图", fontsize=13.0, fontweight="bold", pad=24, color=C_TEXT)
    ax.text(0.5, 1.008, f"Topography, Relief & Water Systems of {en_name}", transform=ax.transAxes,
            ha="center", va="bottom", fontsize=7.8, color="#7f8c8d")
    fig.text(0.5, 0.015, "数据源：AWS Terrarium / Copernicus GLO-30 DEM · 阿里云 DataV · 制作：《中国地理知识手册》",
             ha="center", va="bottom", fontsize=6.8, color="#7f8c8d")

    m2_path = os.path.join(OUT_DIR, f"fig{sec_id}-2_{name}地形地貌图.png")
    fig.savefig(m2_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Map 2 saved: {m2_path}")

    # =========================================================================
    # Map 3: 道路交通图
    # =========================================================================
    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    district.plot(ax=ax, facecolor="#fdfefe", edgecolor="#2c3e50", lw=2.0, zorder=2)
    if len(water_a_d) > 0:
        water_a_d.plot(ax=ax, facecolor="#ebf5fb", edgecolor="#d4e6f1", lw=0.4, zorder=3)
    if len(waterways_d) > 0:
        waterways_d.plot(ax=ax, color="#ebf5fb", lw=1.0, zorder=3)

    # 道路四层分级绘制（次级 → 主要 → 快速路 → 高速，逐层叠压）
    road_layers = mapkit.classify_roads(roads_d)
    mapkit.draw_roads(ax, road_layers)

    if len(rails_d) > 0:
        national_rail = rails_d[rails_d["fclass"].isin(["rail", "narrow_gauge"])]
        subway_rail = rails_d[rails_d["fclass"].isin(["subway", "light_rail"])]
        if len(national_rail) > 0:
            national_rail.plot(ax=ax, color="#1c2833", lw=1.9, zorder=11)
            national_rail.plot(ax=ax, color="white", lw=0.9, linestyle="--", zorder=12)
        if len(subway_rail) > 0:
            subway_rail.plot(ax=ax, color="#884ea0", lw=1.2, zorder=13)

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    # 图面零文字：要素只画「符号 + 编号」，名称与含义统一进图外图例
    sl = mapkit.SymbolLabels(ax, fig)
    sl.reserve([(0.0, 0.0, 0.38, 0.30),      # 图例
                (0.50, 0.0, 1.0, 0.09),      # 比例尺
                (0.90, 0.84, 1.0, 1.0)])     # 指北针
    for sname, slon, slat, ox, oy, stype, ha, va in cfg["stations"]:
        sx, sy = to_alb(slon, slat)
        kind = {"station": "rail_hub", "airport": "airport"}.get(stype, "metro")
        nm, nt = mapkit.split_note(sname)
        sl.add(sx, sy, nm, kind, note=nt)

    for cname, clon, clat, rot in cfg["corridors"]:
        cx_c, cy_c = to_alb(clon, clat)
        nm, nt = mapkit.split_note(cname)
        sl.add(cx_c, cy_c, nm, "corridor", note=nt)
    sym_type_h, sym_idx_h = sl.flush()

    add_scalebar(ax, sb_x0, sb_y0, length_km=scale_km)
    add_compass(ax, 0.955, 0.90)

    # 符号类条目由 SymbolLabels 统一给出，这里只保留线型与边界
    leg_elements = mapkit.road_legend_handles(road_layers, include_minor=True) + [
        Line2D([0], [0], color="#1c2833", lw=1.9, linestyle="-", label="国铁与高铁干线"),
        Line2D([0], [0], color="#884ea0", lw=1.2, label="城市轨道交通 / 地铁"),
        Patch(facecolor="none", edgecolor="#2c3e50", linewidth=1.8, label=f"{name}辖区边界")
    ]
    # 图例移到图幅外下方：loc="lower left" 落在图内左下角时会压住辖区边界
    # （和平区、红桥区最明显，边界正好穿过图例框），而且挤压西南部路网。
    leg = mapkit.stacked_legends(ax, [
        dict(handles=leg_elements + sym_type_h, title="线型与符号含义",
             ncol=3, fontsize=6.8, title_fontsize=7.6),
        dict(handles=sym_idx_h, title="图上编号对照（编号标注于符号旁）",
             ncol=2, fontsize=6.8, title_fontsize=7.6),
    ], top=-0.010, gap=0.013)

    ax.set_title(f"天津市{name}综合道路交通图", fontsize=13.0, fontweight="bold", pad=24, color=C_TEXT)
    ax.text(0.5, 1.008, f"Comprehensive Transportation Network of {en_name}", transform=ax.transAxes,
            ha="center", va="bottom", fontsize=7.8, color="#7f8c8d")
    mapkit.footer_below_legend(
        ax, leg,
        "数据源：OpenStreetMap (2026) · 中国铁路集团 · 天津轨道交通 · 制作：《中国地理知识手册》",
        fontsize=6.8)

    m3_path = os.path.join(OUT_DIR, f"fig{sec_id}-3_{name}道路交通图.png")
    fig.savefig(m3_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Map 3 saved: {m3_path}")

    # =========================================================================
    # Map 4: 特色专题图
    # =========================================================================
    thm = cfg["thematic"]
    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    district.plot(ax=ax, facecolor="#fbfcfc", edgecolor="#2c3e50", lw=2.0, zorder=2)
    if len(water_a_d) > 0:
        water_a_d.plot(ax=ax, facecolor="#eaf2f8", edgecolor="#d4e6f1", lw=0.4, zorder=3)
    if len(waterways_d) > 0:
        waterways_d.plot(ax=ax, color="#eaf2f8", lw=1.0, zorder=3)

    c_map = {
        "unesco": ("#c0392b", "^", 7.5),
        "heritage": ("#78281f", "s", 7.0),
        "history": ("#7d6608", "o", 6.2),
        "culture": ("#9c640c", "o", 6.5),
        "celebrity": ("#8e44ad", "o", 6.2),
        "red": ("#c0392b", "s", 7.0),
        "origin": ("#b03a2e", "*", 9.0),
        "commerce": ("#8e44ad", "D", 6.5),
        "finance": ("#1b4f72", "s", 7.0),
        "tech": ("#2471a3", "D", 6.8),
        "industry": ("#117864", "s", 6.8),
        "edu": ("#2874a6", "^", 6.8),
        "health": ("#27ae60", "s", 6.5),
        "med": ("#16a085", "D", 6.5),
        "port": ("#1f618d", "s", 7.5),
        "hub": ("#b03a2e", "s", 7.2),
        "aero": ("#2e4053", "D", 7.0),
        "expo": ("#9a7d0a", "s", 6.8),
        "eco": ("#1e8449", "o", 6.2),
        "wetland": ("#117864", "o", 6.5),
        "water": ("#1b4f72", "o", 6.5),
        "scenic": ("#27ae60", "o", 6.2),
        "tourism": ("#d35400", "o", 6.5),
        "spa": ("#1abc9c", "o", 6.5),
        "farm": ("#229954", "s", 6.5),
        "fishery": ("#2980b9", "o", 6.2),
        "geology": ("#148f77", "D", 7.0),
        "recycle": ("#d68910", "D", 6.8),
        "creative": ("#884ea0", "D", 6.5)
    }

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    # 图面零文字：专题要素只画「符号 + 编号」，名称与含义统一进图外图例
    lbl_of = dict(thm["legend_items"])
    sl = mapkit.SymbolLabels(ax, fig)
    sl.reserve([(0.50, 0.0, 1.0, 0.09),      # 比例尺
                (0.88, 0.84, 1.0, 1.0)])     # 指北针
    # 颜色按图内实际用到的类型现场分配（FIG_PALETTE 两两 ΔE≥32）。
    # 旧版 c_map 全局固定色在同一幅图里会产生同色/近色同形状的 pairing。
    _kind_order = []
    for fname, flon, flat, ftype, ox, oy in thm["features"]:
        k = ftype if ftype in lbl_of else "_other"
        if k not in _kind_order:
            _kind_order.append(k)
    _colors = mapkit.assign_colors(_kind_order)
    for fname, flon, flat, ftype, ox, oy in thm["features"]:
        fx, fy = to_alb(flon, flat)
        _col, mkr, msz = c_map.get(ftype, ("#2c3e50", "o", 6.2))
        nm, nt = mapkit.split_note(fname)
        k = ftype if ftype in lbl_of else "_other"
        sl.add(fx, fy, nm, k, note=nt, priority=1,
               marker=mkr, face=_colors[k], size=msz,
               kind_label=lbl_of.get(k, "其他专题要素"))
    sym_type_h, sym_idx_h = sl.flush()

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    add_scalebar(ax, sb_x0, sb_y0, length_km=scale_km)
    add_compass(ax, 0.94, 0.91)

    leg_elements = [Patch(facecolor="none", edgecolor="#2c3e50", linewidth=1.8,
                          label=f"{name}辖区边界")]
    leg = mapkit.stacked_legends(ax, [
        dict(handles=leg_elements + sym_type_h, title="符号含义",
             ncol=3, fontsize=7.0, title_fontsize=7.8),
        dict(handles=sym_idx_h, title="图上编号对照（编号标注于符号旁）",
             ncol=2, fontsize=7.0, title_fontsize=7.8),
    ], top=-0.010, gap=0.014)

    ax.set_title(thm["title"], fontsize=13.0, fontweight="bold", pad=24, color=C_TEXT)
    ax.text(0.5, 1.008, thm["en_title"], transform=ax.transAxes,
            ha="center", va="bottom", fontsize=7.8, color="#7f8c8d")
    mapkit.footer_below_legend(
        ax, leg, "数据源：天津市规划和自然资源局 · 天津市统计局 · 制作：《中国地理知识手册》",
        fontsize=6.8)

    m4_path = os.path.join(OUT_DIR, f"fig{sec_id}-4_{name}特色专题图.png")
    fig.savefig(m4_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Map 4 saved: {m4_path}")

    # =========================================================================
    # Map 5: 夜间灯光与 GDP 演进图
    # =========================================================================
    dist_nl = nl_clean_df[nl_clean_df["district_code"] == int(adcode)].sort_values("year").dropna(subset=["year", "sum"])
    gdp_data = cfg["gdp_series"]
    years_gdp = sorted(gdp_data.keys())
    values_gdp = [gdp_data[y] for y in years_gdp]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 5.0), dpi=DPI)
    fig.patch.set_facecolor("white")

    # 子图 1：夜间灯光
    ax1.set_facecolor("#fafbfc")
    years_nl = dist_nl["year"].values
    sum_nl = dist_nl["sum"].values

    ax1.plot(years_nl, sum_nl, color="#e67e22", lw=2.0, marker="o", markersize=3.8, label="夜光辐射总量 (sum)")
    ax1.fill_between(years_nl, sum_nl, color="#fdebd0", alpha=0.5)

    for x_p, y_p, x_t, y_t, note in cfg["nl_annotations"]:
        ax1.annotate(note, xy=(x_p, y_p), xytext=(x_t, y_t),
                     arrowprops=dict(arrowstyle="->", color="#c0392b", lw=0.9),
                     fontsize=7.0, color="#922b21", fontweight="bold",
                     bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#e6b0aa", alpha=0.9))

    ax1.set_title(f"{name}夜间灯光辐射总值变化 (1986—2024)", fontsize=10.0, fontweight="bold", color=C_TEXT, pad=8)
    ax1.set_xlabel("年份", fontsize=8.2)
    ax1.set_ylabel("夜间灯光辐射总量 (nW/cm²/sr)", fontsize=8.2)
    ax1.grid(True, linestyle="--", alpha=0.5)
    max_nl = max(sum_nl) if len(sum_nl) > 0 else 10000
    ax1.set_ylim(0, max_nl * 1.35)
    ax1.tick_params(labelsize=7.5)

    # 子图 2：GDP 演进
    ax2.set_facecolor("#fafbfc")
    bars = ax2.bar([str(y) for y in years_gdp], values_gdp, color="#2980b9", width=0.58, label=f"{name} GDP (亿元)")
    if len(bars) >= 2:
        bars[-2].set_color("#c0392b") # 2023
        bars[-1].set_color("#27ae60") # 2024

    for b in bars:
        h = b.get_height()
        ax2.text(b.get_x() + b.get_width()/2., h + max(values_gdp)*0.015, f"{int(h):d}",
                 ha="center", va="bottom", fontsize=7.0, color="#2c3e50")

    max_gdp = max(values_gdp)
    ax2.set_title(f"{name}地区生产总值（GDP）跨越历程", fontsize=10.0, fontweight="bold", color=C_TEXT, pad=8)
    ax2.set_xlabel("年份", fontsize=8.2)
    ax2.set_ylabel("地区生产总值 (亿元)", fontsize=8.2)
    ax2.grid(True, axis="y", linestyle="--", alpha=0.5)
    ax2.set_ylim(0, max_gdp * 1.25)
    ax2.tick_params(labelsize=7.5)

    fig.suptitle(f"天津市{name}空间经济活力演进：长时序夜光与 GDP 跨越式跃升 (1986—2024)",
                 fontsize=12.0, fontweight="bold", color=C_TEXT, y=0.98)
    fig.text(0.5, 0.015, f"数据来源：长时序夜间灯光数据 · 天津市及{name}国民经济和社会发展统计公报 · 制作：《中国地理知识手册》",
             ha="center", fontsize=7.0, color="#7f8c8d")

    plt.tight_layout(rect=[0, 0.04, 1, 0.94])
    m5_path = os.path.join(OUT_DIR, f"fig{sec_id}-5_{name}夜间灯光与经济发展演进图.png")
    fig.savefig(m5_path, dpi=DPI)
    plt.close(fig)
    print(f"Map 5 saved: {m5_path}")

    print(f"All 5 maps for {sec_id} {name} successfully generated!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--adcode", type=str, default="120101", help="District adcode (e.g. 120101) or 'all' or comma-separated list")
    args = parser.parse_args()

    if args.adcode == "all":
        for code in sorted(DISTRICT_CONFIGS.keys()):
            generate_district_maps(code)
    elif "," in args.adcode:
        for code in args.adcode.split(","):
            generate_district_maps(code.strip())
    else:
        generate_district_maps(args.adcode)
