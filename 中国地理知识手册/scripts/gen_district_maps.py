# -*- coding: utf-8 -*-
"""通用北京市各区分幅地图自动化生成引擎
支持 16 个区：
1. fig{sec_id}-1_{name}行政区位图.png
2. fig{sec_id}-2_{name}地形地貌图.png
3. fig{sec_id}-3_{name}道路交通图.png
4. fig{sec_id}-4_{name}特色专题图.png
5. fig{sec_id}-5_{name}夜间灯光与经济发展演进图.png
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
from beijing_district_configs import DISTRICT_CONFIGS
from prov_pipeline import prov_dem
import mapkit

setup()
OUT_DIR = FIGURES
os.makedirs(OUT_DIR, exist_ok=True)
_T = Transformer.from_crs("EPSG:4326", ALBERS, always_xy=True)

def to_alb(lon, lat):
    return _T.transform(lon, lat)

# 注记样式表：颜色 / 标记 / 字号 / 优先级（越小越优先占位）
PLACE_STYLE = {
    "gov":      dict(color="#78281f", mcolor="#c0392b", marker="*", fs=9.8, ms=11.5, pri=0, z=16),
    # 交通枢纽用深蓝：旧 #c0392b 与街镇的 #d35400 同为方块、dE 仅 25，
    # 图例里分不清；改蓝后 dE>45。
    "station":  dict(color="#154360", mcolor="#1f618d", marker="s", fs=8.5, ms=6.5,  pri=1, z=15),
    "town":     dict(color="#935116", mcolor="#d35400", marker="s", fs=8.6, ms=6.2,  pri=1, z=15),
    "tech":     dict(color="#6c3483", mcolor="#8e44ad", marker="D", fs=8.5, ms=6.2,  pri=2, z=14),
    "scenic":   dict(color="#196f3d", mcolor="#27ae60", marker="o", fs=8.2, ms=5.2,  pri=3, z=13),
    "_default": dict(color="#515a5a", mcolor="#566573", marker="o", fs=8.0, ms=6.2,  pri=4, z=12),
}

PLACE_KIND_LABEL = {
    "gov": "区政府驻地",
    "station": "交通枢纽",
    "town": "主要街镇 / 重点功能区",
    "tech": "产业 / 科技园区",
    "scenic": "历史名胜 / 生态文博",
    "_default": "其他地物",
}


def is_clean_line(geom):
    """温和过滤：只剔除两端点跨度 >2.2km 且仅两点的孤立直线（OSM 拼接错误）。

    旧实现只要任一相邻顶点间距 >1.5km（或两点线 >800m）就丢弃整条要素，
    会把立交、隧道、跨河段等正常道路误杀，直接导致路网断裂、悬空线头、
    主城区路网空洞。详见 mapkit.clean_lines 注释。
    """
    if geom is None:
        return False
    if geom.geom_type == "LineString":
        coords = list(geom.coords)
        if len(coords) == 2:
            p1, p2 = coords[0], coords[1]
            dist_deg = ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**0.5
            if dist_deg > 0.022:   # ≈2.2km 的孤立两点直线，判为拼接错误
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

print("Loading base spatial layers...")
DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
bj_all = gpd.read_file(os.path.join(DATA_DIR, "boundaries", "datav", "110000_full.json")).to_crs(ALBERS)
dem_bj, dem_minx, dem_maxy, dem_res = prov_dem("110000", zoom=9, res=300.0)
osm_dir = os.path.join(DATA_DIR, "transport", "beijing", "Beijing-shp", "shape")
nl_clean_df = pd.read_csv(os.path.join(DATA_DIR, "beijing_nightlight_clean.csv"))
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

    # 1. 辖区多边形与范围
    district = bj_all[bj_all["name"] == name]
    if len(district) == 0:
        district = bj_all[bj_all["adcode"] == int(adcode)]
    d_geom = district.geometry.iloc[0]
    db = district.total_bounds

    # 统一画幅中心与方形视口计算，确保居中且四角留白充足，图例与比例尺互不干扰
    cx = (db[0] + db[2]) / 2.0
    cy = (db[1] + db[3]) / 2.0
    span_x = db[2] - db[0]
    span_y = db[3] - db[1]
    max_span = max(span_x, span_y)

    # 视口按辖区真实宽高比扩展，不再强制正方形。
    # 旧写法 ax_xlim / ax_ylim 都用同一个 half_span，东城、西城这类南北长条
    # 辖区会被塞进方框，左右各空掉三成画布，地图本体只占中间窄窄一条；
    # 图例外置到图幅下方后这个浪费更刺眼。改为紧贴 bbox 加 8% 边距。
    pad = max_span * 0.08
    ax_xlim = (db[0] - pad, db[2] + pad)
    ax_ylim = (db[1] - pad, db[3] + pad)

    # 画布尺寸随宽高比自适应：长边固定，短边按比例收，并给上下限兜底，
    # 避免极扁（如东西向狭长辖区）时画布退化成一条。
    _ar = (ax_ylim[1] - ax_ylim[0]) / max(ax_xlim[1] - ax_xlim[0], 1e-9)
    _w = 9.6 / _ar if _ar >= 1 else 9.6
    _w = max(5.6, min(9.6, _w))
    _h = min(10.8, _w * _ar)
    FIGSIZE = (_w, max(5.2, _h))

    # 比例尺定位：固定在右下角安全区
    sb_x0 = ax_xlim[0] + (ax_xlim[1] - ax_xlim[0]) * 0.64
    sb_y0 = ax_ylim[0] + (ax_ylim[1] - ax_ylim[0]) * 0.055

    # 裁剪 OSM 数据
    d_bounds_wgs = district.to_crs("EPSG:4326").total_bounds
    pad_wgs = 0.05
    bbox_wgs = (d_bounds_wgs[0] - pad_wgs, d_bounds_wgs[1] - pad_wgs, d_bounds_wgs[2] + pad_wgs, d_bounds_wgs[3] + pad_wgs)

    roads_raw = gpd.read_file(os.path.join(osm_dir, "roads.shp"), bbox=bbox_wgs)
    water_raw = gpd.read_file(os.path.join(osm_dir, "waterways.shp"), bbox=bbox_wgs)
    rails_raw = gpd.read_file(os.path.join(osm_dir, "railways.shp"), bbox=bbox_wgs)

    if len(roads_raw) > 0:
        clean_mask = roads_raw.geometry.apply(is_clean_line)
        roads_osm = gpd.GeoDataFrame(roads_raw[clean_mask], geometry="geometry", crs=roads_raw.crs).to_crs(ALBERS)
    else:
        roads_osm = gpd.GeoDataFrame(columns=roads_raw.columns, geometry="geometry", crs=ALBERS)

    if len(water_raw) > 0:
        clean_mask = water_raw.geometry.apply(is_clean_line)
        water_osm = gpd.GeoDataFrame(water_raw[clean_mask], geometry="geometry", crs=water_raw.crs).to_crs(ALBERS)
    else:
        water_osm = gpd.GeoDataFrame(columns=water_raw.columns, geometry="geometry", crs=ALBERS)

    if len(rails_raw) > 0:
        clean_mask = rails_raw.geometry.apply(is_clean_line)
        rails_osm = gpd.GeoDataFrame(rails_raw[clean_mask], geometry="geometry", crs=rails_raw.crs).to_crs(ALBERS)
    else:
        rails_osm = gpd.GeoDataFrame(columns=rails_raw.columns, geometry="geometry", crs=ALBERS)

    roads_d = gpd.clip(roads_osm, d_geom) if len(roads_osm) > 0 else roads_osm
    water_d = gpd.clip(water_osm, d_geom) if len(water_osm) > 0 else water_osm
    rails_d = gpd.clip(rails_osm, d_geom) if len(rails_osm) > 0 else rails_osm

    # 裁剪 DEM
    dx_pad, dy_pad = 2000.0, 2000.0
    x0, y0, x1, y1 = db[0] - dx_pad, db[1] - dy_pad, db[2] + dx_pad, db[3] + dy_pad
    c0 = max(0, int((x0 - dem_minx) / dem_res))
    c1 = min(dem_bj.shape[1], int((x1 - dem_minx) / dem_res) + 1)
    r0 = max(0, int((dem_maxy - y1) / dem_res))
    r1 = min(dem_bj.shape[0], int((dem_maxy - y0) / dem_res) + 1)

    sub_dem = dem_bj[r0:r1, c0:c1].copy()
    sub_minx = dem_minx + c0 * dem_res
    sub_maxy = dem_maxy - r0 * dem_res
    sub_extent = (sub_minx, sub_minx + sub_dem.shape[1] * dem_res,
                  sub_maxy - sub_dem.shape[0] * dem_res, sub_maxy)

    tf = from_origin(sub_minx, sub_maxy, dem_res, dem_res)
    inside_mask = rasterize([(d_geom, 1)], out_shape=(sub_dem.shape[0], sub_dem.shape[1]), transform=tf, fill=0, dtype="uint8")

    # -------------------------------------------------------------------------
    # Map 1: 行政区位图
    # -------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    fig.subplots_adjust(left=0.012, right=0.795, top=0.945, bottom=0.012)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    district.plot(ax=ax, facecolor="#f4f8fa", edgecolor="#1a5276", lw=2.4, zorder=3)
    if len(water_d) > 0:
        water_d.plot(ax=ax, color="#7fb3d5", lw=1.2, zorder=4)

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    # 图面零文字：地物只画「符号 + 编号」，名称与含义统一进图外图例。
    # 行政区位图的地名动辄 12~18 字（「首钢工业遗址核心区（工业秀场）」），
    # 石景山 14 个地物挤在 84 km² 里，逐条避让全量审计仍记到 3 处叠字。
    sl = mapkit.SymbolLabels(ax, fig)
    sl.reserve([(0.50, 0.0, 1.0, 0.09),      # 比例尺
                (0.90, 0.84, 1.0, 1.0)])     # 指北针
    for pname, plon, plat, ox, oy, ptype in cfg["places_admin"]:
        px, py = to_alb(plon, plat)
        k = ptype if ptype in PLACE_STYLE else "_default"
        st = PLACE_STYLE[k]
        nm, nt = mapkit.split_note(pname)
        sl.add(px, py, nm, k, note=nt, priority=st["pri"],
               marker=st["marker"], face=st["mcolor"], size=st["ms"],
               kind_label=PLACE_KIND_LABEL.get(k, "其他地物"))
    sym_type_h, sym_idx_h = sl.flush()

    add_scalebar(ax, sb_x0, sb_y0, length_km=scale_km)
    add_compass(ax, 0.055, 0.885)

    leg_elements = [Patch(facecolor="none", edgecolor="#1a5276", linewidth=2.0,
                          label=f"{name}辖区边界")]
    leg = mapkit.stacked_legends(ax, [
        dict(handles=leg_elements + sym_type_h, title="符号含义",
             ncol=3, fontsize=8.0, title_fontsize=8.6),
        dict(handles=sym_idx_h, title="图上编号对照（编号标注于符号旁）",
             ncol=3, fontsize=8.0, title_fontsize=8.6),
    ], top=-0.010, gap=0.014)

    # 右上角北京市域鹰眼图
    inset_ax = fig.add_axes([0.805, 0.735, 0.185, 0.175])
    bj_all.plot(ax=inset_ax, facecolor="#f2f4f4", edgecolor="#bdc3c7", lw=0.6)
    district.plot(ax=inset_ax, facecolor="#c0392b", edgecolor="#78281f", lw=1.2)
    inset_ax.set_aspect("equal")
    inset_ax.axis("off")
    inset_ax.text(0.5, 0.02, f"{name}在全市的位置", transform=inset_ax.transAxes,
                  ha="center", fontsize=8.0, color="#2c3e50", fontweight="bold")

    ax.set_title(f"北京市{name}行政区划与区位图", fontsize=15, fontweight="bold", pad=26, color=C_TEXT)
    ax.text(0.5, 1.008, f"Administrative Boundary & Localities of {en_name}", transform=ax.transAxes,
            ha="center", va="bottom", fontsize=9.0, color="#7f8c8d")
    mapkit.footer_below_legend(
        ax, leg, "底图数据：自然资源部 / 阿里云 DataV · 审图号：GS(2021)6038号 · 制作：《中国地理知识手册》",
        fontsize=8.0)

    m1_path = os.path.join(OUT_DIR, f"fig{sec_id}-1_{name}行政区位图.png")
    fig.savefig(m1_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Map 1 saved: {m1_path}")

    # -------------------------------------------------------------------------
    # Map 2: 地形地貌图
    # -------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    hs = calc_hillshade(sub_dem, dem_res)
    colors = [
        (0.00, "#73a580"),
        (0.08, "#8bbd8b"),
        (0.20, "#c9bb86"),
        (0.40, "#c49257"),
        (0.70, "#9c6039"),
        (1.00, "#5a2b16")
    ]
    cmap = LinearSegmentedColormap.from_list(f"{name}_elev", colors, N=256)
    e_min, e_max = cfg["elev_range"]
    norm = Normalize(vmin=e_min, vmax=e_max)

    rgba = cmap(norm(sub_dem))
    h_weight = 0.52
    hs_c = np.clip(hs, 0, 1)
    for i in range(3):
        rgba[..., i] = rgba[..., i] * (1.0 - h_weight + h_weight * hs_c)

    patch = get_mpl_clip_patch(d_geom)
    ax.add_patch(patch)
    im = ax.imshow(rgba, extent=sub_extent, origin="upper", interpolation="bilinear", zorder=2)
    im.set_clip_path(patch)

    district.boundary.plot(ax=ax, color="#1c2833", lw=2.2, zorder=5)
    if len(water_d) > 0:
        water_d.plot(ax=ax, color="#2980b9", lw=1.5, zorder=6)

    for wname, wlon, wlat, rot in cfg["water_labels"]:
        wx, wy = to_alb(wlon, wlat)
        ax.text(wx, wy, wname, fontsize=8.6, color="#154360", fontweight="bold", rotation=rot,
                ha="center", va="center", zorder=7,
                path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    # 山峰注记：自动避让，按海拔分级符号
    placer = mapkit.LabelPlacer(ax, fig)
    mapkit.reserve_axes_boxes(placer, ax, [(0.02, 0.02, 0.40, 0.14),     # 高程色带
                                           (0.50, 0.0, 1.0, 0.09),      # 比例尺
                                           (0.90, 0.84, 1.0, 1.0)])     # 指北针
    for pname, plon, plat, elev, ox, oy, ha in cfg["peaks"]:
        px, py = to_alb(plon, plat)
        # max_radius 给到候选圈上限并加引线：地形图的「最低点」标签锚在辖区
        # 边缘（温榆河畔、马坊出境口），旁边就是图例/比例尺预留区，
        # 3.4 圈内根本没有空位，全量审计仍记到 2 处叠字。
        if elev > 500:
            placer.add(px, py, pname, color="#641e16", fs=8.8, priority=0,
                       marker="^", mcolor="#78281f", msize=8.5, zorder=12,
                       leader=True, max_radius=6.2)
        elif elev > 100:
            placer.add(px, py, pname, color="#7e5109", fs=8.4, priority=1,
                       marker="^", mcolor="#af601a", msize=7.0, zorder=11,
                       leader=True, max_radius=6.2)
        else:
            placer.add(px, py, pname, color="#196f3d", fs=8.2, priority=2, zorder=10,
                       leader=True, max_radius=10.5)
    placer.flush()

    add_scalebar(ax, sb_x0, sb_y0, length_km=scale_km)
    add_compass(ax, 0.955, 0.90)

    # 左下角高程色带
    cbar_ax = fig.add_axes([0.08, 0.08, 0.22, 0.016])
    cbar = fig.colorbar(matplotlib.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cbar_ax, orientation="horizontal")
    ticks = np.linspace(e_min, e_max, 5).astype(int)
    cbar.set_ticks(ticks)
    cbar.set_ticklabels([f"{t}m" for t in ticks])
    cbar_ax.tick_params(labelsize=7.5)
    cbar_ax.set_title("海拔高度 (米)", fontsize=8.2, pad=3, color="#2c3e50")

    ax.set_title(f"北京市{name}地形地貌与水系图", fontsize=15, fontweight="bold", pad=26, color=C_TEXT)
    ax.text(0.5, 1.008, f"Topography, Relief & Water Systems of {en_name}", transform=ax.transAxes,
            ha="center", va="bottom", fontsize=9.0, color="#7f8c8d")
    fig.text(0.5, 0.015, "数据源：AWS Terrarium / Copernicus GLO-30 DEM · 阿里云 DataV · 制作：《中国地理知识手册》",
             ha="center", va="bottom", fontsize=8.0, color="#7f8c8d")

    m2_path = os.path.join(OUT_DIR, f"fig{sec_id}-2_{name}地形地貌图.png")
    fig.savefig(m2_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Map 2 saved: {m2_path}")

    # -------------------------------------------------------------------------
    # Map 3: 道路交通图
    # -------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    district.plot(ax=ax, facecolor="#fdfefe", edgecolor="#2c3e50", lw=2.2, zorder=2)
    if len(water_d) > 0:
        water_d.plot(ax=ax, color="#ebf5fb", lw=1.2, zorder=3)

    # 道路四层分级绘制（次级 → 主要 → 快速路 → 高速，逐层叠压）
    road_layers = mapkit.classify_roads(roads_d)
    mapkit.draw_roads(ax, road_layers)

    if len(rails_d) > 0:
        national_rail = rails_d[rails_d["type"].isin(["rail", "narrow_gauge"])]
        if len(national_rail) > 0:
            national_rail = national_rail[national_rail.geometry.length > 350]
        subway_rail = rails_d[rails_d["type"].isin(["subway", "light_rail"])]
        if len(subway_rail) > 0:
            subway_rail = subway_rail[subway_rail.geometry.length > 200]
        if len(national_rail) > 0:
            national_rail.plot(ax=ax, color="#1c2833", lw=2.2, zorder=11)
            national_rail.plot(ax=ax, color="white", lw=1.1, linestyle="--", zorder=12)
        if len(subway_rail) > 0:
            subway_rail.plot(ax=ax, color="#884ea0", lw=1.4, zorder=13)

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    # 图面零文字：交通要素只画「符号 + 编号」，名称与含义统一进图外图例。
    # 区级图虽比市域图稀疏，但「东直门枢纽 (2/13/机场线)」一类标签仍有 14 字宽，
    # 两三个挤在换乘站密集处就会互压；统一符号化后图面无一处文字，彻底免疫。
    sl = mapkit.SymbolLabels(ax, fig)
    xl, yl = ax.get_xlim(), ax.get_ylim()
    wx, wy = xl[1] - xl[0], yl[1] - yl[0]
    sl.reserve([(0.0, 0.0, 0.40, 0.36),      # 图例
                (0.52, 0.0, 1.0, 0.10),      # 比例尺
                (0.90, 0.86, 1.0, 1.0)])     # 指北针

    for sname, slon, slat, ox, oy, stype, ha, va in cfg["stations"]:
        sx, sy = to_alb(slon, slat)
        kind = "rail_hub" if stype == "station" else "metro"
        nm, nt = mapkit.split_note(sname)
        sl.add(sx, sy, nm, kind, note=nt)

    for cname, clon, clat, rot in cfg["corridors"]:
        cx_c, cy_c = to_alb(clon, clat)
        nm, nt = mapkit.split_note(cname)
        sl.add(cx_c, cy_c, nm, "corridor", note=nt)
    sym_type_h, sym_idx_h = sl.flush()

    add_scalebar(ax, sb_x0, sb_y0, length_km=scale_km)
    add_compass(ax, 0.955, 0.90)

    # 符号类条目由 SymbolLabels 统一给出，这里只保留线型与边界，
    # 否则"客运特等/一级铁路枢纽"会和"铁路特等/一级客运枢纽"在图上列两遍。
    leg_elements = mapkit.road_legend_handles(road_layers, include_minor=True) + [
        Line2D([0], [0], color="#1c2833", lw=2.2, linestyle="-", label="国铁与高铁干线"),
        Line2D([0], [0], color="#884ea0", lw=1.4, label="城市轨道交通 / 地铁"),
        Patch(facecolor="none", edgecolor="#2c3e50", linewidth=2.0, label=f"{name}辖区边界")
    ]
    # 图例移到图幅外下方：图内左下角会压住辖区边界（西城、东城边界正穿过图例框）
    # 图例分两组堆叠到图幅下方：① 线型与符号含义 ② 图上编号对照
    leg = mapkit.stacked_legends(ax, [
        dict(handles=leg_elements + sym_type_h, title="线型与符号含义",
             ncol=3, fontsize=7.4, title_fontsize=8.2),
        dict(handles=sym_idx_h, title="图上编号对照（编号标注于符号旁）",
             ncol=2, fontsize=7.4, title_fontsize=8.2),
    ], top=-0.010, gap=0.014)

    ax.set_title(f"北京市{name}综合道路交通图", fontsize=15, fontweight="bold", pad=26, color=C_TEXT)
    ax.text(0.5, 1.008, f"Comprehensive Transportation Network of {en_name}", transform=ax.transAxes,
            ha="center", va="bottom", fontsize=9.0, color="#7f8c8d")
    mapkit.footer_below_legend(
        ax, leg,
        "数据源：OpenStreetMap (2026) · 中国铁路集团 · 北京地铁 · 制作：《中国地理知识手册》",
        fontsize=8.0)

    m3_path = os.path.join(OUT_DIR, f"fig{sec_id}-3_{name}道路交通图.png")
    fig.savefig(m3_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Map 3 saved: {m3_path}")

    # -------------------------------------------------------------------------
    # Map 4: 特色专题图
    # -------------------------------------------------------------------------
    thm = cfg["thematic"]
    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    fig.subplots_adjust(left=0.012, right=0.988, top=0.955, bottom=0.012)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    district.plot(ax=ax, facecolor="#fbfcfc", edgecolor="#2c3e50", lw=2.2, zorder=2)
    if len(water_d) > 0:
        water_d.plot(ax=ax, color="#eaf2f8", lw=1.2, zorder=3)

    c_map = {
        "unesco": ("#c0392b", "^", 8.5),
        "axis": ("#d35400", "s", 8.0),
        "history": ("#7d6608", "o", 7.0),
        "commerce": ("#8e44ad", "D", 7.0),
        "finance": ("#1b4f72", "s", 8.0),
        "culture": ("#9c640c", "o", 7.5),
        "tech": ("#2471a3", "D", 7.5),
        "cbd": ("#78281f", "s", 8.5),
        "olympic": ("#196f3d", "^", 8.0),
        "embassy": ("#2e4053", "o", 7.0),
        "global": ("#117864", "D", 7.0),
        "fbd": ("#b03a2e", "s", 8.5),
        "rail": ("#17202a", "s", 8.0),
        "eco": ("#1e8449", "o", 7.0),
        "heritage": ("#6e2c00", "s", 8.0),
        "temple": ("#7d6608", "^", 8.0),
        "village": ("#935116", "o", 7.0),
        "trail": ("#515a5a", "o", 6.5),
        "geopark": ("#148f77", "D", 8.0),
        "edu": ("#2874a6", "^", 7.5),
        "admin": ("#c0392b", "*", 11.0),
        "canal": ("#2980b9", "s", 8.0),
        "resort": ("#d68910", "o", 7.5),
        "art": ("#8e44ad", "D", 7.0),
        "airport": ("#1f618d", "s", 8.5),
        "trade": ("#2e4053", "D", 7.0),
        "expo": ("#9a7d0a", "s", 7.5),
        "energy": ("#b7950b", "D", 8.0),
        "bio": ("#229954", "D", 8.0),
        "greatwall": ("#78281f", "s", 8.0),
        "hydrogen": ("#2e86c1", "D", 7.5),
        "water": ("#1b4f72", "o", 7.5),
        "summit": ("#b03a2e", "^", 8.0),
        "cinema": ("#884ea0", "s", 7.5),
        "lake": ("#2874a6", "o", 7.5),
        "logistics": ("#34495e", "s", 7.5),
        "valley": ("#196f3d", "o", 7.0),
        "orchard": ("#d35400", "o", 7.0),
        "wetland": ("#117864", "o", 7.0),
        "scenic": ("#27ae60", "o", 7.0)
    }

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    # 图面零文字：专题要素只画「符号 + 编号」，名称与含义统一进图外图例
    lbl_of = dict(thm["legend_items"])
    sl = mapkit.SymbolLabels(ax, fig)
    sl.reserve([(0.50, 0.0, 1.0, 0.09),      # 比例尺
                (0.90, 0.84, 1.0, 1.0)])     # 指北针
    # 颜色按图内实际用到的类型现场分配（FIG_PALETTE 两两 ΔE≥32）。
    # 旧版 c_map 全局固定色：30 多个类型轮转十来个颜色，同一幅图两个
    # 类型拿到同色/近色（如 biomed vs _other 同为 #c0392b）的 pairing
    # 被全量审计记了 51 处 low_contrast。
    _kind_order = []
    for fname, flon, flat, ftype, ox, oy in thm["features"]:
        k = ftype if ftype in lbl_of else "_other"
        if k not in _kind_order:
            _kind_order.append(k)
    _colors = mapkit.assign_colors(_kind_order)
    for fname, flon, flat, ftype, ox, oy in thm["features"]:
        fx, fy = to_alb(flon, flat)
        _col, mkr, msz = c_map.get(ftype, ("#2c3e50", "o", 7.0))
        nm, nt = mapkit.split_note(fname)
        # 类型不在本图 legend_items 里的一律并入「其他专题要素」，
        # 否则同一图例会列出两三个同名的"专题要素"，读者无从对照。
        k = ftype if ftype in lbl_of else "_other"
        sl.add(fx, fy, nm, k, note=nt, priority=1,
               marker=mkr, face=_colors[k], size=msz,
               kind_label=lbl_of.get(k, "其他专题要素"))
    sym_type_h, sym_idx_h = sl.flush()

    add_scalebar(ax, sb_x0, sb_y0, length_km=scale_km)
    add_compass(ax, 0.955, 0.90)

    leg_elements = [Patch(facecolor="none", edgecolor="#2c3e50", linewidth=2.0,
                          label=f"{name}辖区边界")]
    leg = mapkit.stacked_legends(ax, [
        dict(handles=leg_elements + sym_type_h, title="符号含义",
             ncol=3, fontsize=8.0, title_fontsize=8.6),
        dict(handles=sym_idx_h, title="图上编号对照（编号标注于符号旁）",
             ncol=2, fontsize=8.0, title_fontsize=8.6),
    ], top=-0.010, gap=0.014)

    ax.set_title(thm["title"], fontsize=15, fontweight="bold", pad=26, color=C_TEXT)
    ax.text(0.5, 1.008, thm["en_title"], transform=ax.transAxes,
            ha="center", va="bottom", fontsize=9.0, color="#7f8c8d")
    mapkit.footer_below_legend(
        ax, leg, "数据源：北京市规划和自然资源委员会 · 北京市统计局 · 制作：《中国地理知识手册》",
        fontsize=8.0)

    if cfg.get("thematic_override"):
        # 海淀区第 4 幅由 update_haidian_maps.py 单独产出（重点高校与科研院所分布图），
        # 两个脚本各写一份 fig01-06-4 会互相覆盖，正文引用的那一版被"特色专题图"顶掉。
        print("Map 4 skipped: 由 update_haidian_maps.py 产出")
        plt.close(fig)
    else:
        m4_path = os.path.join(OUT_DIR, f"fig{sec_id}-4_{name}特色专题图.png")
        fig.savefig(m4_path, dpi=DPI, bbox_inches="tight")
        plt.close(fig)
        print(f"Map 4 saved: {m4_path}")

    # -------------------------------------------------------------------------
    # Map 5: 夜间灯光与 GDP 演进图
    # -------------------------------------------------------------------------
    dist_nl = nl_clean_df[nl_clean_df["district_code"] == int(adcode)].sort_values("year").dropna(subset=["year", "sum"])
    gdp_data = cfg["gdp_series"]
    years_gdp = sorted(gdp_data.keys())
    values_gdp = [gdp_data[y] for y in years_gdp]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5.2), dpi=DPI)
    fig.patch.set_facecolor("white")

    # 子图 1：夜间灯光
    ax1.set_facecolor("#fafbfc")
    years_nl = dist_nl["year"].values
    sum_nl = dist_nl["sum"].values

    ax1.plot(years_nl, sum_nl, color="#e67e22", lw=2.4, marker="o", markersize=4.5, label="夜光辐射总量 (sum)")
    ax1.fill_between(years_nl, sum_nl, color="#fdebd0", alpha=0.5)

    for x_p, y_p, x_t, y_t, note in cfg["nl_annotations"]:
        ax1.annotate(note, xy=(x_p, y_p), xytext=(x_t, y_t),
                     arrowprops=dict(arrowstyle="->", color="#c0392b", lw=1.0),
                     fontsize=8.2, color="#922b21", fontweight="bold",
                     bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#e6b0aa", alpha=0.9))

    ax1.set_title(f"{name}夜间灯光辐射总值变化 (1986—2024)", fontsize=11.5, fontweight="bold", color=C_TEXT, pad=10)
    ax1.set_xlabel("年份", fontsize=9.2)
    ax1.set_ylabel("夜间灯光辐射总量 (nW/cm²/sr)", fontsize=9.2)
    ax1.grid(True, linestyle="--", alpha=0.5)
    max_nl = max(sum_nl) if len(sum_nl) > 0 else 10000
    ax1.set_ylim(0, max_nl * 1.35)

    # 子图 2：GDP 演进
    ax2.set_facecolor("#fafbfc")
    bars = ax2.bar([str(y) for y in years_gdp], values_gdp, color="#2980b9", width=0.6, label=f"{name} GDP (亿元)")
    bars[-2].set_color("#c0392b") # 2023
    bars[-1].set_color("#27ae60") # 2024

    for b in bars:
        h = b.get_height()
        ax2.text(b.get_x() + b.get_width()/2., h + max(values_gdp)*0.015, f"{int(h):d}",
                 ha="center", va="bottom", fontsize=7.8, color="#2c3e50")

    max_gdp = max(values_gdp)
    ax2.set_title(f"{name}地区生产总值（GDP）跨越历程", fontsize=11.5, fontweight="bold", color=C_TEXT, pad=10)
    ax2.set_xlabel("年份", fontsize=9.2)
    ax2.set_ylabel("地区生产总值 (亿元)", fontsize=9.2)
    ax2.grid(True, axis="y", linestyle="--", alpha=0.5)
    ax2.set_ylim(0, max_gdp * 1.25)

    fig.suptitle(f"北京市{name}空间经济活力演进：长时序夜光与 GDP 跨越式跃升 (1986—2024)",
                 fontsize=13.5, fontweight="bold", color=C_TEXT, y=0.98)
    fig.text(0.5, 0.015, f"数据来源：长时序夜间灯光数据 · 北京市及{name}国民经济和社会发展统计公报 · 制作：《中国地理知识手册》",
             ha="center", fontsize=8.0, color="#7f8c8d")

    plt.tight_layout(rect=[0, 0.04, 1, 0.94])
    m5_path = os.path.join(OUT_DIR, f"fig{sec_id}-5_{name}夜间灯光与经济发展演进图.png")
    fig.savefig(m5_path, dpi=DPI)
    plt.close(fig)
    print(f"Map 5 saved: {m5_path}")

    # 此处原有「海淀区同时复制一份 fig01-05-* 别名」的兼容代码。
    # 正文（sections_vol2/01-06_海淀区.md）引用的是 fig01-06-*，别名没有消费者，
    # 却让 01-05 号段同时出现「石景山区」与「海淀区」两套图，图号重复、
    # 每次重跑都会复活，清掉又回来。已删除。

    print(f"All 5 maps for {sec_id} {name} successfully generated!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--adcode", type=str, default="110101", help="District adcode (e.g. 110101) or 'all'")
    args = parser.parse_args()

    if args.adcode == "all":
        for code in sorted(DISTRICT_CONFIGS.keys()):
            generate_district_maps(code)
    else:
        generate_district_maps(args.adcode)
