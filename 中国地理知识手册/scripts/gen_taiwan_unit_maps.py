# -*- coding: utf-8 -*-
"""台湾省 4 大整合分析单元地图自动化生成引擎
覆盖 4 个分析单元（26-01 至 26-04），每个单元 5 幅出版级专业地图，共 20 幅：
1. fig{sec_id}-1_{name}行政区位图.png
2. fig{sec_id}-2_{name}地形地貌图.png
3. fig{sec_id}-3_{name}道路交通图.png
4. fig{sec_id}-4_{name}特色专题图.png
5. fig{sec_id}-5_{name}夜间灯光与经济发展演进图.png

严格遵循出版级海淀标杆规范：微缩字号、紧凑图例、无注记压盖、真实矢量底图。
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

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册"
sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))
from style import ALBERS, C_TEXT, DATA, DPI, FIGURES, setup
from taiwan_configs import TAIWAN_OVERVIEW, TAIWAN_DISTRICT_CONFIGS
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

print("Initializing base spatial environments for Taiwan...")
DATA_DIR = os.path.join(BASE_DIR, "data")
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")

tw_all = gpd.read_file(os.path.join(DATAV_DIR, "710000.json")).to_crs(ALBERS)
tw_all["geometry"] = tw_all.geometry.buffer(0)
tw_union = tw_all.union_all()

dem_file = os.path.join(DATA_DIR, "dem", "province", "710000_z9.npz")
dem_data = np.load(dem_file)
dem_raw = dem_data['dem']
dem_res = float(dem_data['res'])
dem_minx = float(dem_data['minx'])
dem_maxy = float(dem_data['maxy'])
nrows, ncols = dem_raw.shape
dem_extent = [dem_minx, dem_minx + ncols * dem_res, dem_maxy - nrows * dem_res, dem_maxy]

dem_elev = np.where(dem_raw < 0, np.nan, dem_raw)
hillshade = calc_hillshade(dem_elev, dem_res)

terrain_cmap = LinearSegmentedColormap.from_list("tw_unit_terrain", [
    (0.0, "#27ae60"),    # 平原/台地绿
    (0.15, "#a9dfbf"),   # 低丘陵浅绿
    (0.35, "#f9e79f"),   # 丘陵谷地黄
    (0.55, "#f39c12"),   # 中山橙黄
    (0.75, "#ba4a00"),   # 高山林带红褐
    (0.90, "#6e2c00"),   # 极高山荒漠深褐
    (1.0, "#f2f4f4")     # 极顶苍白
])

def generate_unit_maps(code):
    cfg = TAIWAN_DISTRICT_CONFIGS[code]
    sec_id = cfg["sec_id"]
    name = cfg["name"]
    counties = cfg["counties"]
    print(f"\n=======================================================")
    print(f"Generating 5 publication maps for {sec_id} {name} ({code})...")
    print(f"=======================================================")

    # 计算该单元在 Albers 投影下的范围边界
    pts = []
    for p in cfg.get("places_admin", []):
        if "钓鱼岛" not in p[0]:
            pts.append(to_alb(p[1], p[2]))
    for pk in cfg.get("peaks", []):
        pts.append(to_alb(pk[1], pk[2]))
    for w in cfg.get("water_labels", []):
        pts.append(to_alb(w[1], w[2]))
    for t in cfg.get("transport_labels", []):
        pts.append(to_alb(t[1], t[2]))
    for s in cfg.get("special_labels", []):
        pts.append(to_alb(s[1], s[2]))

    xs = [pt[0] for pt in pts]
    ys = [pt[1] for pt in pts]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max_x - min_x
    span_y = max_y - min_y
    pad_m = cfg.get("pad_m", 10000)

    # 针对各单元进行视觉比例优化
    if code == "710100":  # 北部
        ax_xlim = (min_x - pad_m - 8000, max_x + pad_m + 8000)
        ax_ylim = (min_y - pad_m, max_y + pad_m)
    elif code == "710200": # 中西部
        ax_xlim = (min_x - pad_m - 12000, max_x + pad_m + 12000)
        ax_ylim = (min_y - pad_m, max_y + pad_m)
    elif code == "710300": # 南部
        ax_xlim = (min_x - pad_m - 12000, max_x + pad_m + 12000)
        ax_ylim = (min_y - pad_m, max_y + pad_m)
    else: # 710400 东部与海岛
        ax_xlim = (min_x - pad_m - 15000, max_x + pad_m + 15000)
        ax_ylim = (min_y - pad_m, max_y + pad_m)

    # -------------------------------------------------------------
    # Map 1: 行政区位图
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9.2, 7.8), dpi=DPI)
    fig.subplots_adjust(left=0.03, right=0.97, top=0.93, bottom=0.04)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#eaf2f8")

    tw_all.plot(ax=ax, facecolor="#fef9e7", edgecolor="#2c3e50", linewidth=1.2, zorder=3)

    # 绘制各县市中心点与标注
    for p in cfg.get("places_admin", []):
        if "钓鱼岛" in p[0]:
            continue
        px, py = to_alb(p[1], p[2])
        if ax_xlim[0] <= px <= ax_xlim[1] and ax_ylim[0] <= py <= ax_ylim[1]:
            ax.plot(px, py, marker="o", color="#b03a2e", markersize=6.0, markeredgecolor="white", mew=1.0, zorder=9)
            ax.text(px + 6000, py + 2000, p[0].split(" ")[0], fontsize=8.0, fontweight="bold",
                    color="#1b2631", zorder=10, path_effects=[pe.withStroke(linewidth=2.2, foreground="white")])

    # 邻近相邻区域文字提示
    if code == "710100":
        ax.text(1630000, 2670000, "← 邻接中西部平原与盆地区", fontsize=8.5, color="#7f8c8d", fontweight="bold")
    elif code == "710200":
        ax.text(1640000, 2710000, "↑ 邻接北部都会区", fontsize=8.5, color="#7f8c8d", fontweight="bold")
        ax.text(1600000, 2580000, "↓ 邻接南部临港重工业与农科区", fontsize=8.5, color="#7f8c8d", fontweight="bold")
    elif code == "710300":
        ax.text(1600000, 2595000, "↑ 邻接中西部平原与盆地区", fontsize=8.5, color="#7f8c8d", fontweight="bold")
    elif code == "710400":
        ax.text(1580000, 2600000, "← 隔中央山脉与西部平原相望", fontsize=8.5, color="#7f8c8d", fontweight="bold")

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    add_compass(ax, 0.94, 0.92)
    mapkit.add_scalebar(ax, ax_xlim[0] + (ax_xlim[1]-ax_xlim[0])*0.05, ax_ylim[0] + (ax_ylim[1]-ax_ylim[0])*0.05, length_km=cfg.get("scale_km", 20))

    ax.set_title(f"台湾省 {name} 行政区位与政区格局图", fontsize=12.5, fontweight="bold", color=C_TEXT, pad=10)
    fig.text(0.5, 0.012, f"制图范围：台湾省 · {name}（涵盖 {len(counties)} 个县市） · 制作：《中国地理知识手册》",
             ha="center", fontsize=7.2, color="#7f8c8d")

    m1_path = os.path.join(OUT_DIR, f"fig{sec_id}-1_{name}行政区位图.png")
    fig.savefig(m1_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Map 1 saved: {m1_path}")

    # -------------------------------------------------------------
    # Map 2: 地形地貌图
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9.2, 7.8), dpi=DPI)
    fig.subplots_adjust(left=0.03, right=0.97, top=0.93, bottom=0.04)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#eaf2f8")

    e_min, e_max = cfg.get("elev_range", (0.0, 3952.0))
    norm = Normalize(vmin=0.0, vmax=max(e_max, 1000.0))
    rgb_c = terrain_cmap(norm(dem_elev))[:, :, :3]
    h_blend = 0.52 * rgb_c + 0.48 * hillshade[:, :, np.newaxis]
    h_blend = np.clip(h_blend, 0.0, 1.0)

    im = ax.imshow(h_blend, extent=dem_extent, origin="upper", zorder=3)
    patch = get_polygon_patch(tw_union)
    if patch is not None:
        ax.add_patch(patch)
        im.set_clip_path(patch)

    tw_all.plot(ax=ax, facecolor="none", edgecolor="#2c3e50", linewidth=0.9, zorder=5)

    # 标注重要山峰
    for pk in cfg.get("peaks", []):
        px, py = to_alb(pk[1], pk[2])
        if ax_xlim[0] <= px <= ax_xlim[1] and ax_ylim[0] <= py <= ax_ylim[1]:
            ax.plot(px, py, marker="^", color="#c0392b", markersize=7.2, markeredgecolor="white", mew=1.0, zorder=9)
            ax.text(px + 5000, py, f"{pk[0]} ({pk[3]:.0f}m)", fontsize=7.6, fontweight="bold",
                    color="#78281f", zorder=10, va="center", path_effects=[pe.withStroke(linewidth=2.2, foreground="white")])

    # 标注主要水系
    for w in cfg.get("water_labels", []):
        wx, wy = to_alb(w[1], w[2])
        if ax_xlim[0] <= wx <= ax_xlim[1] and ax_ylim[0] <= wy <= ax_ylim[1]:
            ax.text(wx, wy, w[0], fontsize=7.6, fontstyle="italic", fontweight="bold",
                    color="#1b4f72", zorder=10, ha="center", va="center",
                    path_effects=[pe.withStroke(linewidth=2.2, foreground="#eaf2f8")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    add_compass(ax, 0.94, 0.92)
    mapkit.add_scalebar(ax, ax_xlim[0] + (ax_xlim[1]-ax_xlim[0])*0.05, ax_ylim[0] + (ax_ylim[1]-ax_ylim[0])*0.05, length_km=cfg.get("scale_km", 20))

    ax.set_title(f"台湾省 {name} 地势起伏与山川脉络图", fontsize=12.5, fontweight="bold", color=C_TEXT, pad=10)
    fig.text(0.5, 0.012, f"拔海标高跨度：${e_min:.0f}\\text{{ m}} \\sim {e_max:.1f}\\text{{ m}}$ · 制作：《中国地理知识手册》",
             ha="center", fontsize=7.2, color="#7f8c8d")

    m2_path = os.path.join(OUT_DIR, f"fig{sec_id}-2_{name}地形地貌图.png")
    fig.savefig(m2_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Map 2 saved: {m2_path}")

    # -------------------------------------------------------------
    # Map 3: 道路交通图
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9.2, 7.8), dpi=DPI)
    fig.subplots_adjust(left=0.03, right=0.97, top=0.93, bottom=0.04)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#fcfcfc")

    tw_all.plot(ax=ax, facecolor="#edf2f7", edgecolor="#a0aec0", linewidth=0.8, zorder=2)

    # 绘制骨干干线
    for hname, coords, color, lw in TAIWAN_OVERVIEW["highways"]:
        alb_pts = [to_alb(pt[0], pt[1]) for pt in coords]
        xs, ys = zip(*alb_pts)
        if "HSR" in hname:
            ax.plot(xs, ys, color=color, linewidth=lw + 1.2, linestyle="-", zorder=6, alpha=0.95)
            ax.plot(xs, ys, color="white", linewidth=lw - 0.8, linestyle="--", zorder=7)
        else:
            ax.plot(xs, ys, color=color, linewidth=lw, linestyle="-", zorder=5, alpha=0.85)

    # 标注本区交通枢纽
    for t in cfg.get("transport_labels", []):
        tx, ty = to_alb(t[1], t[2])
        if ax_xlim[0] <= tx <= ax_xlim[1] and ax_ylim[0] <= ty <= ax_ylim[1]:
            ax.plot(tx, ty, marker="s", color="#8e44ad", markersize=6.0, markeredgecolor="white", mew=0.8, zorder=9)
            ax.text(tx + 5000, ty, t[0], fontsize=7.6, fontweight="bold",
                    color="#4a235a", zorder=10, va="center", path_effects=[pe.withStroke(linewidth=2.0, foreground="white")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    add_compass(ax, 0.94, 0.92)
    mapkit.add_scalebar(ax, ax_xlim[0] + (ax_xlim[1]-ax_xlim[0])*0.05, ax_ylim[0] + (ax_ylim[1]-ax_ylim[0])*0.05, length_km=cfg.get("scale_km", 20))

    ax.set_title(f"台湾省 {name} 道路交通与立体枢纽走廊图", fontsize=12.5, fontweight="bold", color=C_TEXT, pad=10)
    fig.text(0.5, 0.012, f"立体交通廊道：台湾高铁 / 环岛干线铁路 / 国道高速公路群 · 制作：《中国地理知识手册》",
             ha="center", fontsize=7.2, color="#7f8c8d")

    m3_path = os.path.join(OUT_DIR, f"fig{sec_id}-3_{name}道路交通图.png")
    fig.savefig(m3_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Map 3 saved: {m3_path}")

    # -------------------------------------------------------------
    # Map 4: 特色专题图
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9.2, 7.8), dpi=DPI)
    fig.subplots_adjust(left=0.03, right=0.97, top=0.93, bottom=0.04)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#f9fafb")

    tw_all.plot(ax=ax, facecolor="#edf2f7", edgecolor="#cbd5e0", linewidth=0.8, zorder=2)

    for s in cfg.get("special_labels", []):
        sx, sy = to_alb(s[1], s[2])
        if ax_xlim[0] <= sx <= ax_xlim[1] and ax_ylim[0] <= sy <= ax_ylim[1]:
            ax.plot(sx, sy, marker="*", color="#d35400", markersize=9.0, markeredgecolor="white", mew=1.0, zorder=9)
            ax.text(sx + 5000, sy, s[0], fontsize=7.6, fontweight="bold",
                    color="#7e5109", zorder=10, va="center", path_effects=[pe.withStroke(linewidth=2.0, foreground="white")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    add_compass(ax, 0.94, 0.92)
    mapkit.add_scalebar(ax, ax_xlim[0] + (ax_xlim[1]-ax_xlim[0])*0.05, ax_ylim[0] + (ax_ylim[1]-ax_ylim[0])*0.05, length_km=cfg.get("scale_km", 20))

    ax.set_title(f"台湾省 {name} 现代核心产业与世界级名胜分布图", fontsize=12.5, fontweight="bold", color=C_TEXT, pad=10)
    fig.text(0.5, 0.012, f"高新技术园区 · 核心文化名胜 · 战略重点平台 · 制作：《中国地理知识手册》",
             ha="center", fontsize=7.2, color="#7f8c8d")

    m4_path = os.path.join(OUT_DIR, f"fig{sec_id}-4_{name}特色专题图.png")
    fig.savefig(m4_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Map 4 saved: {m4_path}")

    # -------------------------------------------------------------
    # Map 5: 夜间灯光与经济发展演进图
    # -------------------------------------------------------------
    fig = plt.figure(figsize=(10.0, 7.2), dpi=DPI)
    fig.patch.set_facecolor("white")
    gs = fig.add_gridspec(2, 2, height_ratios=[1.2, 1.0], hspace=0.35, wspace=0.25, left=0.08, right=0.95, top=0.91, bottom=0.08)

    # Panel A: 卫星夜间灯光演变多期图例示意
    ax_nl = fig.add_subplot(gs[0, :])
    ax_nl.set_facecolor("#0b132b")

    years_nl = [1986, 2000, 2015, 2024]
    box_w = 0.22
    for i, yr in enumerate(years_nl):
        sub_x = 0.04 + i * 0.24
        rect = Rectangle((sub_x, 0.15), box_w, 0.70, transform=ax_nl.transAxes,
                         facecolor="#1c2541", edgecolor="#48cae4", linewidth=1.1)
        ax_nl.add_patch(rect)
        ax_nl.text(sub_x + box_w/2, 0.72, f"{yr} 年灯光印记", transform=ax_nl.transAxes,
                   ha="center", va="center", color="#f1faee", fontsize=8.2, fontweight="bold")

        nl_note = ""
        for n in cfg.get("nl_annotations", []):
            if n[0] == yr:
                nl_note = n[4] if len(n) > 4 else n[-1]
                break
        if not nl_note:
            nl_note = "经济与城镇空间稳步拓展"

        ax_nl.text(sub_x + box_w/2, 0.42, nl_note, transform=ax_nl.transAxes,
                   ha="center", va="center", color="#a8dadc", fontsize=7.0, wrap=True,
                   multialignment="center")

    ax_nl.set_title(f"1986—2024 年卫星夜间灯光与城市化演进（{name}）", fontsize=10.0, fontweight="bold", color="#f1faee", pad=8)
    ax_nl.set_xticks([])
    ax_nl.set_yticks([])

    # Panel B: 地区生产总值跨越柱状图
    ax_gdp = fig.add_subplot(gs[1, 0])
    gdp_data = cfg.get("gdp_series", {})
    yrs = sorted(gdp_data.keys())
    vals = [gdp_data[y] for y in yrs]

    bars = ax_gdp.bar(yrs, vals, width=2.4, color="#2980b9", edgecolor="#1b4f72", linewidth=0.9, zorder=3)
    ax_gdp.plot(yrs, vals, marker="o", color="#e74c3c", linewidth=1.8, markersize=5.0, zorder=4)
    for b, v in zip(bars, vals):
        ax_gdp.text(b.get_x() + b.get_width()/2, v + max(vals)*0.02, f"{v:,.0f}",
                    ha="center", va="bottom", fontsize=7.2, fontweight="bold", color="#2c3e50")

    ax_gdp.set_title("地区生产总值（折合人民币亿元）", fontsize=9.2, fontweight="bold", color=C_TEXT)
    ax_gdp.set_ylabel("亿元人民币", fontsize=8.0, fontweight="bold")
    ax_gdp.grid(True, linestyle="--", alpha=0.4, zorder=0)

    # Panel C: 关键发展指标卡片
    ax_card = fig.add_subplot(gs[1, 1])
    ax_card.set_facecolor("#f8f9fa")
    for spine in ax_card.spines.values():
        spine.set_edgecolor("#cbd5e0")

    info_text = (
        f"【{name} 2024 年核心发展指标】\n\n"
        f"• 陆地总面积: {cfg.get('area_km2', 0):,.1f} 平方公里\n"
        f"• 常住总人口: {cfg.get('pop_wan', 0):.1f} 万人\n"
        f"• 城镇化水平: {cfg.get('urban_rate', 0):.1f}%\n"
        f"• 2024 年 GDP: {cfg.get('gdp_2024', 0):,.1f} 亿元人民币\n"
        f"• 人均 GDP: {cfg.get('per_gdp_yuan', 0):,} 元人民币\n"
        f"• 三次产业结构: {cfg.get('structure', '—')}"
    )
    ax_card.text(0.08, 0.50, info_text, transform=ax_card.transAxes, fontsize=8.0,
                 va="center", color="#2c3e50", linespacing=1.4)
    ax_card.set_xticks([])
    ax_card.set_yticks([])

    fig.suptitle(f"台湾省 {name} 夜间灯光与经济发展演进图", fontsize=12.5, fontweight="bold", y=0.98, color=C_TEXT)
    m5_path = os.path.join(OUT_DIR, f"fig{sec_id}-5_{name}夜间灯光与经济发展演进图.png")
    fig.savefig(m5_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Map 5 saved: {m5_path}")

def main():
    for code in sorted(TAIWAN_DISTRICT_CONFIGS.keys()):
        generate_unit_maps(code)
    print("\nAll 20 unit maps for Chapter 26 (Taiwan) generated successfully!")

if __name__ == "__main__":
    main()
