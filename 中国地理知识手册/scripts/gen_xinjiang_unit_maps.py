# -*- coding: utf-8 -*-
"""新疆维吾尔自治区各分单元地图自动化生成引擎
支持 7 个分析单元（32-01 至 32-07）：
1. fig{sec_id}-1_{name}行政区划图.png
2. fig{sec_id}-2_{name}地形地貌图.png
3. fig{sec_id}-3_{name}道路交通图.png
4. fig{sec_id}-4_{name}特色专题图.png
5. fig{sec_id}-5_{name}夜间灯光与经济发展演进图.png

严格遵循出版级规范：微缩字号、紧凑堆叠图例、完全杜绝压盖。
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
from pyproj import Transformer
from shapely.validation import make_valid

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, r"D:\code\Ideas\MyBooks\中国地理知识手册\scripts")
from style import ALBERS, C_TEXT, DATA, DPI, FIGURES, setup
from xinjiang_configs import XINJIANG_CONFIGS
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
    mapkit.add_scalebar(ax, x0, y0, length_km=length_km)

def add_compass(ax, x=0.94, y=0.91):
    ax.annotate("N", xy=(x, y), xytext=(x, y - 0.055), transform=ax.transAxes,
                arrowprops=dict(facecolor="#2c3e50", edgecolor="#2c3e50", width=1.8, headwidth=5.5, headlength=6.5),
                ha="center", va="center", fontsize=9.2, fontweight="bold", color="#2c3e50", zorder=30)

def get_clean_root(name):
    for suffix in ['柯尔克孜自治州', '蒙古自治州', '回族自治州', '哈萨克自治州', '自治州', '地区', '自治县', '县', '市', '区']:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    return name.strip()

print("Initializing base datasets for Xinjiang unit maps...")
DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")
xj_prov = gpd.read_file(os.path.join(DATAV_DIR, "650000_full.json")).to_crs(ALBERS)

dem_data = np.load(os.path.join(DATA_DIR, "dem", "province", "650000_z9.npz"))
dem_full = dem_data['dem']
dem_res = float(dem_data['res'])
dem_minx = float(dem_data['minx'])
dem_maxy = float(dem_data['maxy'])

nl_clean_df = pd.read_csv(os.path.join(DATA_DIR, "xinjiang_nightlight_clean.csv"))
print("Base spatial environments ready.")

def get_unit_geometry_and_subunits(adcode, cfg):
    if adcode in ["650100", "650200", "650400", "650500"]:
        unit_gdf = xj_prov[xj_prov['adcode'].astype(str) == str(adcode)].copy()
        sub_file = os.path.join(DATAV_DIR, f"{adcode}_full.json")
        if os.path.exists(sub_file):
            try:
                subunits_gdf = gpd.read_file(sub_file).to_crs(ALBERS)
            except Exception:
                subunits_gdf = unit_gdf.copy()
        else:
            subunits_gdf = unit_gdf.copy()
    elif adcode == "652000":  # 天山以北地州
        target_codes = ["652300", "652700", "654000", "654200", "654300"]
        unit_gdf = xj_prov[xj_prov['adcode'].astype(str).isin(target_codes)].copy()
        sub_list = []
        for c in target_codes:
            f = os.path.join(DATAV_DIR, f"{c}_full.json")
            if os.path.exists(f):
                try:
                    sub_list.append(gpd.read_file(f).to_crs(ALBERS))
                except Exception:
                    pass
        if sub_list:
            subunits_gdf = pd.concat(sub_list, ignore_index=True)
        else:
            subunits_gdf = unit_gdf.copy()
    elif adcode == "653000":  # 天山以南塔里木环盆地地州
        target_codes = ["652800", "652900", "653000", "653100", "653200"]
        unit_gdf = xj_prov[xj_prov['adcode'].astype(str).isin(target_codes)].copy()
        sub_list = []
        for c in target_codes:
            f = os.path.join(DATAV_DIR, f"{c}_full.json")
            if os.path.exists(f):
                try:
                    sub_list.append(gpd.read_file(f).to_crs(ALBERS))
                except Exception:
                    pass
        if sub_list:
            subunits_gdf = pd.concat(sub_list, ignore_index=True)
        else:
            subunits_gdf = unit_gdf.copy()
    elif adcode == "659000":  # 新疆生产建设兵团直辖城市组团
        unit_gdf = xj_prov[xj_prov['adcode'].astype(str).str.startswith("659")].copy()
        subunits_gdf = unit_gdf.copy()
    else:
        unit_gdf = xj_prov.copy()
        subunits_gdf = xj_prov.copy()
    return unit_gdf, subunits_gdf

def generate_unit_maps(adcode):
    cfg = XINJIANG_CONFIGS.get(str(adcode))
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
    
    # 对于兵团这种离散多边形，设置适度的全疆视野包络
    if adcode == "659000":
        db = xj_prov.total_bounds
        pad_m = 30000.0
    else:
        db = unit_gdf.total_bounds
        pad_m = cfg.get("pad_m", 15000.0)

    span_x = db[2] - db[0]
    span_y = db[3] - db[1]
    ax_xlim = (db[0] - pad_m, db[2] + pad_m)
    ax_ylim = (db[1] - pad_m, db[3] + pad_m)

    _ar = (ax_ylim[1] - ax_ylim[0]) / max(ax_xlim[1] - ax_xlim[0], 1e-9)
    _w = 9.6 / _ar if _ar >= 1 else 9.6
    _w = max(5.6, min(9.6, _w))
    _h = min(10.8, _w * _ar)
    FIGSIZE = (_w, max(5.2, _h))

    # 比例尺位置：右下角
    sb_x0 = ax_xlim[0] + (ax_xlim[1] - ax_xlim[0]) * 0.62
    sb_y0 = ax_ylim[0] + (ax_ylim[1] - ax_ylim[0]) * 0.055

    # 裁剪 DEM 栅格
    dx_pad, dy_pad = 15000.0, 15000.0
    x0, y0, x1, y1 = db[0] - dx_pad, db[1] - dy_pad, db[2] + dx_pad, db[3] + dy_pad
    c0 = max(0, int((x0 - dem_minx) / dem_res))
    c1 = min(dem_full.shape[1], int((x1 - dem_minx) / dem_res) + 1)
    r0 = max(0, int((dem_maxy - y1) / dem_res))
    r1 = min(dem_full.shape[0], int((dem_maxy - y0) / dem_res) + 1)

    # 若裁剪区域过大（如南疆/北疆），步进降采样防止内存过载
    sub_step = 2 if (c1 - c0) > 3000 or (r1 - r0) > 3000 else 1
    sub_dem = dem_full[r0:r1:sub_step, c0:c1:sub_step].copy()
    cur_res = dem_res * sub_step
    sub_minx = dem_minx + c0 * dem_res
    sub_maxy = dem_maxy - r0 * dem_res
    sub_extent = (sub_minx, sub_minx + sub_dem.shape[1] * cur_res,
                  sub_maxy - sub_dem.shape[0] * cur_res, sub_maxy)

    scale_mult = max(1.0, scale_km / 2.0)

    # =========================================================================
    # Map 1: 行政区划图 / 空间格局图
    # =========================================================================
    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    if adcode == "659000":
        # 兵团背景：全疆底图弱化
        xj_prov.plot(ax=ax, facecolor="#f4f6f7", edgecolor="#bdc3c7", lw=0.6, zorder=2)
        unit_gdf.plot(ax=ax, facecolor="#a9dfbf", edgecolor="#145a32", lw=1.5, zorder=4)
    else:
        subunits_gdf.plot(ax=ax, facecolor="#f8f9fa", edgecolor="#7f8c8d", lw=0.6, ls=":", zorder=3)
        unit_gdf.boundary.plot(ax=ax, edgecolor="#1a5276", lw=2.0, zorder=4)

    admin_covered = set()
    for p in cfg.get("places_admin", []):
        pname = p[0].split("(")[0].strip()
        for sfx in ["管委会", "市政府", "州政府", "行署", "城关", "县城"]:
            if pname.endswith(sfx):
                base = pname[:-len(sfx)].strip()
                if base:
                    admin_covered.add(base)
                    r = get_clean_root(base)
                    if r:
                        admin_covered.add(r)
        admin_covered.add(pname)
        admin_covered.add(get_clean_root(pname))

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

    # 区县/下属单元注记
    for _, row in subunits_gdf.iterrows():
        sname = row.get("name", "")
        if sname and sname not in admin_covered and len(sname) <= 8:
            clean_s = get_clean_root(sname)
            if clean_s not in admin_covered:
                c = row.geometry.representative_point()
                cx_p, cy_p = c.x, c.y
                if ax_xlim[0] <= cx_p <= ax_xlim[1] and ax_ylim[0] <= cy_p <= ax_ylim[1]:
                    ax.text(cx_p, cy_p, sname, fontsize=6.8, color="#2c3e50", fontweight="bold",
                            ha="center", va="center", zorder=10,
                            path_effects=[pe.withStroke(linewidth=1.8, foreground="#ffffff")])

    add_scalebar(ax, sb_x0, sb_y0, length_km=scale_km)
    add_compass(ax, 0.94, 0.91)

    leg_elements = [Patch(facecolor="none", edgecolor="#1a5276", linewidth=1.8,
                          label=f"{name}辖域范围")]
    leg = mapkit.stacked_legends(ax, [
        dict(handles=leg_elements + sym_type_h, title="符号含义",
             ncol=3, fontsize=7.0, title_fontsize=7.6),
        dict(handles=sym_idx_h, title="图上编号对照（编号标注于符号旁）",
             ncol=2, fontsize=7.0, title_fontsize=7.6),
    ], top=-0.010, gap=0.014)

    chart_title = "空间格局图" if adcode in ["652000", "653000", "659000"] else "行政区位图"
    ax.set_title(f"新疆维吾尔自治区{name}{chart_title}", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
    ax.text(0.5, 1.008, f"Administrative Location & Spatial Hierarchy of {en_name}", transform=ax.transAxes,
            ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
    mapkit.footer_below_legend(
        ax, leg, "数据源：自然资源部标准地图与 DataV 行政区划 · 制作：《中国地理知识手册》",
        fontsize=6.5)

    m1_path = os.path.join(OUT_DIR, f"fig{sec_id}-1_{name}{chart_title}.png")
    fig.savefig(m1_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Map 1 saved: {m1_path}")

    # =========================================================================
    # Map 2: 地形地貌图
    # =========================================================================
    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    hs = calc_hillshade(sub_dem, cur_res)
    e_min, e_max = cfg["elev_range"]
    colors = [
        (0.00, "#2980b9"),   # 负海拔/低谷湖泊
        (0.05, "#a9dfbf"),
        (0.20, "#f9e79f"),   # 盆地冲积暖黄
        (0.40, "#edbb99"),   # 丘陵中山棕褐
        (0.65, "#ba4a00"),   # 高中山深褐
        (0.85, "#78281f"),   # 极高山雪线
        (1.00, "#fdfefe")    # 极顶灰白
    ]
    cmap = LinearSegmentedColormap.from_list(f"{name}_elev", colors, N=256)
    norm = Normalize(vmin=e_min, vmax=e_max)

    valid = np.nan_to_num(sub_dem, nan=e_min)
    valid = np.clip(valid, norm.vmin, norm.vmax)
    rgb = cmap(norm(valid))[:, :, :3]
    rgb_shaded = rgb * (0.42 + 0.58 * hs[:, :, np.newaxis])

    im = ax.imshow(rgb_shaded, extent=sub_extent, origin="upper", zorder=3)
    if adcode != "659000":
        patch = get_mpl_clip_patch(u_geom)
        ax.add_patch(patch)
        im.set_clip_path(patch)

    unit_gdf.boundary.plot(ax=ax, color="#1a252f", lw=1.5, zorder=5)

    # 标注水体
    for wname, wlon, wlat, rot in cfg.get("water_labels", []):
        wx, wy = to_alb(wlon, wlat)
        if db[0] - 25000 <= wx <= db[2] + 25000 and db[1] - 25000 <= wy <= db[3] + 25000:
            ax.text(wx, wy, wname, fontsize=7.2, color="#1b4f72", style="italic", fontweight="bold",
                    ha="center", va="center", rotation=rot, zorder=12,
                    path_effects=[pe.withStroke(linewidth=1.8, foreground="#ffffff")])

    # 标注山峰高点与极值
    for pname, plon, plat, elev, ox, oy, side in cfg.get("peaks", []):
        px, py = to_alb(plon, plat)
        tx, ty = px + ox * scale_mult, py + oy * scale_mult
        ha = "left" if side == "left" else "right"
        marker_color = "#b03a2e" if elev > 1500 else "#27ae60"
        ax.plot(px, py, "^" if elev > 1500 else "v", color=marker_color, markersize=6.2, zorder=12)
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

    m2_title = "地形地貌与水系图" if adcode in ["652000", "653000"] else ("地形地貌与绿洲格局图" if adcode == "659000" else "地形地貌图")
    ax.set_title(f"新疆维吾尔自治区{name}{m2_title}", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
    ax.text(0.5, 1.008, f"Topography, Relief & Hydrological Network of {en_name}", transform=ax.transAxes,
            ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
    fig.text(0.5, 0.015, "数据源：AWS Terrain GLO-30 30m DEM · 投影：Albers 等积圆锥 · 制作：《中国地理知识手册》",
             ha="center", va="bottom", fontsize=6.5, color="#7f8c8d")

    m2_path = os.path.join(OUT_DIR, f"fig{sec_id}-2_{name}{m2_title}.png")
    fig.savefig(m2_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Map 2 saved: {m2_path}")

    # =========================================================================
    # Map 3: 道路交通图 / 综合交通网络图
    # =========================================================================
    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    if adcode == "659000":
        xj_prov.plot(ax=ax, facecolor="#fdfefe", edgecolor="#bdc3c7", lw=0.6, zorder=2)
        unit_gdf.plot(ax=ax, facecolor="#e8f8f5", edgecolor="#16a085", lw=1.2, zorder=3)
    else:
        unit_gdf.plot(ax=ax, facecolor="#fdfefe", edgecolor="#7f8c8d", lw=1.2, zorder=3)
        subunits_gdf.boundary.plot(ax=ax, color="#d5dbdb", lw=0.5, ls=":", zorder=3)

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

    leg_elements = [
        Line2D([0], [0], color="#c0392b", lw=2.2, label="高速铁路与客运大通道"),
        Line2D([0], [0], color="#2c3e50", lw=1.8, label="国家干线普铁与货运枢纽"),
        Line2D([0], [0], color="#e67e22", lw=1.8, label="国家高速公路与主干道")
    ]
    leg = mapkit.stacked_legends(ax, [
        dict(handles=leg_elements + sym_type_h, title="线型与符号含义",
             ncol=3, fontsize=6.8, title_fontsize=7.6),
        dict(handles=sym_idx_h, title="图上编号对照（编号标注于符号旁）",
             ncol=2, fontsize=6.8, title_fontsize=7.6),
    ], top=-0.010, gap=0.013)

    m3_title = "综合交通网络图" if adcode in ["652000", "653000"] else ("道路交通网络图" if adcode == "659000" else "道路交通图")
    ax.set_title(f"新疆维吾尔自治区{name}{m3_title}", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
    ax.text(0.5, 1.008, f"Transportation Network & Transit Corridors of {en_name}", transform=ax.transAxes,
            ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
    mapkit.footer_below_legend(
        ax, leg, "数据源：地方综合立体交通网规划与民航铁路枢纽导录 · 制作：《中国地理知识手册》",
        fontsize=6.5)

    m3_path = os.path.join(OUT_DIR, f"fig{sec_id}-3_{name}{m3_title}.png")
    fig.savefig(m3_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Map 3 saved: {m3_path}")

    # =========================================================================
    # Map 4: 特色专题图 / 重点优势产业分布图
    # =========================================================================
    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    if adcode == "659000":
        xj_prov.plot(ax=ax, facecolor="#fdfefe", edgecolor="#bdc3c7", lw=0.6, zorder=2)
        unit_gdf.plot(ax=ax, facecolor="#e8f8f5", edgecolor="#16a085", lw=1.2, zorder=3)
    else:
        unit_gdf.plot(ax=ax, facecolor="#fdfefe", edgecolor="#7f8c8d", lw=1.2, zorder=3)
        subunits_gdf.boundary.plot(ax=ax, color="#d5dbdb", lw=0.5, ls=":", zorder=3)

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    sl = mapkit.SymbolLabels(ax, fig)
    sl.reserve([(0.0, 0.0, 0.42, 0.32),      # 图例
                (0.50, 0.0, 1.0, 0.09),      # 比例尺
                (0.90, 0.84, 1.0, 1.0)])     # 指北针

    themes = cfg.get("theme_elements", [])
    theme_palette = [
    ("#c0392b", "o", "重大文保/历史古迹"),
    ("#1f618d", "s", "现代制造/重化新材"),
    ("#196f3d", "^", "生态保护/高山名胜"),
    ("#d35400", "D", "特色农业/林果节水"),
    ("#7d3c98", "p", "能源战略/绿色算力"),
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

    for idx, item in enumerate(themes):
        tname = item[0]
        tlon = item[1]
        tlat = item[2]
        tdesc = item[3] if len(item) > 3 else ""
        tx_t, ty_t = to_alb(tlon, tlat)
        color, marker, kind_label = theme_palette[idx % len(theme_palette)]
        nm, nt = mapkit.split_note(tname)
        note_str = tdesc if tdesc else nt
        sl.add(tx_t, ty_t, nm, f"thm_{idx}", note=note_str, priority=1,
               marker=marker, face=color, size=7.2,
               kind_label=kind_label)
    sym_type_h, sym_idx_h = sl.flush()

    add_scalebar(ax, sb_x0, sb_y0, length_km=scale_km)
    add_compass(ax, 0.955, 0.90)

    leg = mapkit.stacked_legends(ax, [
        dict(handles=sym_type_h, title="符号类型含义",
             ncol=3, fontsize=7.0, title_fontsize=7.6),
        dict(handles=sym_idx_h, title="图上特色要素编号对照（编号标注于符号旁）",
             ncol=1, fontsize=6.8, title_fontsize=7.6),
    ], top=-0.010, gap=0.014)

    m4_title = "重点优势产业分布图" if adcode in ["652000", "653000"] else ("特色优势产业分布图" if adcode == "659000" else "特色专题图")
    ax.set_title(f"新疆维吾尔自治区{name}{m4_title}",
                 fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
    ax.text(0.5, 1.008, f"Special Topics: Dominant Industries & Cultural Heritage of {en_name}", transform=ax.transAxes,
            ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
    mapkit.footer_below_legend(
        ax, leg, "数据源：地方发展规划与重点特色产业导录 · 制作：《中国地理知识手册》",
        fontsize=6.5)

    m4_path = os.path.join(OUT_DIR, f"fig{sec_id}-4_{name}{m4_title}.png")
    fig.savefig(m4_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Map 4 saved: {m4_path}")

    # =========================================================================
    # Map 5: 夜间灯光与经济发展演进图
    # =========================================================================
    fig, (ax_nl, ax_gdp) = plt.subplots(2, 1, figsize=(9.5, 8.5), dpi=DPI)
    fig.patch.set_facecolor("white")

    # 提取夜光数据
    if adcode in ["650100", "650200", "650400", "650500"]:
        short_code = str(adcode)[:4]
        nl_sub = nl_clean_df[nl_clean_df["city_code"].astype(str).str.startswith(short_code)].groupby("year")["sum"].sum().reset_index()
    elif adcode == "652000":
        nl_sub = nl_clean_df[nl_clean_df["city_code"].astype(str).str[:4].isin(["6523", "6527", "6540", "6542", "6543"])].groupby("year")["sum"].sum().reset_index()
    elif adcode == "653000":
        nl_sub = nl_clean_df[nl_clean_df["city_code"].astype(str).str[:4].isin(["6528", "6529", "6530", "6531", "6532"])].groupby("year")["sum"].sum().reset_index()
    elif adcode == "659000":
        nl_sub = nl_clean_df[nl_clean_df["city_code"].astype(str).str.startswith("659")].groupby("year")["sum"].sum().reset_index()
        # 若兵团数据较少，加上若干典型垦区
        if len(nl_sub) == 0:
            nl_sub = nl_clean_df[nl_clean_df["district_name"].astype(str).str.contains("团|师|石河子|阿拉尔|图木舒克|五家渠")].groupby("year")["sum"].sum().reset_index()
    else:
        nl_sub = pd.DataFrame()

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

    # 历年 GDP 柱状图
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
    fig.text(0.5, 0.01, "数据来源：夜间灯光数据集 (1986-2024) · 新疆统计年鉴与历年国民经济和社会发展统计公报 · 制作：《中国地理知识手册》",
             ha="center", va="bottom", fontsize=6.5, color="#7f8c8d")

    m5_path = os.path.join(OUT_DIR, f"fig{sec_id}-5_{name}夜间灯光与经济发展演进图.png")
    fig.savefig(m5_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Map 5 saved: {m5_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Xinjiang unit maps")
    parser.add_argument("--adcode", type=str, default=None, help="Target ADCODE (e.g. 650100)")
    args = parser.parse_args()

    if args.adcode:
        generate_unit_maps(args.adcode)
    else:
        adcodes = sorted(list(XINJIANG_CONFIGS.keys()))
        for adc in adcodes:
            generate_unit_maps(adc)
    print("\nAll requested Xinjiang unit maps generated successfully!")
