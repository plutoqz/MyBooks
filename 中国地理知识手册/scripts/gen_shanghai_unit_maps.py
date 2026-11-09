# -*- coding: utf-8 -*-
"""上海市各市辖区分单元地图自动化生成引擎
支持 16 个分析单元（09-01 至 09-16）：
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

sys.path.insert(0, r"D:\code\Ideas\MyBooks\中国地理知识手册\scripts")
from style import ALBERS, C_TEXT, DATA, DPI, FIGURES, setup
from shanghai_configs import SHANGHAI_CONFIGS
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
    "district": "subdistrict",
    "county": "town",
    "airport": "station",
    "rail": "station",
    "port": "station",
    "heritage": "scenic",
    "nature": "scenic",
    "mountain": "scenic",
    "lake": "scenic",
    "industry": "tech",
    "mining": "tech",
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
    d = np.nan_to_num(dem, nan=0.0)
    gy, gx = np.gradient(d, res)
    slope = np.arctan(np.sqrt(gx * gx + gy * gy))
    aspect = np.arctan2(-gx, gy)
    shaded = np.sin(alt_rad) * np.cos(slope) + np.cos(alt_rad) * np.sin(slope) * np.cos(az_rad - aspect)
    return np.clip(shaded, 0.0, 1.0)

def add_scalebar(ax, x0, y0, length_km=3):
    mapkit.add_scalebar(ax, x0, y0, length_km=length_km)

def add_compass(ax, x=0.94, y=0.91):
    ax.annotate("N", xy=(x, y), xytext=(x, y - 0.055), transform=ax.transAxes,
                arrowprops=dict(facecolor="#2c3e50", edgecolor="#2c3e50", width=1.8, headwidth=5.5, headlength=6.5),
                ha="center", va="center", fontsize=8.8, fontweight="bold", color="#2c3e50", zorder=30)

print("Initializing base spatial environments for Shanghai...")
DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")
sh_prov = gpd.read_file(os.path.join(DATAV_DIR, "310000_full.json")).to_crs(ALBERS)
sh_prov["geometry"] = sh_prov.geometry.buffer(0)

dem_data = np.load(os.path.join(DATA_DIR, "dem", "province", "310000_z9.npz"))
dem_full = np.nan_to_num(dem_data['dem'], nan=0.0)
dem_res = float(dem_data['res'])
dem_minx = float(dem_data['minx'])
dem_maxy = float(dem_data['maxy'])

nl_clean_df = pd.read_csv(os.path.join(DATA_DIR, "shanghai_nightlight_clean.csv"))
print("Base spatial environments ready.")

def get_unit_geometry_and_subunits(adcode, cfg):
    unit_gdf = sh_prov[sh_prov['adcode'].astype(str) == str(adcode)].copy()
    unit_gdf["geometry"] = unit_gdf.geometry.buffer(0)
    sub_file = os.path.join(DATAV_DIR, f"{adcode}_full.json")
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
    cfg = SHANGHAI_CONFIGS.get(adcode)
    if not cfg:
        print(f"Config for {adcode} not found, skipping...")
        return

    sec_id = cfg["sec_id"]
    name = cfg["name"]
    en_name = cfg["en_name"]
    scale_km = cfg.get("scale_km", 5)
    print(f"\n=======================================================")
    print(f"Generating 5 publication maps for {sec_id} {name} ({adcode})...")
    print(f"=======================================================")

    unit_gdf, subunits_gdf = get_unit_geometry_and_subunits(adcode, cfg)
    if unit_gdf.empty:
        print(f"Error: unit_gdf for {adcode} is empty!")
        return

    unit_union = make_valid(unit_gdf.union_all())
    db = unit_gdf.total_bounds
    pad_m = cfg.get("pad_m", 3000.0)
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

    # 裁剪 DEM 栅格
    dx_pad = max(pad_m * 1.5, 6000.0)
    dy_pad = max(pad_m * 1.5, 6000.0)
    x0, y0, x1, y1 = db[0] - dx_pad, db[1] - dy_pad, db[2] + dx_pad, db[3] + dy_pad
    c0 = max(0, int((x0 - dem_minx) / dem_res))
    c1 = min(dem_full.shape[1], int((x1 - dem_minx) / dem_res) + 1)
    r0 = max(0, int((dem_maxy - y1) / dem_res))
    r1 = min(dem_full.shape[0], int((dem_maxy - y0) / dem_res) + 1)

    sub_step = 2 if (c1 - c0) > 2000 or (r1 - r0) > 2000 else 1
    sub_dem = dem_full[r0:r1:sub_step, c0:c1:sub_step].copy()
    cur_res = dem_res * sub_step
    sub_minx = dem_minx + c0 * dem_res
    sub_maxy = dem_maxy - r0 * dem_res
    sub_extent = (sub_minx, sub_minx + sub_dem.shape[1] * cur_res,
                  sub_maxy - sub_dem.shape[0] * cur_res, sub_maxy)

    # =========================================================================
    # Map 1: 行政区位图
    # =========================================================================
    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    # 绘制全市背景作为邻近参照
    sh_prov.plot(ax=ax, facecolor="#f8f9fa", edgecolor="#bdc3c7", lw=0.6, ls=":", zorder=2)
    # 高亮本区
    unit_gdf.plot(ax=ax, facecolor="#eaf2f8", edgecolor="#1a5276", lw=2.0, zorder=4)

    # 绘制邻近区名称注记
    for _, row in sh_prov.iterrows():
        other_code = str(row.get("adcode", ""))
        other_name = str(row.get("name", ""))
        if other_code != str(adcode):
            pt = row.geometry.representative_point()
            if ax_xlim[0] <= pt.x <= ax_xlim[1] and ax_ylim[0] <= pt.y <= ax_ylim[1]:
                ax.text(pt.x, pt.y, other_name, fontsize=7.2, color="#7f8c8d", weight="bold",
                        ha="center", va="center", zorder=5,
                        path_effects=[pe.withStroke(linewidth=1.8, foreground="#ffffff")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    sl = mapkit.SymbolLabels(ax, fig)
    sl.reserve([(0.50, 0.0, 1.0, 0.09),
                (0.88, 0.86, 1.0, 1.0)])
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

    add_scalebar(ax, sb_x0, sb_y0, length_km=scale_km)
    add_compass(ax, 0.94, 0.91)

    leg_elements = [Patch(facecolor="#eaf2f8", edgecolor="#1a5276", linewidth=1.8,
                          label=f"{name}辖域范围")]
    leg = mapkit.stacked_legends(ax, [
        dict(handles=leg_elements + sym_type_h, title="符号含义",
             ncol=2, fontsize=7.0, title_fontsize=7.6),
        dict(handles=sym_idx_h, title="图上编号对照（编号标注于符号旁）",
             ncol=2, fontsize=6.8, title_fontsize=7.6),
    ], top=-0.010, gap=0.014)

    chart_title = "行政区位图"
    ax.set_title(f"上海市{name}{chart_title}", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
    ax.text(0.5, 1.008, f"Administrative Location & Spatial Structure of {en_name}", transform=ax.transAxes,
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

    e_min, e_max = cfg.get("elev_range", (2.5, 6.0))
    if e_max <= e_min:
        e_max = e_min + 2.0
    norm = Normalize(vmin=e_min, vmax=e_max)
    t_colors = [
        (0.00, "#196f3d"),
        (0.15, "#27ae60"),
        (0.35, "#7dcea0"),
        (0.55, "#f9e79f"),
        (0.75, "#eb984e"),
        (0.90, "#ba4a00"),
        (1.00, "#78281f")
    ]
    cmap = LinearSegmentedColormap.from_list("unit_dem", t_colors)

    hs_sub = calc_hillshade(sub_dem, cur_res)
    rgb_dem = cmap(norm(sub_dem))[:, :, :3]
    rgb_shaded = rgb_dem * (0.44 + 0.56 * hs_sub[:, :, np.newaxis])

    im = ax.imshow(rgb_shaded, extent=sub_extent, origin="upper", zorder=2)
    patch2 = get_mpl_clip_patch(unit_union)
    ax.add_patch(patch2)
    im.set_clip_path(patch2)

    unit_gdf.boundary.plot(ax=ax, color="#1a5276", lw=1.6, zorder=5)

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    sl = mapkit.SymbolLabels(ax, fig)
    sl.reserve([(0.50, 0.0, 1.0, 0.09),
                (0.88, 0.86, 1.0, 1.0)])

    for pname, plon, plat, pelev, ox, oy, direct in cfg.get("peaks", []):
        px, py = to_alb(plon, plat)
        m = "^" if pelev > 20 else "o"
        c = "#78281f" if pelev > 20 else "#27ae60"
        nm, nt = mapkit.split_note(pname)
        sl.add(px, py, nm, "peak", note=nt, priority=1,
               marker=m, face=c, size=6.8, kind_label="主要高程标高与控制极点")

    for wname, wlon, wlat, rot in cfg.get("water_labels", []):
        wx, wy = to_alb(wlon, wlat)
        nm, nt = mapkit.split_note(wname)
        sl.add(wx, wy, nm, "water", note=nt, priority=2,
               marker="s", face="#1f618d", size=5.5, kind_label="骨干河流水系与水面湖泊")

    sym_type_h, sym_idx_h = sl.flush()

    leg = mapkit.stacked_legends(ax, [
        dict(handles=sym_type_h, title="地形与水文要素", ncol=2, fontsize=6.8, title_fontsize=7.6),
        dict(handles=sym_idx_h, title="图上要素编号对照", ncol=2, fontsize=6.8, title_fontsize=7.6),
    ], top=-0.010, gap=0.014)

    add_scalebar(ax, sb_x0, sb_y0, length_km=scale_km)
    add_compass(ax, 0.94, 0.91)

    cax = ax.inset_axes([0.04, 0.06, 0.025, 0.22])
    cb = plt.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cax, orientation="vertical")
    cb.set_label("高程 Elevation (m)", fontsize=6.8, color="#2c3e50")
    cb.ax.tick_params(labelsize=6.0, length=2.0)

    m2_title = "地形地貌图"
    ax.set_title(f"上海市{name}{m2_title}", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
    ax.text(0.5, 1.008, f"Topography, Micro-Relief & Water Network of {en_name}", transform=ax.transAxes,
            ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
    fig.text(0.5, 0.015, "数据源：AWS Terrain GLO-30 30m DEM · 投影：Albers 等积圆锥 · 制作：《中国地理知识手册》",
             ha="center", va="bottom", fontsize=6.5, color="#7f8c8d")

    m2_path = os.path.join(OUT_DIR, f"fig{sec_id}-2_{name}{m2_title}.png")
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

    unit_gdf.plot(ax=ax, facecolor="#fdfefe", edgecolor="#1a5276", lw=1.5, zorder=3)
    sh_prov.boundary.plot(ax=ax, color="#d5dbdb", lw=0.5, ls=":", zorder=2)

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    sl = mapkit.SymbolLabels(ax, fig)
    sl.reserve([(0.0, 0.0, 0.36, 0.28),
                (0.50, 0.0, 1.0, 0.09),
                (0.90, 0.84, 1.0, 1.0)])

    for item in cfg.get("stations", []):
        sname = item[0]
        slon = item[1]
        slat = item[2]
        sx, sy = to_alb(slon, slat)
        if "机场" in sname:
            kind = "airport"
        elif "站" in sname:
            kind = "rail_hub"
        elif "港" in sname or "码头" in sname:
            kind = "port"
        elif "桥" in sname or "线" in sname or "路" in sname:
            kind = "corridor"
        else:
            kind = "dryport"
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
        Line2D([0], [0], color="#c0392b", lw=2.2, label="高速铁路/轨道交通/市域快线"),
        Line2D([0], [0], color="#8e44ad", lw=1.8, label="国际航空空港/深水港区码头"),
        Line2D([0], [0], color="#2980b9", lw=1.8, label="城市高架道路/国家高速公路")
    ]
    leg = mapkit.stacked_legends(ax, [
        dict(handles=leg_elements + sym_type_h, title="线型与交通枢纽含义",
             ncol=2, fontsize=6.8, title_fontsize=7.6),
        dict(handles=sym_idx_h, title="图上编号对照（编号标注于符号旁）",
             ncol=2, fontsize=6.8, title_fontsize=7.6),
    ], top=-0.010, gap=0.013)

    m3_title = "道路交通图"
    ax.set_title(f"上海市{name}{m3_title}", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
    ax.text(0.5, 1.008, f"Integrated Transportation Network & Corridors of {en_name}", transform=ax.transAxes,
            ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
    mapkit.footer_below_legend(
        ax, leg, "数据源：上海市交通委员会 · 综合交通发展白皮书 · 制作：《中国地理知识手册》",
        fontsize=6.5)

    m3_path = os.path.join(OUT_DIR, f"fig{sec_id}-3_{name}{m3_title}.png")
    fig.savefig(m3_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Map 3 saved: {m3_path}")

    # =========================================================================
    # Map 4: 特色专题图
    # =========================================================================
    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    unit_gdf.plot(ax=ax, facecolor="#fdfefe", edgecolor="#1a5276", lw=1.5, zorder=3)
    sh_prov.boundary.plot(ax=ax, color="#d5dbdb", lw=0.5, ls=":", zorder=2)

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")

    sl = mapkit.SymbolLabels(ax, fig)
    sl.reserve([(0.0, 0.0, 0.42, 0.32),
                (0.50, 0.0, 1.0, 0.09),
                (0.90, 0.84, 1.0, 1.0)])

    themes = cfg.get("theme_elements", [])
    theme_palette = [
    ("#c0392b", "o", "重大文保/历史红色经典"),
    ("#1f618d", "s", "现代金融/高能现代服务业"),
    ("#196f3d", "^", "生态保护/滨江卓越水岸"),
    ("#d35400", "D", "先进制造/重装科技硬核"),
    ("#7d3c98", "p", "新质生产力/产业科创枢纽"),
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
        dict(handles=sym_type_h, title="特色专题类别", ncol=2, fontsize=6.8, title_fontsize=7.6),
        dict(handles=sym_idx_h, title="专题要素与战略定位索引", ncol=1, fontsize=6.6, title_fontsize=7.6),
    ], top=-0.010, gap=0.014)

    m4_title = "特色专题图"
    ax.set_title(f"上海市{name}{m4_title}", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
    ax.text(0.5, 1.008, f"Special Thematic & Industrial Features of {en_name}", transform=ax.transAxes,
            ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
    mapkit.footer_below_legend(
        ax, leg, "数据源：上海市各区规划和自然资源局 · 制作：《中国地理知识手册》",
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
    nl_sub = nl_clean_df[nl_clean_df["district_code"].fillna(0).astype(int) == int(adcode)].sort_values("year")

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
    fig.text(0.5, 0.01, "数据来源：夜间灯光遥感时序数据集 (1986-2024) · 上海统计年鉴与历年国民经济和社会发展统计公报 · 制作：《中国地理知识手册》",
             ha="center", va="bottom", fontsize=6.5, color="#7f8c8d")

    m5_path = os.path.join(OUT_DIR, f"fig{sec_id}-5_{name}夜间灯光与经济发展演进图.png")
    fig.savefig(m5_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Map 5 saved: {m5_path}")

def main():
    parser = argparse.ArgumentParser(description="Generate unit maps for Shanghai municipality.")
    parser.add_argument("--code", type=str, default="all", help="Adcode of unit or 'all'")
    args = parser.parse_args()

    if args.code == "all":
        for adcode in SHANGHAI_CONFIGS.keys():
            generate_unit_maps(adcode)
    else:
        generate_unit_maps(args.code)

if __name__ == "__main__":
    main()
