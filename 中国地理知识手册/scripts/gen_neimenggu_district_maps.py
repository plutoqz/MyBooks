# -*- coding: utf-8 -*-
"""内蒙古自治区各盟市分幅地图自动化生成引擎
支持 12 个盟市（29-01 至 29-12）：
1. fig{sec_id}-1_{name}行政区位图.png
2. fig{sec_id}-2_{name}地形地貌图.png
3. fig{sec_id}-3_{name}道路交通图.png
4. fig{sec_id}-4_{name}特色专题图.png
5. fig{sec_id}-5_{name}夜间灯光与经济发展演进图.png

严格对标海淀/石家庄/太原基准：整体字号微缩、杜绝文字压盖、要素清晰呼应、机器零冲突。
"""
import os
import sys
import argparse
import zipfile
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
from shapely.validation import make_valid

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, r"D:\code\Ideas\MyBooks\中国地理知识手册\scripts")
from style import ALBERS, C_TEXT, DATA, DPI, FIGURES, setup
from neimenggu_district_configs import NEIMENGGU_CONFIGS
from prov_pipeline import prov_dem
import mapkit

setup()
OUT_DIR = FIGURES
os.makedirs(OUT_DIR, exist_ok=True)
_T = Transformer.from_crs("EPSG:4326", ALBERS, always_xy=True)

def to_alb(lon, lat):
    return _T.transform(lon, lat)

PLACE_KIND_LABEL = {
    "gov": "党委政府驻地 / 行政核心",
    "subdistrict": "核心城区 / 街道办事处",
    "town": "重点城镇 / 乡村振兴支点",
    "tech": "先进产业园区 / 科创新极",
    "station": "综合交通枢纽 / 站场空港",
    "scenic": "名胜古迹 / 自然风景名胜",
    "_default": "重要节点",
}

PLACE_STYLE = {
    "gov":        dict(color="#78281f", mcolor="#c0392b", marker="*", fs=8.0, ms=9.5, pri=0, z=16, weight="bold"),
    "subdistrict":dict(color="#935116", mcolor="#d35400", marker="s", fs=7.0, ms=5.2, pri=1, z=15, weight="bold"),
    "town":       dict(color="#145a32", mcolor="#196f3d", marker="^", fs=7.0, ms=5.5, pri=1, z=15, weight="bold"),
    "tech":       dict(color="#6c3483", mcolor="#8e44ad", marker="D", fs=7.0, ms=5.2, pri=2, z=14, weight="bold"),
    "station":    dict(color="#154360", mcolor="#1f618d", marker="P", fs=7.0, ms=5.8, pri=1, z=15, weight="bold"),
    "scenic":     dict(color="#7d6608", mcolor="#b7950b", marker="p", fs=6.8, ms=5.2, pri=3, z=13, weight="normal"),
    "_default":   dict(color="#2c3e50", mcolor="#566573", marker="o", fs=6.5, ms=4.0, pri=4, z=12, weight="normal"),
}

_KIND_ALIAS = {
    "subdistrict": "town",
    "industry": "tech",
    "airport": "station",
    "eco": "scenic"
}

def safe_clip(gdf, mask_geom):
    if gdf is None or len(gdf) == 0:
        return gdf
    mask_clean = make_valid(mask_geom)
    try:
        sub = gdf[gdf.intersects(mask_clean.envelope)].copy()
        if len(sub) == 0:
            return sub
        sub['geometry'] = sub['geometry'].apply(make_valid)
        return gpd.clip(sub, mask_clean)
    except Exception:
        pass
    try:
        mask_buf = mask_clean.buffer(0)
        return gpd.clip(gdf, mask_buf)
    except Exception:
        return gdf[gdf.intersects(mask_clean)].copy()

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

def add_scalebar(ax, x0, y0, length_km=20):
    mapkit.add_scalebar(ax, x0, y0, length_km=length_km)

def add_compass(ax, x=0.94, y=0.91):
    ax.annotate("N", xy=(x, y), xytext=(x, y - 0.055), transform=ax.transAxes,
                arrowprops=dict(facecolor="#2c3e50", edgecolor="#2c3e50", width=1.8, headwidth=5.5, headlength=6.5),
                ha="center", va="center", fontsize=9.2, fontweight="bold", color="#2c3e50", zorder=30)

def get_clean_root(name):
    for suffix in ['满族蒙古族自治县', '达斡尔族自治旗', '鄂伦春自治旗', '鄂温克族自治旗', '自治旗', '联合旗', '前旗', '中旗', '后旗', '旗', '市', '县', '区']:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    return name.strip()

print("Initializing base datasets for Inner Mongolia district maps...")
DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")
nm_prov = gpd.read_file(os.path.join(DATAV_DIR, "150000_full.json")).to_crs(ALBERS)
dem_nm, dem_minx, dem_maxy, dem_res = prov_dem("150000", zoom=9, res=300.0)

nl_clean_df = pd.read_csv(os.path.join(DATA_DIR, "neimenggu_nightlight_clean.csv"))

# 加载解压好的 OSM 矢量
osm_dir = os.path.join(DATA_DIR, "transport", "neimenggu")
roads_shp = os.path.join(osm_dir, "gis_osm_roads_free_1.shp")

roads_full = None
rails_full = None
waterways_full = None
water_a_full = None

if os.path.exists(roads_shp):
    try:
        print("Loading Inner Mongolia OSM shapefiles...")
        roads_full = gpd.read_file(roads_shp)
        rails_full = gpd.read_file(os.path.join(osm_dir, "gis_osm_railways_free_1.shp"))
        waterways_full = gpd.read_file(os.path.join(osm_dir, "gis_osm_waterways_free_1.shp"))
        water_a_full = gpd.read_file(os.path.join(osm_dir, "gis_osm_water_a_free_1.shp"))
        print("Inner Mongolia OSM shapefiles successfully loaded.")
    except Exception as e:
        print(f"Warning: could not load OSM shapefiles: {e}")

print("Base spatial environments ready.")

def get_unit_geometry_and_subunits(adcode, cfg):
    unit_gdf = nm_prov[nm_prov['adcode'].astype(str) == str(adcode)]
    sub_file = os.path.join(DATAV_DIR, f"{adcode}_full.json")
    if os.path.exists(sub_file):
        subunits_gdf = gpd.read_file(sub_file).to_crs(ALBERS)
    else:
        subunits_gdf = unit_gdf.copy()
    return unit_gdf, subunits_gdf

def generate_district_maps(adcode):
    cfg = NEIMENGGU_CONFIGS.get(str(adcode))
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

    unit_gdf, subunits_gdf = get_unit_geometry_and_subunits(adcode, cfg)
    u_geom = unit_gdf.union_all()
    db = unit_gdf.total_bounds

    span_x = db[2] - db[0]
    span_y = db[3] - db[1]
    max_span = max(span_x, span_y)

    pad = max_span * 0.08
    ax_xlim = (db[0] - pad, db[2] + pad)
    ax_ylim = (db[1] - pad, db[3] + pad)

    _ar = (ax_ylim[1] - ax_ylim[0]) / max(ax_xlim[1] - ax_xlim[0], 1e-9)
    _w = 9.6 / _ar if _ar >= 1 else 9.6
    _w = max(5.6, min(9.6, _w))
    _h = min(10.8, _w * _ar)
    FIGSIZE = (_w, max(5.2, _h))

    # 比例尺位置：右下角
    sb_x0 = ax_xlim[0] + (ax_xlim[1] - ax_xlim[0]) * 0.62
    sb_y0 = ax_ylim[0] + (ax_ylim[1] - ax_ylim[0]) * 0.055

    # 裁剪水体与交通图层
    roads_d = gpd.GeoDataFrame()
    rails_d = gpd.GeoDataFrame()
    waterways_d = gpd.GeoDataFrame()
    water_a_d = gpd.GeoDataFrame()

    if roads_full is not None:
        d_bounds_wgs = unit_gdf.to_crs("EPSG:4326").total_bounds
        pad_wgs = 0.10
        bbox_wgs = (d_bounds_wgs[0] - pad_wgs, d_bounds_wgs[1] - pad_wgs, d_bounds_wgs[2] + pad_wgs, d_bounds_wgs[3] + pad_wgs)

        try:
            roads_clip = roads_full.cx[bbox_wgs[0]:bbox_wgs[2], bbox_wgs[1]:bbox_wgs[3]]
            rails_clip = rails_full.cx[bbox_wgs[0]:bbox_wgs[2], bbox_wgs[1]:bbox_wgs[3]]
            waterways_clip = waterways_full.cx[bbox_wgs[0]:bbox_wgs[2], bbox_wgs[1]:bbox_wgs[3]]
            water_a_clip = water_a_full.cx[bbox_wgs[0]:bbox_wgs[2], bbox_wgs[1]:bbox_wgs[3]]

            roads_osm = roads_clip.to_crs(ALBERS) if len(roads_clip) > 0 else gpd.GeoDataFrame(crs=ALBERS)
            rails_osm = rails_clip.to_crs(ALBERS) if len(rails_clip) > 0 else gpd.GeoDataFrame(crs=ALBERS)
            waterways_osm = waterways_clip.to_crs(ALBERS) if len(waterways_clip) > 0 else gpd.GeoDataFrame(crs=ALBERS)
            water_a_osm = water_a_clip.to_crs(ALBERS) if len(water_a_clip) > 0 else gpd.GeoDataFrame(crs=ALBERS)

            roads_d = safe_clip(roads_osm, u_geom)
            rails_d = safe_clip(rails_osm, u_geom)
            waterways_d = safe_clip(waterways_osm, u_geom)
            water_a_d = safe_clip(water_a_osm, u_geom)
        except Exception as e:
            print(f"OSM clip warning: {e}")

    # 裁剪 DEM
    dx_pad, dy_pad = 8000.0, 8000.0
    x0, y0, x1, y1 = db[0] - dx_pad, db[1] - dy_pad, db[2] + dx_pad, db[3] + dy_pad
    c0 = max(0, int((x0 - dem_minx) / dem_res))
    c1 = min(dem_nm.shape[1], int((x1 - dem_minx) / dem_res) + 1)
    r0 = max(0, int((dem_maxy - y1) / dem_res))
    r1 = min(dem_nm.shape[0], int((dem_maxy - y0) / dem_res) + 1)

    sub_dem = dem_nm[r0:r1, c0:c1].copy()
    sub_minx = dem_minx + c0 * dem_res
    sub_maxy = dem_maxy - r0 * dem_res
    sub_extent = (sub_minx, sub_minx + sub_dem.shape[1] * dem_res,
                  sub_maxy - sub_dem.shape[0] * dem_res, sub_maxy)

    scale_mult = max(1.0, scale_km / 2.0)

    # =========================================================================
    # Map 1: 行政区位图
    # =========================================================================
    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    subunits_gdf.plot(ax=ax, facecolor="#f8f9fa", edgecolor="#7f8c8d", lw=0.6, ls=":", zorder=3)
    unit_gdf.boundary.plot(ax=ax, edgecolor="#1a5276", lw=2.0, zorder=4)

    admin_covered = set()
    for p in cfg.get("places_admin", []):
        pname = p[0].split("(")[0].strip()
        for sfx in ["管委会", "市政府", "行政公署", "城关", "县城", "矿区", "园区", "口岸区"]:
            if pname.endswith(sfx):
                base = pname[:-len(sfx)].strip()
                if base:
                    admin_covered.add(base)
                    r = get_clean_root(base)
                    if r:
                        admin_covered.add(r)
        admin_covered.add(pname)
        admin_covered.add(get_clean_root(pname))

    if len(water_a_d) > 0:
        water_a_d.plot(ax=ax, facecolor="#d4e6f1", edgecolor="#a9cce3", lw=0.4, zorder=6)
    if len(waterways_d) > 0:
        waterways_d.plot(ax=ax, color="#7fb3d5", lw=0.8, zorder=7)

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    sl = mapkit.SymbolLabels(ax, fig)
    sl.reserve([(0.50, 0.0, 1.0, 0.09),      # 比例尺
                (0.88, 0.86, 1.0, 1.0)])     # 指北针
    for pname, plon, plat, ox, oy, ptype in cfg.get("places_admin", []):
        px, py = to_alb(plon, plat)
        ptype = _KIND_ALIAS.get(ptype, ptype)
        k = ptype if ptype in PLACE_STYLE else "_default"
        st = PLACE_STYLE.get(k, PLACE_STYLE["_default"])
        nm, nt = mapkit.split_note(pname)
        sl.add(px, py, nm, k, note=nt, priority=st["pri"],
               marker=st["marker"], face=st["mcolor"], size=st["ms"],
               kind_label=PLACE_KIND_LABEL.get(k, "其他地物"))
    sym_type_h, sym_idx_h = sl.flush()

    placer = mapkit.LabelPlacer(ax, fig)
    _vi = 0
    for _, srow in subunits_gdf.iterrows():
        sname = srow.get("name", "")
        if not sname or sname == name or len(subunits_gdf) <= 1:
            continue
        s_root = get_clean_root(sname)
        if sname in admin_covered or (len(s_root) >= 2 and s_root in admin_covered):
            continue
        scx, scy = srow.geometry.centroid.x, srow.geometry.centroid.y
        _vi += 1
        placer.add(scx, scy, sname, color="#566573", fs=7.2, priority=90 + _vi,
                   weight="normal", leader=False, zorder=12, max_radius=0.8)
    placer.flush()

    add_scalebar(ax, sb_x0, sb_y0, length_km=scale_km)
    add_compass(ax, 0.055, 0.885)

    leg_elements = [Patch(facecolor="none", edgecolor="#1a5276", linewidth=1.8,
                          label=f"{name}辖域边界")]
    leg = mapkit.stacked_legends(ax, [
        dict(handles=leg_elements + sym_type_h, title="符号含义",
             ncol=3, fontsize=7.0, title_fontsize=7.6),
        dict(handles=sym_idx_h, title="图上编号对照（编号标注于符号旁）",
             ncol=2, fontsize=7.0, title_fontsize=7.6),
    ], top=-0.010, gap=0.014)

    # 鹰眼全区示意图
    inset_ax = fig.add_axes([0.74, 0.72, 0.22, 0.22])
    nm_prov.plot(ax=inset_ax, facecolor="#f2f4f4", edgecolor="#bdc3c7", lw=0.5)
    unit_gdf.plot(ax=inset_ax, facecolor="#c0392b", edgecolor="#78281f", lw=1.0)
    inset_ax.set_aspect("equal")
    inset_ax.axis("off")
    inset_ax.text(0.5, 0.02, f"{name}在全区位置", transform=inset_ax.transAxes,
                  ha="center", fontsize=6.8, color="#2c3e50", fontweight="bold")

    ax.set_title(f"内蒙古自治区{name}行政区划与区位图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
    ax.text(0.5, 1.008, f"Administrative Boundary & Localities of {en_name}", transform=ax.transAxes,
            ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
    mapkit.footer_below_legend(
        ax, leg, "底图数据：自然资源部 / 阿里云 DataV · 审图号：GS(2021)6038号 · 制作：《中国地理知识手册》",
        fontsize=6.5)

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
    colors = [
        (0.00, "#85c1e9"),   # 水体与低地 (平原/河滩)
        (0.12, "#a9dfbf"),
        (0.28, "#d4efdf"),
        (0.45, "#f9e79f"),   # 草原台地暖黄
        (0.65, "#edbb99"),   # 丘陵中山棕褐
        (0.85, "#ba4a00"),   # 高中山深褐
        (1.00, "#fdfefe")    # 极顶灰白
    ]
    cmap = LinearSegmentedColormap.from_list(f"{name}_elev", colors, N=256)
    norm = Normalize(vmin=max(0.0, e_min), vmax=e_max)

    valid = np.nan_to_num(sub_dem, nan=e_min)
    valid = np.clip(valid, norm.vmin, norm.vmax)
    rgb = cmap(norm(valid))[:, :, :3]
    rgb_shaded = rgb * (0.42 + 0.58 * hs[:, :, np.newaxis])

    im = ax.imshow(rgb_shaded, extent=sub_extent, origin="upper", zorder=3)
    patch = get_mpl_clip_patch(u_geom)
    ax.add_patch(patch)
    im.set_clip_path(patch)

    unit_gdf.boundary.plot(ax=ax, color="#1a252f", lw=1.5, zorder=5)

    if len(water_a_d) > 0:
        water_a_d.plot(ax=ax, facecolor="#5dade2", edgecolor="#2980b9", lw=0.4, zorder=6)
    if len(waterways_d) > 0:
        waterways_d.plot(ax=ax, color="#2980b9", lw=0.9, zorder=7)

    # 标注水体
    for wname, wlon, wlat, rot in cfg.get("water_labels", []):
        wx, wy = to_alb(wlon, wlat)
        if db[0] - 15000 <= wx <= db[2] + 15000 and db[1] - 15000 <= wy <= db[3] + 15000:
            ax.text(wx, wy, wname, fontsize=7.2, color="#1b4f72", style="italic", fontweight="bold",
                    ha="center", va="center", rotation=rot, zorder=12,
                    path_effects=[pe.withStroke(linewidth=1.8, foreground="#ffffff")])

    # 标注山峰高点与极值
    for pname, plon, plat, elev, ox, oy, side in cfg.get("peaks", []):
        px, py = to_alb(plon, plat)
        tx, ty = px + ox * scale_mult, py + oy * scale_mult
        ha = "left" if side == "left" else "right"
        marker_color = "#b03a2e" if elev > 1000 else "#27ae60"
        ax.plot(px, py, "^" if elev > 1000 else "v", color=marker_color, markersize=6.2, zorder=12)
        ax.annotate(pname, xy=(px, py), xytext=(tx, ty),
                    arrowprops=dict(arrowstyle="-", color="#7f8c8d", lw=0.6),
                    fontsize=7.0, fontweight="bold", color="#78281f", ha=ha, va="center", zorder=15,
                    path_effects=[pe.withStroke(linewidth=2.0, foreground="#ffffff")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    add_scalebar(ax, sb_x0, sb_y0, length_km=scale_km)
    add_compass(ax, 0.94, 0.91)

    cax = ax.inset_axes([0.04, 0.06, 0.025, 0.22])
    cb = plt.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cax, orientation="vertical")
    cb.set_label("高程 Elevation (m)", fontsize=6.8, color="#2c3e50")
    cb.ax.tick_params(labelsize=6.0, length=2.0)

    ax.set_title(f"内蒙古自治区{name}地形地貌与水文格局图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
    ax.text(0.5, 1.008, f"Topography, Relief & Hydrological Pattern of {en_name}", transform=ax.transAxes,
            ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
    fig.text(0.5, 0.015, "数据源：AWS Terrain GLO-30 30m DEM · 投影：Albers 等积圆锥 · 制作：《中国地理知识手册》",
             ha="center", va="bottom", fontsize=6.5, color="#7f8c8d")

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

    unit_gdf.plot(ax=ax, facecolor="#fdfefe", edgecolor="#7f8c8d", lw=1.2, zorder=3)
    subunits_gdf.boundary.plot(ax=ax, color="#d5dbdb", lw=0.5, ls=":", zorder=3)

    if len(water_a_d) > 0:
        water_a_d.plot(ax=ax, facecolor="#ebf5fb", edgecolor="#aed6f1", lw=0.4, zorder=4)

    road_layers = []
    if len(roads_d) > 0:
        road_layers = mapkit.classify_roads(roads_d)
        mapkit.draw_roads(ax, road_layers)

    if len(rails_d) > 0:
        rails_d.plot(ax=ax, color="#2c3e50", lw=1.3, ls="-", zorder=11)

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    sl = mapkit.SymbolLabels(ax, fig)
    sl.reserve([(0.0, 0.0, 0.36, 0.28),      # 图例
                (0.50, 0.0, 1.0, 0.09),      # 比例尺
                (0.90, 0.84, 1.0, 1.0)])     # 指北针

    for sname, slon, slat, ox, oy, stype, ha, va in cfg.get("stations", []):
        sx, sy = to_alb(slon, slat)
        kind = "airport" if stype == "airport" else "rail_hub"
        nm, nt = mapkit.split_note(sname)
        sl.add(sx, sy, nm, kind, note=nt)

    for cname, clon, clat, rot in cfg.get("corridors", []):
        cx_c, cy_c = to_alb(clon, clat)
        if db[0] <= cx_c <= db[2] and db[1] <= cy_c <= db[3]:
            nm, nt = mapkit.split_note(cname)
            sl.add(cx_c, cy_c, nm, "corridor", note=nt)
    sym_type_h, sym_idx_h = sl.flush()

    add_scalebar(ax, sb_x0, sb_y0, length_km=scale_km)
    add_compass(ax, 0.955, 0.90)

    leg_elements = mapkit.road_legend_handles(road_layers, include_minor=True) if road_layers else [
        Line2D([0], [0], color="#2c3e50", lw=1.5, label="国家铁路与重载能源大干线"),
        Line2D([0], [0], color="#e67e22", lw=1.5, label="国家高速公路骨架网")
    ]
    leg = mapkit.stacked_legends(ax, [
        dict(handles=leg_elements + sym_type_h, title="线型与符号含义",
             ncol=3, fontsize=6.8, title_fontsize=7.6),
        dict(handles=sym_idx_h, title="图上编号对照（编号标注于符号旁）",
             ncol=2, fontsize=6.8, title_fontsize=7.6),
    ], top=-0.010, gap=0.013)

    ax.set_title(f"内蒙古自治区{name}道路交通与综合枢纽图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
    ax.text(0.5, 1.008, f"Transportation Network & Hubs of {en_name}", transform=ax.transAxes,
            ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
    mapkit.footer_below_legend(
        ax, leg,
        "数据源：OpenStreetMap · 中国国家铁路集团 · 交通运输部 · 制作：《中国地理知识手册》",
        fontsize=6.5)

    m3_path = os.path.join(OUT_DIR, f"fig{sec_id}-3_{name}道路交通图.png")
    fig.savefig(m3_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Map 3 saved: {m3_path}")

    # =========================================================================
    # Map 4: 特色专题图
    # =========================================================================
    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    unit_gdf.plot(ax=ax, facecolor="#fefefe", edgecolor="#1a5276", lw=1.5, zorder=3)
    subunits_gdf.boundary.plot(ax=ax, color="#d5dbdb", lw=0.6, ls=":", zorder=3)

    if len(water_a_d) > 0:
        water_a_d.plot(ax=ax, facecolor="#ebf5fb", edgecolor="#aed6f1", lw=0.4, zorder=4)

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    theme_elements = cfg.get("theme_elements", [])
    sl = mapkit.SymbolLabels(ax, fig)
    sl.reserve([(0.50, 0.0, 1.0, 0.09),      # 比例尺
                (0.88, 0.86, 1.0, 1.0)])     # 指北针

    theme_palette = [
    ("#c0392b", "o", "重大文保/历史遗存"),
    ("#1f618d", "s", "现代制造/战略新兴"),
    ("#196f3d", "^", "生态涵养/水利名胜"),
    ("#d35400", "D", "特色农业/绿色粮牧"),
    ("#7d3c98", "p", "能源战略/口岸开放"),
        ("#16a085", "h", "海洋经济/水利港航工程"),
        ("#b7950b", "*", "农业示范/现代乡村振兴基地"),
        ("#2c3e50", "v", "综合枢纽/关键物流集散中心"),
        ("#e74c3c", "P", "重大科研院所/国家创新中心"),
        ("#2980b9", "X", "数字经济/大数据算力枢纽"),
        ("#27ae60", "d", "地质遗迹/国家地质公园"),
        ("#8e44ad", "8", "文旅融合/国家级度假区"),
        ("#a04000", "<", "能源电力/特高压与新能源基地"),
        ("#117864", ">", "生物医药/生命健康产业示范区"),
        ("#283747", "H", "高端装备/航空航天产业基地"),
        ("#ba4a00", "s", "商贸物流/国际陆港枢纽")

    ]

    for idx, item in enumerate(theme_elements):
        tname = item[0]
        tlon = item[1]
        tlat = item[2]
        tdesc = item[3] if len(item) > 3 else ""
        tx, ty = to_alb(tlon, tlat)
        color, marker, kind_label = theme_palette[idx % len(theme_palette)]
        nm, nt = mapkit.split_note(tname)
        note_str = tdesc if tdesc else nt
        sl.add(tx, ty, nm, f"thm_{idx}", note=note_str, priority=1,
               marker=marker, face=color, size=7.2,
               kind_label=kind_label)

    sym_type_h, sym_idx_h = sl.flush()

    add_scalebar(ax, sb_x0, sb_y0, length_km=scale_km)
    add_compass(ax, 0.94, 0.91)

    leg = mapkit.stacked_legends(ax, [
        dict(handles=sym_type_h, title="符号类型含义",
             ncol=3, fontsize=7.0, title_fontsize=7.6),
        dict(handles=sym_idx_h, title="图上特色要素编号对照（编号标注于符号旁）",
             ncol=1, fontsize=6.8, title_fontsize=7.6),
    ], top=-0.010, gap=0.014)

    ax.set_title(f"内蒙古自治区{name}特色专题图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
    ax.text(0.5, 1.008, f"Thematic Features of {en_name}", transform=ax.transAxes,
            ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
    mapkit.footer_below_legend(
        ax, leg, "数据源：地方发展规划与重点特色产业导录 · 制作：《中国地理知识手册》",
        fontsize=6.5)

    m4_path = os.path.join(OUT_DIR, f"fig{sec_id}-4_{name}特色专题图.png")
    fig.savefig(m4_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Map 4 saved: {m4_path}")

    # =========================================================================
    # Map 5: 夜间灯光与经济发展演进图
    # =========================================================================
    fig, (ax_nl, ax_gdp) = plt.subplots(2, 1, figsize=(9.5, 8.5), dpi=DPI)
    fig.patch.set_facecolor("white")

    # 提取该盟市夜光时序
    nl_sub = nl_clean_df[nl_clean_df["city_name"] == name].groupby("year")["sum"].sum().reset_index()

    if len(nl_sub) > 0:
        years = nl_sub["year"].values
        sums = nl_sub["sum"].values
        ax_nl.plot(years, sums, color="#d35400", lw=2.0, marker="o", markersize=3.5, label="夜间灯光辐射总量 (DN·Pixel)")
        ax_nl.fill_between(years, sums, color="#fdebd0", alpha=0.5)

        for y_pt, s_pt, tx, ty, note in cfg.get("nl_annotations", []):
            ax_nl.annotate(note, xy=(y_pt, s_pt), xytext=(tx, ty),
                           arrowprops=dict(arrowstyle="->", color="#c0392b", lw=0.8),
                           fontsize=6.8, fontweight="bold", color="#78281f",
                           bbox=dict(boxstyle="round,pad=0.2", facecolor="#ffffff", edgecolor="#e74c3c", alpha=0.9))

    ax_nl.set_title(f"{name} 1986—2024 年夜间灯光辐射时序跃迁演进", fontsize=10.5, fontweight="bold", color=C_TEXT)
    ax_nl.set_ylabel("夜光总量辐射积分", fontsize=7.5, color="#2c3e50")
    ax_nl.grid(True, linestyle="--", alpha=0.4)
    ax_nl.tick_params(labelsize=7.0)

    # 下半部分：历年 GDP 柱状图
    gdp_series = cfg.get("gdp_series", {})
    if gdp_series:
        gyears = list(gdp_series.keys())
        gvals = list(gdp_series.values())
        bars = ax_gdp.bar(gyears, gvals, width=1.5, color="#2980b9", edgecolor="#1b4f72", alpha=0.85, label="地区生产总值 (GDP, 亿元)")
        for bar in bars:
            h = bar.get_height()
            ax_gdp.text(bar.get_x() + bar.get_width() / 2.0, h + max(gvals) * 0.015, f"{h:g}",
                        ha="center", va="bottom", fontsize=6.5, fontweight="bold", color="#1b4f72")

    ax_gdp.set_title(f"{name} 2000—2024 年经济总量 (GDP) 跨越式跃升", fontsize=10.5, fontweight="bold", color=C_TEXT)
    ax_gdp.set_ylabel("GDP (亿元)", fontsize=7.5, color="#2c3e50")
    ax_gdp.set_xlabel("年份 Year", fontsize=7.5, color="#2c3e50")
    ax_gdp.grid(True, linestyle="--", alpha=0.4)
    ax_gdp.tick_params(labelsize=7.0)

    fig.tight_layout(pad=2.5)
    fig.text(0.5, 0.01, "数据来源：夜间灯光数据集 (1986-2024) · 内蒙古统计年鉴与历年国民经济和社会发展统计公报 · 制作：《中国地理知识手册》",
             ha="center", va="bottom", fontsize=6.5, color="#7f8c8d")

    m5_path = os.path.join(OUT_DIR, f"fig{sec_id}-5_{name}夜间灯光与经济发展演进图.png")
    fig.savefig(m5_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Map 5 saved: {m5_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Inner Mongolia district maps")
    parser.add_argument("--adcode", type=str, default=None, help="Target ADCODE (e.g. 150100)")
    args = parser.parse_args()

    if args.adcode:
        generate_district_maps(args.adcode)
    else:
        adcodes = sorted(list(NEIMENGGU_CONFIGS.keys()))
        for adc in adcodes:
            generate_district_maps(adc)
    print("\nAll requested Inner Mongolia district maps generated successfully!")
