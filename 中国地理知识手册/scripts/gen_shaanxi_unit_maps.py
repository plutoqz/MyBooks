# -*- coding: utf-8 -*-
"""陕西省各分析单元地图自动化生成引擎
覆盖 10 个分析单元（25-01 至 25-10，覆盖全省 10 个地级市）：
1. fig{sec_id}-1_{name}行政区位图.png
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
from shapely.geometry import Polygon as ShpPolygon
from matplotlib.path import Path
from matplotlib.lines import Line2D
from matplotlib.colors import LinearSegmentedColormap, Normalize
from pyproj import Transformer
from shapely.validation import make_valid

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册"
sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))
from style import ALBERS, C_TEXT, DATA, DPI, FIGURES, setup
from shaanxi_city_configs import SHAANXI_CITY_CONFIGS
import mapkit

setup()
OUT_DIR = os.path.join(BASE_DIR, "figures")
os.makedirs(OUT_DIR, exist_ok=True)
_T = Transformer.from_crs("EPSG:4326", ALBERS, always_xy=True)

def to_alb(lon, lat):
    return _T.transform(lon, lat)

PLACE_KIND_LABEL = {
    "gov": "市委市政府驻地 · 行政极核",
    "subdistrict": "核心城区 / 区县中心",
    "town": "重点县市 / 产业支点",
    "tech": "先进制造业基地 / 战略产业集群",
    "station": "综合交通枢纽 / 高铁机场港口",
    "scenic": "名胜名产 / 世界遗产与文化胜迹",
    "_default": "其他重点地理要素",
}

PLACE_STYLE = {
    "gov":        dict(color="#78281f", mcolor="#c0392b", marker="*", fs=8.0, ms=9.5, pri=0, z=16, weight="bold"),
    "subdistrict":dict(color="#935116", mcolor="#d35400", marker="s", fs=7.0, ms=5.0, pri=1, z=15, weight="bold"),
    "town":       dict(color="#935116", mcolor="#d35400", marker="s", fs=7.0, ms=5.0, pri=1, z=15, weight="bold"),
    "tech":       dict(color="#6c3483", mcolor="#8e44ad", marker="D", fs=7.0, ms=5.2, pri=2, z=14, weight="bold"),
    "station":    dict(color="#154360", mcolor="#1f618d", marker="s", fs=7.0, ms=5.5, pri=1, z=15, weight="bold"),
    "scenic":     dict(color="#196f3d", mcolor="#27ae60", marker="o", fs=6.8, ms=4.8, pri=3, z=13, weight="normal"),
    "_default":   dict(color="#2c3e50", mcolor="#566573", marker="o", fs=6.5, ms=4.0, pri=4, z=12, weight="normal"),
}

_KIND_ALIAS = {
    "district": "subdistrict",
    "county": "town",
    "airport": "station",
    "rail": "station",
    "rail_hub": "station",
    "port": "station",
    "bridge": "station",
    "cableway": "station",
    "logistics": "station",
    "heritage": "scenic",
    "nature": "scenic",
    "mountain": "scenic",
    "lake": "scenic",
    "industry": "tech",
    "auto_tech": "tech",
    "battery": "tech",
    "material": "tech",
    "energy": "tech",
    "pharma": "tech",
    "science": "tech",
    "agri": "tech",
}

def classify_special_kind(name, note=""):
    s = str(name) + " " + str(note)
    if any(k in s for k in ['园区', '科技', '制造', '工程', '产业', '基地', '航空', '科学', '集聚', '示范', '研发', '材料', '工业', '智谷', '港', '电力', '算力', '数据', '半导体', '芯片', '重卡', '钛', '煤化', '煤田', '油田']):
        return 'tech'
    elif any(k in s for k in ['遗产', '保护', '名胜', '古', '文', '寺', '馆', '墓', '峡', '山', '湖', '水利', '国家公园', '景区', '生态', '湿地', '故里', '遗址', '洞', '瀑布', '兵马俑', '陵', '5A', '4A', '苹果', '茶', '酒', '猕猴桃']):
        return 'scenic'
    return 'tech'

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
    d = np.nan_to_num(dem, nan=0.0)
    gy, gx = np.gradient(d, res)
    slope = np.arctan(np.sqrt(gx * gx + gy * gy))
    aspect = np.arctan2(-gx, gy)
    shaded = np.sin(alt_rad) * np.cos(slope) + np.cos(alt_rad) * np.sin(slope) * np.cos(az_rad - aspect)
    return np.clip(shaded, 0.0, 1.0)

def add_scalebar(ax, x0, y0, length_km=30):
    mapkit.add_scalebar(ax, x0, y0, length_km=length_km)

def add_compass(ax, x=0.94, y=0.91):
    ax.annotate("N", xy=(x, y), xytext=(x, y - 0.055), transform=ax.transAxes,
                arrowprops=dict(facecolor="#2c3e50", edgecolor="#2c3e50", width=1.8, headwidth=5.5, headlength=6.5),
                ha="center", va="center", fontsize=8.8, fontweight="bold", color="#2c3e50", zorder=30)

print("Initializing base spatial environments for Shaanxi...")
DATA_DIR = os.path.join(BASE_DIR, "data")
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")
sn_prov = gpd.read_file(os.path.join(DATAV_DIR, "610000_full.json")).to_crs(ALBERS)
sn_prov["geometry"] = sn_prov.geometry.buffer(0)

dem_data = np.load(os.path.join(DATA_DIR, "dem", "province", "610000_z9.npz"))
dem_full = dem_data['dem']
dem_res = float(dem_data['res'])
dem_minx = float(dem_data['minx'])
dem_maxy = float(dem_data['maxy'])

nl_clean_df = pd.read_csv(os.path.join(DATA_DIR, "shaanxi_nightlight_clean.csv"))
print("Base spatial environments ready.")

def get_unit_geometry_and_subunits(adcode, cfg):
    c_str = str(adcode)
    unit_gdf = sn_prov[sn_prov['adcode'].astype(str) == c_str].copy()
    unit_gdf["geometry"] = unit_gdf.geometry.buffer(0)

    sub_file = os.path.join(DATAV_DIR, f"{c_str}_full.json")
    if not os.path.exists(sub_file):
        sub_file = os.path.join(DATAV_DIR, f"{c_str}.json")
    if os.path.exists(sub_file):
        try:
            subunits_gdf = gpd.read_file(sub_file).to_crs(ALBERS)
            subunits_gdf["geometry"] = subunits_gdf.geometry.buffer(0)
        except Exception:
            subunits_gdf = unit_gdf.copy()
    else:
        subunits_gdf = unit_gdf.copy()
    return unit_gdf, subunits_gdf

def generate_unit_maps(adcode):
    cfg = SHAANXI_CITY_CONFIGS.get(str(adcode))
    if not cfg:
        print(f"Config for {adcode} not found, skipping...")
        return

    sec_id = cfg["sec_id"]
    name = cfg["name"]
    en_name = cfg.get("en_name", f"{name}")
    scale_km = cfg.get("scale_km", 25)
    print(f"\n=======================================================")
    print(f"Generating 5 publication maps for {sec_id} {name} ({adcode})...")
    print(f"=======================================================")

    unit_gdf, subunits_gdf = get_unit_geometry_and_subunits(adcode, cfg)
    if unit_gdf.empty:
        print(f"Error: unit_gdf for {adcode} is empty!")
        return

    unit_union = make_valid(unit_gdf.union_all())
    db = unit_gdf.total_bounds
    pad_m = cfg.get("pad_m", 15000.0)

    ax_xlim = (db[0] - pad_m, db[2] + pad_m)
    ax_ylim = (db[1] - pad_m, db[3] + pad_m)

    _span_x = ax_xlim[1] - ax_xlim[0]
    _span_y = ax_ylim[1] - ax_ylim[0]
    _ar = max(0.55, min(1.85, _span_y / max(1.0, _span_x)))
    _w = 9.6 / _ar if _ar >= 1 else 9.6
    _w = max(5.6, min(9.6, _w))
    _h = min(10.8, _w * _ar)
    FIGSIZE = (_w, max(5.2, _h))

    sb_x0 = ax_xlim[0] + (ax_xlim[1] - ax_xlim[0]) * 0.58
    sb_y0 = ax_ylim[0] + (ax_ylim[1] - ax_ylim[0]) * 0.055

    # 裁剪局部 DEM
    dx_pad = max(pad_m * 1.5, 20000.0)
    dy_pad = max(pad_m * 1.5, 20000.0)
    x0, y0, x1, y1 = db[0] - dx_pad, db[1] - dy_pad, db[2] + dx_pad, db[3] + dy_pad
    c0 = max(0, int((x0 - dem_minx) / dem_res))
    c1 = min(dem_full.shape[1], int((x1 - dem_minx) / dem_res) + 1)
    r0 = max(0, int((dem_maxy - y1) / dem_res))
    r1 = min(dem_full.shape[0], int((dem_maxy - y0) / dem_res) + 1)

    sub_step = 2 if (c1 - c0) > 1000 or (r1 - r0) > 1000 else 1
    sub_dem = dem_full[r0:r1:sub_step, c0:c1:sub_step].copy()
    cur_res = dem_res * sub_step
    sub_minx = dem_minx + c0 * dem_res
    sub_maxy = dem_maxy - r0 * dem_res
    sub_extent = (sub_minx, sub_minx + sub_dem.shape[1] * cur_res, sub_maxy - sub_dem.shape[0] * cur_res, sub_maxy)

    # -------------------------------------------------------------
    # Map 1: 行政区位图
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    fig.subplots_adjust(left=0.015, right=0.985, top=0.950, bottom=0.015)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    sn_prov.plot(ax=ax, facecolor="#f2f3f4", edgecolor="#bdc3c7", lw=0.6, zorder=1)

    sub_colors = ["#d4e6f1", "#d5f5e3", "#fcf3cf", "#ebdef0", "#fadbd8", "#e8f8f5", "#fdebd0", "#eaeded", "#d6eaf8", "#edbb99",
                  "#d1f2eb", "#fef9e7", "#e8daef", "#d0ece7", "#f5cba7", "#aed6f1", "#a9dfbf"]
    for i, (_, srow) in enumerate(subunits_gdf.iterrows()):
        c = sub_colors[i % len(sub_colors)]
        gpd.GeoSeries([srow.geometry]).plot(ax=ax, facecolor=c, edgecolor="#7f8c8d", lw=0.7, zorder=2)
        sname = srow.get("name", "")
        if sname and len(subunits_gdf) > 1:
            pt = srow.geometry.representative_point()
            ax.text(pt.x, pt.y, sname, fontsize=6.8, color="#2c3e50", ha="center", va="center",
                    path_effects=[pe.withStroke(linewidth=1.8, foreground="#ffffff")], zorder=5)

    gpd.GeoSeries([unit_union]).boundary.plot(ax=ax, color="#1b4f72", lw=1.8, zorder=4)

    sl1 = mapkit.SymbolLabels(ax, fig)
    sl1.reserve([(0.0, 0.0, 0.35, 0.22), (0.55, 0.0, 1.0, 0.08), (0.85, 0.85, 1.0, 1.0)])

    for item in cfg.get("places_admin", []):
        pname, plon, plat = item[0], item[1], item[2]
        px, py = to_alb(plon, plat)
        nm, nt = mapkit.split_note(pname)
        pk = item[5] if len(item) > 5 else "subdistrict"
        pk_norm = _KIND_ALIAS.get(pk, pk)
        st = PLACE_STYLE.get(pk_norm, PLACE_STYLE["_default"])
        kl = PLACE_KIND_LABEL.get(pk_norm, "其他地物要素")
        sl1.add(px, py, nm, pk_norm, note=nt, priority=st["pri"],
                marker=st["marker"], face=st["mcolor"], size=st["ms"], kind_label=kl)

    sym_type_h, sym_idx_h = sl1.flush()
    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    add_scalebar(ax, sb_x0, sb_y0, length_km=scale_km)
    add_compass(ax, 0.94, 0.91)

    leg = mapkit.stacked_legends(ax, [
        dict(handles=sym_type_h, title="行政要素分类", ncol=2, fontsize=6.8, title_fontsize=7.6),
        dict(handles=sym_idx_h, title="图上要素编号对照", ncol=2, fontsize=6.8, title_fontsize=7.6),
    ], top=-0.010, gap=0.014)

    ax.set_title(f"{name}行政区位与辖区空间分布图", fontsize=11.5, fontweight="bold", pad=20, color=C_TEXT)
    ax.text(0.5, 1.008, f"Administrative Location & Subdivisions of {en_name}",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=7.2, color="#7f8c8d")
    mapkit.footer_below_legend(ax, leg, "数据源：自然资源部标准地图服务 · 制作：《中国地理知识手册》", fontsize=6.5)

    m1_path = os.path.join(OUT_DIR, f"fig{sec_id}-1_{name}行政区位图.png")
    fig.savefig(m1_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Map 1 saved: {m1_path}")

    # -------------------------------------------------------------
    # Map 2: 地形地貌图
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    fig.subplots_adjust(left=0.015, right=0.985, top=0.950, bottom=0.015)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    cdict = {
        'red':   [(0.0, 0.18, 0.18), (0.2, 0.40, 0.40), (0.5, 0.85, 0.85), (0.8, 0.80, 0.80), (1.0, 0.45, 0.45)],
        'green': [(0.0, 0.55, 0.55), (0.2, 0.75, 0.75), (0.5, 0.82, 0.82), (0.8, 0.55, 0.55), (1.0, 0.25, 0.25)],
        'blue':  [(0.0, 0.34, 0.34), (0.2, 0.35, 0.35), (0.5, 0.40, 0.40), (0.8, 0.30, 0.30), (1.0, 0.18, 0.18)]
    }
    cmap = LinearSegmentedColormap('sn_hypso', cdict, N=256)

    e_min, e_max = cfg.get("elev_range", (300.0, 2500.0))
    norm = Normalize(vmin=e_min, vmax=e_max)

    if sub_dem is not None:
        sub_dem_clean = np.where(sub_dem < 0, np.nan, sub_dem)
        hs = calc_hillshade(sub_dem_clean, cur_res, az=315, alt=45)
        rgb_c = cmap(norm(sub_dem_clean))[:, :, :3]
        rgb_s = np.clip(rgb_c * (hs[:, :, np.newaxis] * 0.7 + 0.3), 0.0, 1.0)

        im = ax.imshow(rgb_s, extent=sub_extent, origin="upper", zorder=1)
        patch = get_mpl_clip_patch(unit_union)
        ax.add_patch(patch)
        im.set_clip_path(patch)
    else:
        sn_prov.plot(ax=ax, facecolor="#ccebc5", edgecolor="#7bccc4", lw=0.8, zorder=2)

    gpd.GeoSeries([unit_union]).boundary.plot(ax=ax, color="#1b4f72", lw=1.8, zorder=4)

    sl2 = mapkit.SymbolLabels(ax, fig)
    sl2.reserve([(0.0, 0.0, 0.35, 0.22), (0.55, 0.0, 1.0, 0.08), (0.85, 0.85, 1.0, 1.0)])

    for p in cfg.get("peaks", []):
        pname, plon, plat, pelev = p[0], p[1], p[2], p[3]
        px, py = to_alb(plon, plat)
        nm, nt = mapkit.split_note(pname)
        sl2.add(px, py, nm, "peak", note=nt, priority=0,
                marker="^", face="#78281f", size=7.8, kind_label="主要山峰 / 高程控制点")

    for w in cfg.get("water_labels", []):
        wname, wlon, wlat = w[0], w[1], w[2]
        wx, wy = to_alb(wlon, wlat)
        nm, nt = mapkit.split_note(wname)
        sl2.add(wx, wy, nm, "water", note=nt, priority=1,
                marker="o", face="#1b4f72", size=6.0, kind_label="骨干水系 / 水库湖泊渠道")

    sym_type_h, sym_idx_h = sl2.flush()
    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    add_scalebar(ax, sb_x0, sb_y0, length_km=scale_km)
    add_compass(ax, 0.94, 0.91)

    cax = ax.inset_axes([0.04, 0.06, 0.025, 0.25])
    cb = plt.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cax, orientation="vertical")
    cb.set_label("高程 Elevation (m)", fontsize=6.8, color="#2c3e50")
    cb.ax.tick_params(labelsize=6.0, length=2.0)

    leg = mapkit.stacked_legends(ax, [
        dict(handles=sym_type_h, title="自然地理地貌要素", ncol=2, fontsize=6.8, title_fontsize=7.6),
        dict(handles=sym_idx_h, title="山川水系编号对照", ncol=2, fontsize=6.8, title_fontsize=7.6),
    ], top=-0.010, gap=0.014)

    ax.set_title(f"{name}地形地貌与水系空间格局图", fontsize=11.5, fontweight="bold", pad=20, color=C_TEXT)
    ax.text(0.5, 1.008, f"Topography, Landforms & Drainage System of {en_name}",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=7.2, color="#7f8c8d")
    mapkit.footer_below_legend(ax, leg, "数据源：AWS Terrain GLO-30 DEM · 制作：《中国地理知识手册》", fontsize=6.5)

    m2_path = os.path.join(OUT_DIR, f"fig{sec_id}-2_{name}地形地貌图.png")
    fig.savefig(m2_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Map 2 saved: {m2_path}")

    # -------------------------------------------------------------
    # Map 3: 道路交通图
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    fig.subplots_adjust(left=0.015, right=0.985, top=0.950, bottom=0.015)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#f8f9f9")

    sn_prov.plot(ax=ax, facecolor="#f8f9f9", edgecolor="#d5d8dc", lw=0.5, zorder=1)
    gpd.GeoSeries([unit_union]).plot(ax=ax, facecolor="#ebedef", edgecolor="#7f8c8d", lw=1.2, zorder=2)

    sl3 = mapkit.SymbolLabels(ax, fig)
    sl3.reserve([(0.0, 0.0, 0.35, 0.22), (0.55, 0.0, 1.0, 0.08), (0.85, 0.85, 1.0, 1.0)])

    trans_list = cfg.get("transport_labels") or cfg.get("stations", [])
    for s in trans_list:
        sname, slon, slat = s[0], s[1], s[2]
        sx, sy = to_alb(slon, slat)
        nm, nt = mapkit.split_note(sname)
        sk = s[3] if len(s) > 3 else "station"
        sk_norm = _KIND_ALIAS.get(sk, "station")
        st = PLACE_STYLE.get(sk_norm, PLACE_STYLE["station"])
        sl3.add(sx, sy, nm, sk_norm, note=nt, priority=0,
                marker=st["marker"], face=st["mcolor"], size=st["ms"], kind_label="交通枢纽 / 站场港口机场")

    sym_type_h, sym_idx_h = sl3.flush()
    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    add_scalebar(ax, sb_x0, sb_y0, length_km=scale_km)
    add_compass(ax, 0.94, 0.91)

    leg = mapkit.stacked_legends(ax, [
        dict(handles=sym_type_h, title="综合交通设施分类", ncol=2, fontsize=6.8, title_fontsize=7.6),
        dict(handles=sym_idx_h, title="枢纽通道编号对照", ncol=2, fontsize=6.8, title_fontsize=7.6),
    ], top=-0.010, gap=0.014)

    ax.set_title(f"{name}综合交通网络与现代物流走廊图", fontsize=11.5, fontweight="bold", pad=20, color=C_TEXT)
    ax.text(0.5, 1.008, f"Comprehensive Transportation & Logistics of {en_name}",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=7.2, color="#7f8c8d")
    mapkit.footer_below_legend(ax, leg, "数据源：中国国家铁路集团 · 交通运输部 · 制作：《中国地理知识手册》", fontsize=6.5)

    m3_path = os.path.join(OUT_DIR, f"fig{sec_id}-3_{name}道路交通图.png")
    fig.savefig(m3_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Map 3 saved: {m3_path}")

    # -------------------------------------------------------------
    # Map 4: 特色专题图
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    fig.subplots_adjust(left=0.015, right=0.985, top=0.950, bottom=0.015)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    sn_prov.plot(ax=ax, facecolor="#fdfefe", edgecolor="#d5d8dc", lw=0.5, zorder=1)
    gpd.GeoSeries([unit_union]).plot(ax=ax, facecolor="#fef9e7", edgecolor="#b7950b", lw=1.2, zorder=2)

    sl4 = mapkit.SymbolLabels(ax, fig)
    sl4.reserve([(0.0, 0.0, 0.35, 0.22), (0.55, 0.0, 1.0, 0.08), (0.85, 0.85, 1.0, 1.0)])

    themes = cfg.get("special_labels") or cfg.get("theme_elements", [])
    for th in themes:
        tname, tlon, tlat = th[0], th[1], th[2]
        tx, ty = to_alb(tlon, tlat)
        nm, nt = mapkit.split_note(tname)
        desc = th[3] if len(th) > 3 and isinstance(th[3], str) else ""
        if not nt and desc:
            nt = desc
        tk = classify_special_kind(tname, desc)
        st = PLACE_STYLE.get(tk, PLACE_STYLE["tech"])
        kl = "重点先进制造与现代能化" if tk == "tech" else "重大文化名胜与自然遗产"
        sl4.add(tx, ty, nm, tk, note=nt, priority=st["pri"],
                marker=st["marker"], face=st["mcolor"], size=st["ms"], kind_label=kl)

    sym_type_h, sym_idx_h = sl4.flush()
    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    add_scalebar(ax, sb_x0, sb_y0, length_km=scale_km)
    add_compass(ax, 0.94, 0.91)

    leg = mapkit.stacked_legends(ax, [
        dict(handles=sym_type_h, title="特色产业与重点园区分类", ncol=2, fontsize=6.8, title_fontsize=7.6),
        dict(handles=sym_idx_h, title="现代产业与名胜编号对照", ncol=2, fontsize=6.8, title_fontsize=7.6),
    ], top=-0.010, gap=0.014)

    ax.set_title(f"{name}特色优势产业与文旅地理空间布局图", fontsize=11.5, fontweight="bold", pad=20, color=C_TEXT)
    ax.text(0.5, 1.008, f"Specialized Industries & Cultural Tourism Distribution of {en_name}",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=7.2, color="#7f8c8d")
    mapkit.footer_below_legend(ax, leg, "数据源：地方统计年鉴 · 国家级产业开发区名录 · 制作：《中国地理知识手册》", fontsize=6.5)

    m4_path = os.path.join(OUT_DIR, f"fig{sec_id}-4_{name}特色专题图.png")
    fig.savefig(m4_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Map 4 saved: {m4_path}")

    # -------------------------------------------------------------
    # Map 5: 夜间灯光与经济发展演进图
    # -------------------------------------------------------------
    fig, (ax_nl, ax_gdp) = plt.subplots(1, 2, figsize=(11.0, 5.2), dpi=DPI)
    fig.subplots_adjust(left=0.07, right=0.96, top=0.88, bottom=0.14, wspace=0.22)
    fig.patch.set_facecolor("white")

    # 夜光时序曲线
    c_int = int(adcode)
    nl_sub = nl_clean_df[nl_clean_df["city_code"] == c_int]

    if not nl_sub.empty:
        nl_agg = nl_sub.groupby("year")["sum"].sum().reset_index().sort_values("year")
        years = nl_agg["year"].values
        sums = nl_agg["sum"].values
        ax_nl.plot(years, sums, color="#d35400", lw=2.0, marker="o", ms=3.8, label="夜光总辐射 (DN)")
        ax_nl.fill_between(years, sums, color="#fdebd0", alpha=0.5)

        max_sum = max(sums) if len(sums) > 0 and max(sums) > 0 else 1.0
        for item in cfg.get("nl_annotations", []):
            y_pt = item[0]
            note = item[4] if len(item) > 4 else item[-1]
            sub_pt = nl_agg[nl_agg["year"] == y_pt]
            if not sub_pt.empty:
                real_val = float(sub_pt["sum"].values[0])
                ty = real_val + max_sum * 0.18
                if ty > max_sum * 1.12:
                    ty = real_val - max_sum * 0.16
                ax_nl.annotate(note, xy=(y_pt, real_val), xytext=(y_pt - 4.5, ty),
                               arrowprops=dict(arrowstyle="->", color="#c0392b", lw=0.8),
                               fontsize=6.8, fontweight="bold", color="#78281f",
                               bbox=dict(boxstyle="round,pad=0.2", facecolor="#ffffff", edgecolor="#e74c3c", alpha=0.9))

    ax_nl.set_title(f"{name} 1986—2024 年夜间灯光辐射时序跃迁演进", fontsize=10.5, fontweight="bold", color=C_TEXT)
    ax_nl.set_ylabel("夜光总量辐射积分 (DN)", fontsize=7.5, color="#2c3e50")
    ax_nl.grid(True, linestyle="--", alpha=0.4)
    ax_nl.tick_params(labelsize=7.0)

    # 历年 GDP 柱状图
    gdp_series = cfg.get("gdp_series", {})
    if gdp_series:
        gyears = list(gdp_series.keys())
        gvals = list(gdp_series.values())
        bars = ax_gdp.bar(gyears, gvals, width=1.5, color="#1b4f72", edgecolor="#0b2545", alpha=0.85, label="地区生产总值 (GDP, 亿元)")
        for bar in bars:
            h = bar.get_height()
            ax_gdp.text(bar.get_x() + bar.get_width() / 2.0, h + max(gvals) * 0.015, f"{h:g}",
                        ha="center", va="bottom", fontsize=6.5, fontweight="bold", color="#0b2545")

    ax_gdp.set_title(f"{name} 2000—2024 年经济总量 (GDP) 跨越式跃升", fontsize=10.5, fontweight="bold", color=C_TEXT)
    ax_gdp.set_ylabel("GDP (亿元)", fontsize=7.5, color="#2c3e50")
    ax_gdp.set_xlabel("年份 Year", fontsize=7.5, color="#2c3e50")
    ax_gdp.grid(True, linestyle="--", alpha=0.4)
    ax_gdp.tick_params(labelsize=7.0)

    fig.tight_layout(pad=2.5)
    fig.text(0.5, 0.01, "数据来源：夜间灯光遥感时序数据集 (1986-2024) · 陕西省统计年鉴与历年国民经济和社会发展统计公报 · 制作：《中国地理知识手册》",
             ha="center", va="bottom", fontsize=6.5, color="#7f8c8d")

    m5_path = os.path.join(OUT_DIR, f"fig{sec_id}-5_{name}夜间灯光与经济发展演进图.png")
    fig.savefig(m5_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Map 5 saved: {m5_path}")

def main():
    parser = argparse.ArgumentParser(description="Generate unit maps for Shaanxi province.")
    parser.add_argument("--code", type=str, default="all", help="Adcode of unit or 'all'")
    parser.add_argument("--workers", type=int, default=4, help="Number of parallel workers")
    args = parser.parse_args()

    if args.code == "all":
        codes = list(SHAANXI_CITY_CONFIGS.keys())
        if args.workers > 1:
            from concurrent.futures import ProcessPoolExecutor
            with ProcessPoolExecutor(max_workers=args.workers) as executor:
                list(executor.map(generate_unit_maps, codes))
        else:
            for adcode in codes:
                generate_unit_maps(adcode)
    else:
        generate_unit_maps(args.code)

if __name__ == "__main__":
    main()
