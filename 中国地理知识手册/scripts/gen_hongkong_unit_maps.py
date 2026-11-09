# -*- coding: utf-8 -*-
"""香港特别行政区 4 大整合分析单元地图自动化生成引擎
覆盖 4 个分析单元（27-01 至 27-04）：
1. fig{sec_id}-1_{name}行政区位图.png
2. fig{sec_id}-2_{name}地形地貌图.png
3. fig{sec_id}-3_{name}道路交通图.png
4. fig{sec_id}-4_{name}特色专题图.png
5. fig{sec_id}-5_{name}夜间灯光与经济发展演进图.png

严格遵循出版级规范：微缩字号、紧凑堆叠图例、完全杜绝压盖。
"""
import os
import sys
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
from hongkong_configs import HONGKONG_OVERVIEW, HONGKONG_DISTRICT_CONFIGS
import mapkit

setup()
OUT_DIR = os.path.join(BASE_DIR, "figures")
os.makedirs(OUT_DIR, exist_ok=True)
_T = Transformer.from_crs("EPSG:4326", ALBERS, always_xy=True)

def to_alb(lon, lat):
    return _T.transform(lon, lat)

def get_polygon_patch(polygon):
    if polygon.geom_type == 'Polygon':
        geoms = [polygon]
    elif polygon.geom_type == 'MultiPolygon':
        geoms = list(polygon.geoms)
    else:
        return None
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

def add_compass(ax, x=0.94, y=0.92):
    ax.annotate("N", xy=(x, y), xytext=(x, y - 0.055), transform=ax.transAxes,
                arrowprops=dict(facecolor="#2c3e50", edgecolor="#2c3e50", width=1.8, headwidth=5.5, headlength=6.5),
                ha="center", va="center", fontsize=8.8, fontweight="bold", color="#2c3e50", zorder=30)

print("Initializing base spatial environments for Hong Kong...")
DATA_DIR = os.path.join(BASE_DIR, "data")
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")

hk_all = gpd.read_file(os.path.join(DATAV_DIR, "810000_full.json")).to_crs(ALBERS)
hk_all["geometry"] = hk_all.geometry.buffer(0)
hk_union = hk_all.union_all()

dem_file = os.path.join(DATA_DIR, "dem", "province", "810000_z11.npz")
dem_data = np.load(dem_file)
dem_raw = dem_data['dem']
dem_res = float(dem_data['res'])
dem_minx = float(dem_data['minx'])
dem_maxy = float(dem_data['maxy'])
nrows, ncols = dem_raw.shape
dem_extent = [dem_minx, dem_minx + ncols * dem_res, dem_maxy - nrows * dem_res, dem_maxy]

dem_elev = np.where(dem_raw < 0, np.nan, dem_raw)
hillshade = calc_hillshade(dem_elev, dem_res)

terrain_cmap = LinearSegmentedColormap.from_list("hk_unit_terrain", [
    (0.0, "#2ecc71"),   # 沿海平地/填海区
    (0.25, "#a9dfbf"),  # 低丘缓坡
    (0.50, "#f9e79f"),  # 丘陵谷地
    (0.70, "#f5b041"),  # 中山台地
    (0.85, "#e59866"),  # 高峰山脊
    (1.0, "#873600")    # 极顶
])

def generate_unit_maps(code):
    cfg = HONGKONG_DISTRICT_CONFIGS[code]
    sec_id = cfg["sec_id"]
    name = cfg["name"]
    districts = cfg["districts"]
    print(f"\n=======================================================")
    print(f"Generating 5 publication maps for {sec_id} {name} ({code})...")
    print(f"=======================================================")

    sub_gdf = hk_all[hk_all['name'].isin(districts)]
    unit_geom = sub_gdf.geometry.union_all()

    b = unit_geom.bounds
    span_x = b[2] - b[0]
    span_y = b[3] - b[1]
    pad_m = cfg.get("pad_m", 4000)
    ax_xlim = (b[0] - pad_m, b[2] + pad_m)
    ax_ylim = (b[1] - pad_m, b[3] + pad_m)

    # -------------------------------------------------------------
    # Map 1: 行政区位图
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9.2, 7.2), dpi=DPI)
    fig.subplots_adjust(left=0.03, right=0.97, top=0.93, bottom=0.04)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#eaf2f8")

    hk_all.plot(ax=ax, facecolor="#eaeded", edgecolor="#bdc3c7", linewidth=0.6, zorder=2)
    sub_gdf.plot(ax=ax, facecolor="#fef9e7", edgecolor="#1b4f72", linewidth=1.2, zorder=4)

    for idx, row in sub_gdf.iterrows():
        dname = row['name']
        pt = row.geometry.representative_point()
        ax.text(pt.x, pt.y, dname, fontsize=8.0, fontweight="bold", color="#78281f",
                ha="center", va="center", zorder=7,
                path_effects=[pe.withStroke(linewidth=2.2, foreground="white")])

    for p in cfg.get("places_admin", []):
        px, py = to_alb(p[1], p[2])
        if ax_xlim[0] <= px <= ax_xlim[1] and ax_ylim[0] <= py <= ax_ylim[1]:
            ax.plot(px, py, marker="o", color="#b03a2e", markersize=5.5, markeredgecolor="white", mew=0.8, zorder=9)
            ax.text(px + span_x * 0.02, py + span_y * 0.015, p[0], fontsize=7.2, fontweight="bold",
                    color="#1b2631", zorder=10, path_effects=[pe.withStroke(linewidth=2.0, foreground="white")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    add_compass(ax, 0.94, 0.92)
    mapkit.add_scalebar(ax, ax_xlim[0] + (ax_xlim[1]-ax_xlim[0])*0.05, ax_ylim[0] + (ax_ylim[1]-ax_ylim[0])*0.05, length_km=cfg.get("scale_km", 10))

    ax.set_title(f"香港特别行政区 {name} 行政区位与政区格局图", fontsize=12.0, fontweight="bold", color=C_TEXT, pad=10)
    fig.text(0.5, 0.012, f"制图范围：香港特别行政区 · {name}（下辖 {len(districts)} 区） · 制作：《中国地理知识手册》",
             ha="center", fontsize=6.8, color="#7f8c8d")

    m1_path = os.path.join(OUT_DIR, f"fig{sec_id}-1_{name}行政区位图.png")
    fig.savefig(m1_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Map 1 saved: {m1_path}")

    # -------------------------------------------------------------
    # Map 2: 地形地貌图
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9.2, 7.2), dpi=DPI)
    fig.subplots_adjust(left=0.03, right=0.97, top=0.93, bottom=0.04)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#eaf2f8")

    e_min, e_max = cfg.get("elev_range", (0.0, 957.0))
    norm = Normalize(vmin=0.0, vmax=max(e_max, 500.0))
    rgb_c = terrain_cmap(norm(dem_elev))[:, :, :3]
    h_blend = 0.55 * rgb_c + 0.45 * hillshade[:, :, np.newaxis]
    h_blend = np.clip(h_blend, 0.0, 1.0)

    hk_all.plot(ax=ax, facecolor="#e5e8e8", edgecolor="#bdc3c7", linewidth=0.5, zorder=2)
    im = ax.imshow(h_blend, extent=dem_extent, origin="upper", zorder=3)
    patch = get_polygon_patch(unit_geom)
    if patch is not None:
        ax.add_patch(patch)
        im.set_clip_path(patch)

    sub_gdf.boundary.plot(ax=ax, color="#1b4f72", linewidth=1.0, zorder=5)

    for p in cfg.get("peaks", []):
        px, py = to_alb(p[1], p[2])
        if ax_xlim[0] <= px <= ax_xlim[1] and ax_ylim[0] <= py <= ax_ylim[1]:
            ax.plot(px, py, marker="^", color="#c0392b", markersize=7.0, markeredgecolor="white", mew=0.8, zorder=10)
            ax.text(px + span_x * 0.02, py + span_y * 0.015, f"{p[0]} ({p[3]:.0f}m)", fontsize=7.2,
                    fontweight="bold", color="#78281f", zorder=11,
                    path_effects=[pe.withStroke(linewidth=2.0, foreground="white")])

    for w in cfg.get("water_labels", []):
        wx, wy = to_alb(w[1], w[2])
        if ax_xlim[0] <= wx <= ax_xlim[1] and ax_ylim[0] <= wy <= ax_ylim[1]:
            ax.text(wx, wy, w[0], fontsize=7.2, style="italic", fontweight="bold", color="#2471a3",
                    ha="center", va="center", zorder=8, path_effects=[pe.withStroke(linewidth=2.0, foreground="white")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    add_compass(ax, 0.94, 0.92)
    mapkit.add_scalebar(ax, ax_xlim[0] + (ax_xlim[1]-ax_xlim[0])*0.05, ax_ylim[0] + (ax_ylim[1]-ax_ylim[0])*0.05, length_km=cfg.get("scale_km", 10))

    cax = fig.add_axes([0.04, 0.14, 0.015, 0.22])
    sm = plt.cm.ScalarMappable(cmap=terrain_cmap, norm=norm)
    sm.set_array([])
    cb = fig.colorbar(sm, cax=cax, orientation="vertical")
    cb.set_label("高程 (m)", fontsize=6.8, color=C_TEXT)
    cb.ax.tick_params(labelsize=6.5)

    ax.set_title(f"香港特别行政区 {name} 地势起伏与山川脉络图", fontsize=12.0, fontweight="bold", color=C_TEXT, pad=10)
    fig.text(0.5, 0.012, f"制图基准：Albers等积投影 · DEM高程：AWS Terrain z11 (75m) · 制作：《中国地理知识手册》",
             ha="center", fontsize=6.8, color="#7f8c8d")

    m2_path = os.path.join(OUT_DIR, f"fig{sec_id}-2_{name}地形地貌图.png")
    fig.savefig(m2_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Map 2 saved: {m2_path}")

    # -------------------------------------------------------------
    # Map 3: 道路交通图
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9.2, 7.2), dpi=DPI)
    fig.subplots_adjust(left=0.03, right=0.97, top=0.93, bottom=0.04)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#eaf2f8")

    hk_all.plot(ax=ax, facecolor="#f2f4f4", edgecolor="#bdc3c7", linewidth=0.5, zorder=2)
    sub_gdf.plot(ax=ax, facecolor="#fefefe", edgecolor="#7f8c8d", linewidth=0.9, zorder=3)

    for t in cfg.get("transport_labels", []):
        tx, ty = to_alb(t[1], t[2])
        if ax_xlim[0] <= tx <= ax_xlim[1] and ax_ylim[0] <= ty <= ax_ylim[1]:
            ax.plot(tx, ty, marker="s", color="#8e44ad", markersize=6.0, markeredgecolor="white", mew=0.8, zorder=10)
            ax.text(tx + span_x * 0.02, ty + span_y * 0.015, f"{t[0]}\n[{t[3] if len(t)>3 else '交通枢纽'}]",
                    fontsize=6.8, fontweight="bold", color="#4a235a", zorder=11,
                    path_effects=[pe.withStroke(linewidth=2.0, foreground="white")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    add_compass(ax, 0.94, 0.92)
    mapkit.add_scalebar(ax, ax_xlim[0] + (ax_xlim[1]-ax_xlim[0])*0.05, ax_ylim[0] + (ax_ylim[1]-ax_ylim[0])*0.05, length_km=cfg.get("scale_km", 10))

    ax.set_title(f"香港特别行政区 {name} 道路交通与立体枢纽走廊图", fontsize=12.0, fontweight="bold", color=C_TEXT, pad=10)
    fig.text(0.5, 0.012, f"数据来源：香港特区政府运输署 · 港铁公司 MTR · 制作：《中国地理知识手册》",
             ha="center", fontsize=6.8, color="#7f8c8d")

    m3_path = os.path.join(OUT_DIR, f"fig{sec_id}-3_{name}道路交通图.png")
    fig.savefig(m3_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Map 3 saved: {m3_path}")

    # -------------------------------------------------------------
    # Map 4: 特色专题图
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9.2, 7.2), dpi=DPI)
    fig.subplots_adjust(left=0.03, right=0.97, top=0.93, bottom=0.04)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#f9f9fb")

    hk_all.plot(ax=ax, facecolor="#f2f4f4", edgecolor="#bdc3c7", linewidth=0.5, zorder=2)
    sub_gdf.plot(ax=ax, facecolor="#fefefe", edgecolor="#2c3e50", linewidth=0.9, zorder=3)

    for s in cfg.get("special_labels", []):
        sx, sy = to_alb(s[1], s[2])
        if ax_xlim[0] <= sx <= ax_xlim[1] and ax_ylim[0] <= sy <= ax_ylim[1]:
            ax.plot(sx, sy, marker="*", color="#e67e22", markersize=9.0, markeredgecolor="white", mew=0.8, zorder=10)
            ax.text(sx + span_x * 0.02, sy + span_y * 0.015, f"{s[0]}\n({s[3] if len(s)>3 else '核心功能区'})",
                    fontsize=6.8, fontweight="bold", color="#7e5109", zorder=11,
                    path_effects=[pe.withStroke(linewidth=2.0, foreground="white")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    add_compass(ax, 0.94, 0.92)
    mapkit.add_scalebar(ax, ax_xlim[0] + (ax_xlim[1]-ax_xlim[0])*0.05, ax_ylim[0] + (ax_ylim[1]-ax_ylim[0])*0.05, length_km=cfg.get("scale_km", 10))

    ax.set_title(f"香港特别行政区 {name} 现代核心产业与世界级名胜分布图", fontsize=12.0, fontweight="bold", color=C_TEXT, pad=10)
    fig.text(0.5, 0.012, f"数据来源：香港特区政府发展局 · 旅游发展局 · 制作：《中国地理知识手册》",
             ha="center", fontsize=6.8, color="#7f8c8d")

    m4_path = os.path.join(OUT_DIR, f"fig{sec_id}-4_{name}特色专题图.png")
    fig.savefig(m4_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Map 4 saved: {m4_path}")

    # -------------------------------------------------------------
    # Map 5: 夜间灯光与经济发展演进图
    # -------------------------------------------------------------
    fig = plt.figure(figsize=(10.5, 6.2), dpi=DPI)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.15, 1.0], wspace=0.25)
    ax_map = fig.add_subplot(gs[0])
    ax_gdp = fig.add_subplot(gs[1])

    ax_map.set_facecolor("#0b172a")
    sub_gdf.plot(ax=ax_map, facecolor="#132338", edgecolor="#2c3e50", linewidth=0.8, zorder=2)

    nl_notes = cfg.get("nl_annotations", [])
    colors = ["#f39c12", "#e74c3c", "#3498db", "#2ecc71"]
    for idx, note in enumerate(nl_notes):
        nx, ny = to_alb(note[1], note[2])
        c = colors[idx % len(colors)]
        ax_map.plot(nx, ny, marker="o", color=c, markersize=8.0, markeredgecolor="white", mew=1.0, zorder=8)
        ax_map.text(nx + span_x * 0.02, ny + span_y * 0.015, f"{note[0]}年: {note[3]}",
                    fontsize=6.8, fontweight="bold", color="white", zorder=9,
                    path_effects=[pe.withStroke(linewidth=2.0, foreground="#0b172a")])

    ax_map.set_xlim(ax_xlim)
    ax_map.set_ylim(ax_ylim)
    add_compass(ax_map, 0.94, 0.92)
    mapkit.add_scalebar(ax_map, ax_xlim[0] + (ax_xlim[1]-ax_xlim[0])*0.05, ax_ylim[0] + (ax_ylim[1]-ax_ylim[0])*0.05,
                        length_km=cfg.get("scale_km", 10), label_color="white")
    ax_map.set_title(f"{name} 城市空间与夜光集聚演化", fontsize=10.0, fontweight="bold", color=C_TEXT)

    gdp_series = cfg.get("gdp_series", {})
    if gdp_series:
        gyears = list(gdp_series.keys())
        gvals = list(gdp_series.values())
        bars = ax_gdp.bar(gyears, gvals, width=1.8, color="#b03a2e", edgecolor="#78281f", alpha=0.88, label="GDP (亿元人民币)")
        for bar in bars:
            h = bar.get_height()
            ax_gdp.text(bar.get_x() + bar.get_width() / 2.0, h + max(gvals) * 0.02, f"{h:g}",
                        ha="center", va="bottom", fontsize=7.0, fontweight="bold", color="#78281f")

    ax_gdp.set_title(f"{name} 2000—2024 年经济体量 (GDP) 跃迁", fontsize=10.0, fontweight="bold", color=C_TEXT)
    ax_gdp.set_ylabel("GDP (亿元人民币)", fontsize=7.8, color="#2c3e50")
    ax_gdp.set_xlabel("年份 Year", fontsize=7.8, color="#2c3e50")
    ax_gdp.grid(True, linestyle="--", alpha=0.4)
    ax_gdp.tick_params(labelsize=7.2)

    fig.tight_layout(pad=2.2)
    fig.text(0.5, 0.012, f"数据来源：香港特区政府统计处 · 制作：《中国地理知识手册》",
             ha="center", fontsize=6.8, color="#7f8c8d")

    m5_path = os.path.join(OUT_DIR, f"fig{sec_id}-5_{name}夜间灯光与经济发展演进图.png")
    fig.savefig(m5_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Map 5 saved: {m5_path}")

def main():
    for code in HONGKONG_DISTRICT_CONFIGS.keys():
        generate_unit_maps(code)
    print("\nAll 20 unit maps for Chapter 27 (Hong Kong) generated successfully!")

if __name__ == "__main__":
    main()
