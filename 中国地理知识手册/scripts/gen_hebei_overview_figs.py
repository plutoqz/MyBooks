# -*- coding: utf-8 -*-
"""河北省地理统揽专题地图生成引擎（03-00）
包含 5 幅全省域权威地图与分析图表（精细调优排版、缩减字号、杜绝压盖、杜绝要素倒置）：
1. fig03-00-1_河北省地形地貌与海陆地势格局图.png
2. fig03-00-2_河北省行政区划与空间骨架图.png
3. fig03-00-3_河北省综合立体交通网与海陆空枢纽图.png
4. fig03-00-4_河北省产业经济与先进制造业带分布图.png
5. fig03-00-5_河北省生态安全屏障与自然水系格局图.png
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

def add_scalebar(ax, x0, y0, length_km=100):
    """统一走 mapkit 版本，按像素宽度自适应是否画中点刻度。"""
    import mapkit
    mapkit.add_scalebar(ax, x0, y0, length_km=length_km)

def add_compass(ax, x=0.94, y=0.92):
    ax.annotate("N", xy=(x, y), xytext=(x, y - 0.055), transform=ax.transAxes,
                arrowprops=dict(facecolor="#2c3e50", edgecolor="#2c3e50", width=1.8, headwidth=5.5, headlength=6.5),
                ha="center", va="center", fontsize=8.8, fontweight="bold", color="#2c3e50", zorder=30)

print("Loading Hebei provincial spatial data...")
DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
hb_cities = gpd.read_file(os.path.join(DATA_DIR, "boundaries", "datav", "130000_full.json")).to_crs(ALBERS)
hb_union = hb_cities.unary_union
bb = hb_cities.total_bounds

# 视口与中心计算
cx = (bb[0] + bb[2]) / 2.0
cy = (bb[1] + bb[3]) / 2.0
span_x = bb[2] - bb[0]
span_y = bb[3] - bb[1]
max_span = max(span_x, span_y)

half_span_x = max_span * 0.54
half_span_y = max_span * 0.56
ax_xlim = (cx - half_span_x * 0.98, cx + half_span_x * 1.02)
ax_ylim = (cy - half_span_y * 0.96, cy + half_span_y * 1.06)

# 加载 DEM
print("Loading Hebei DEM...")
dem_hb, dem_minx, dem_maxy, dem_res = prov_dem("130000", zoom=9, res=300.0)

# 加载京津界线作为地理背景参考
bj_all = gpd.read_file(os.path.join(DATA_DIR, "boundaries", "datav", "110000_full.json")).to_crs(ALBERS)
tj_all = gpd.read_file(os.path.join(DATA_DIR, "boundaries", "datav", "120000_full.json")).to_crs(ALBERS)
bj_union = bj_all.unary_union
tj_union = tj_all.unary_union

# 提取雄安新区、辛集市、定州市边界
bd_sub = gpd.read_file(os.path.join(DATA_DIR, "boundaries", "datav", "130600_full.json")).to_crs(ALBERS)
sjz_sub = gpd.read_file(os.path.join(DATA_DIR, "boundaries", "datav", "130100_full.json")).to_crs(ALBERS)

xiongan_geom = bd_sub[bd_sub['adcode'].astype(str).isin(['130629', '130632', '130638'])].unary_union
xinji_geom = sjz_sub[sjz_sub['adcode'].astype(str) == '130181'].geometry.iloc[0]
dingzhou_geom = bd_sub[bd_sub['adcode'].astype(str) == '130682'].geometry.iloc[0]

# 加载 OSM 骨干水系与路网
print("Loading Hebei OSM base layers...")
osm_dir = os.path.join(DATA_DIR, "transport", "hebei")
waterways_full = gpd.read_file(os.path.join(osm_dir, "gis_osm_waterways_free_1.shp")).to_crs(ALBERS)
water_a_full = gpd.read_file(os.path.join(osm_dir, "gis_osm_water_a_free_1.shp")).to_crs(ALBERS)
rails_full = gpd.read_file(os.path.join(osm_dir, "gis_osm_railways_free_1.shp")).to_crs(ALBERS)
roads_full = gpd.read_file(os.path.join(osm_dir, "gis_osm_roads_free_1.shp")).to_crs(ALBERS)

# 筛选大河流与主水体并裁切到河北省界（彻底消除京津背景中的碎线污染）
main_rivers_raw = waterways_full[waterways_full['fclass'].isin(['river', 'canal'])]
main_lakes_raw = water_a_full[water_a_full['fclass'].isin(['water', 'reservoir', 'wetland'])]
main_rivers = gpd.clip(main_rivers_raw, hb_union)
main_lakes = gpd.clip(main_lakes_raw, hb_union)
main_rails = gpd.clip(rails_full[rails_full['fclass'].isin(['rail', 'narrow_gauge'])], hb_union)
motorways = gpd.clip(roads_full[roads_full['fclass'].isin(['motorway', 'motorway_link', 'trunk'])], hb_union)

print("Spatial base layers successfully initialized and clipped.")

# 11 地级市政府驻地权威坐标
CITY_GOV_COORDS = {
    "石家庄市": (114.515, 38.042),
    "唐山市": (118.180, 39.630),
    "秦皇岛市": (119.600, 39.935),
    "邯郸市": (114.490, 36.612),
    "邢台市": (114.508, 37.070),
    "保定市": (115.465, 38.874),
    "张家口市": (114.886, 40.810),
    "承德市": (117.963, 40.953),
    "沧州市": (116.839, 38.304),
    "廊坊市": (116.704, 39.528),
    "衡水市": (115.670, 37.739)
}

# =============================================================================
# 1. fig03-00-1_河北省地形地貌与海陆地势格局图
# =============================================================================
def gen_fig1():
    print("Generating fig03-00-1_河北省地形地貌与海陆地势格局图.png...")
    fig, ax = plt.subplots(figsize=(10.5, 10.5), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    # DEM 渲染
    hs = calc_hillshade(dem_hb, dem_res)
    colors = [
        (0.00, "#a8c878"),   # 平原与低地绿
        (0.08, "#cce09b"),
        (0.20, "#e8d696"),   # 浅丘陵黄褐
        (0.40, "#d2b48c"),   # 山地棕褐
        (0.65, "#a0785a"),   # 高中山深褐
        (0.85, "#8b6548"),
        (1.00, "#f5f5f5")    # 极高峰灰白
    ]
    cmap_elev = LinearSegmentedColormap.from_list("hebei_relief", colors)
    valid = np.nan_to_num(dem_hb, nan=0.0)
    valid = np.clip(valid, 0.0, 2882.0)
    norm = Normalize(vmin=0, vmax=2882)
    rgb = cmap_elev(norm(valid))[:, :, :3]
    rgb_shaded = rgb * (0.42 + 0.58 * hs[:, :, np.newaxis])

    dem_extent = (dem_minx, dem_minx + dem_hb.shape[1] * dem_res,
                  dem_maxy - dem_hb.shape[0] * dem_res, dem_maxy)
    im = ax.imshow(rgb_shaded, extent=dem_extent, origin="upper", zorder=3)
    patch = get_mpl_clip_patch(hb_union)
    ax.add_patch(patch)
    im.set_clip_path(patch)

    # 绘制京津轮廓以展现环抱格局（底色柔和，保持干净）
    gpd.GeoSeries([bj_union]).plot(ax=ax, facecolor="#f2f4f4", edgecolor="#7f8c8d", lw=0.9, ls="--", alpha=0.8, zorder=4)
    gpd.GeoSeries([tj_union]).plot(ax=ax, facecolor="#f2f4f4", edgecolor="#7f8c8d", lw=0.9, ls="--", alpha=0.8, zorder=4)
    bj_cx, bj_cy = to_alb(116.40, 39.90)
    tj_cx, tj_cy = to_alb(117.20, 39.12)
    ax.text(bj_cx, bj_cy, "北京市\n(Beijing)", ha="center", va="center", fontsize=7.8, fontweight="bold", color="#555555",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="#ffffff", edgecolor="#bdc3c7", alpha=0.85), zorder=12)
    ax.text(tj_cx, tj_cy, "天津市\n(Tianjin)", ha="center", va="center", fontsize=7.8, fontweight="bold", color="#555555",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="#ffffff", edgecolor="#bdc3c7", alpha=0.85), zorder=12)

    # 绘制河北省界与各市分界
    hb_cities.boundary.plot(ax=ax, color="#2c3e50", lw=0.6, ls=":", zorder=5)
    gpd.GeoSeries([hb_union]).boundary.plot(ax=ax, color="#1a252f", lw=1.2, zorder=6)

    # 叠置水系（已裁切至省界）
    main_lakes.plot(ax=ax, facecolor="#5dade2", edgecolor="#2e86c1", lw=0.4, alpha=0.9, zorder=7)
    main_rivers.plot(ax=ax, color="#2e86c1", lw=0.7, alpha=0.85, zorder=7)

    # 渤海湾水域
    bohai_x, bohai_y = to_alb(119.5, 38.6)
    ax.text(bohai_x, bohai_y, "渤  海\n(Bohai Sea)", ha="center", va="center", fontsize=9.5, fontweight="bold", color="#2980b9",
            style="italic", zorder=8)

    # 主要山脉走向注记（避让水库与高峰）
    ranges = [
        ("太  行  山  脉", 114.25, 37.45, 78),
        ("燕  山  山  脉", 117.65, 40.85, 10),
        ("坝  上  高  原", 115.35, 41.75, 0),
        ("华  北  平  原", 115.95, 37.85, 0)
    ]
    for name, rlon, rlat, rot in ranges:
        rx, ry = to_alb(rlon, rlat)
        ax.text(rx, ry, name, ha="center", va="center", fontsize=9.2, fontweight="bold",
                color="#4a3b32", rotation=rot, zorder=10,
                path_effects=[pe.withStroke(linewidth=2.2, foreground="#ffffff")])

    # 著名山峰与极值注记（严格纠正引线方向，杜绝要素交叉倒置）
    peaks = [
        # 小五台山位于北京西侧蔚县，引线向西北外延至张家口南部山区空白处
        ("小五台山 (东台 2882m·河北最高峰)", 115.035, 39.995, -75, 45, "right"),
        # 塞罕坝位于承德最北端
        ("塞罕坝 (1650m)", 117.255, 42.415, 35, 20, "left"),
        # 雾灵山位于密云/兴隆交界，引线向东北外展至承德南部空白区
        ("雾灵山 (2118m)", 117.485, 40.605, 55, 35, "left"),
        # 驼梁位于石家庄平山西部边界，引线向西
        ("驼梁 (2281m)", 113.821, 38.742, -50, 15, "right"),
        # 白石山位于保定涞源，引线向西南
        ("白石山 (2096m)", 114.685, 39.335, -50, -20, "right"),
        # 祖山位于秦皇岛青龙，引线向东北
        ("祖山 (1428m)", 119.545, 40.165, 45, 25, "left"),
        # 碣石山位于昌黎，引线向东南
        ("碣石山 (695m)", 119.185, 39.735, 35, -20, "left")
    ]
    for pname, plon, plat, ox, oy, ha in peaks:
        px, py = to_alb(plon, plat)
        ax.plot(px, py, "^", color="#b03a2e", markersize=6.0, zorder=11)
        ax.annotate(pname, xy=(px, py), xytext=(ox, oy), textcoords="offset points",
                    fontsize=6.8, fontweight="bold", color="#900c3f", ha=ha, va="center", zorder=12,
                    path_effects=[pe.withStroke(linewidth=2.0, foreground="#ffffff")],
                    arrowprops=dict(arrowstyle="->", color="#900c3f", lw=0.6))

    # 关键水体注记（与山脉山峰文字错开）
    waters = [
        ("白洋淀", 115.985, 38.885, "center", "center"),
        ("衡水湖", 115.605, 37.605, "center", "center"),
        ("潘家口水库", 118.285, 40.355, "left", "center"),
        ("官厅水库", 115.715, 40.365, "right", "center"),
        ("岗南水库", 114.015, 38.315, "right", "bottom"),
        ("岳城水库", 114.225, 36.335, "left", "center"),
        ("滦河干流", 118.255, 40.655, "left", "center"),
        ("滏阳河", 115.255, 37.255, "center", "center"),
        ("大清河", 116.355, 39.015, "left", "center")
    ]
    for wname, wlon, wlat, wha, wva in waters:
        wx, wy = to_alb(wlon, wlat)
        ax.text(wx, wy, wname, ha=wha, va=wva, fontsize=7.0, color="#1b4f72",
                style="italic", zorder=11, path_effects=[pe.withStroke(linewidth=1.8, foreground="#ffffff")])

    # 标题与排版
    ax.set_title("河北省地形地貌与海陆地势格局图", fontsize=13.0, fontweight="bold", color=C_TEXT, pad=18)
    ax.text(0.5, 1.015, "Topography, Geomorphology and Land-Sea Relief of Hebei Province",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=8.2, color="#555555")

    # 罗盘与比例尺
    add_compass(ax, x=0.94, y=0.92)
    add_scalebar(ax, ax_xlim[0] + (ax_xlim[1] - ax_xlim[0]) * 0.05, ax_ylim[0] + (ax_ylim[1] - ax_ylim[0]) * 0.04, length_km=100)

    # 高程图例
    cax = ax.inset_axes([0.05, 0.12, 0.025, 0.22])
    cb = plt.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap_elev), cax=cax, orientation="vertical")
    cb.set_label("高程 Elevation (m)", fontsize=7.0, color="#2c3e50")
    cb.ax.tick_params(labelsize=6.2, length=2.5)

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")
    out_path = os.path.join(OUT_DIR, "fig03-00-1_河北省地形地貌与海陆地势格局图.png")
    plt.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close()
    print(f"Saved: {out_path}")

# =============================================================================
# 2. fig03-00-2_河北省行政区划与空间骨架图
# =============================================================================
def gen_fig2():
    print("Generating fig03-00-2_河北省行政区划与空间骨架图.png...")
    fig, ax = plt.subplots(figsize=(10.5, 10.5), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    # 柔和底色区划色彩
    city_colors = {
        "石家庄市": "#eaf2f8",
        "唐山市": "#fef9e7",
        "秦皇岛市": "#e8f8f5",
        "邯郸市": "#fdedec",
        "邢台市": "#f5eef8",
        "保定市": "#eafaf1",
        "张家口市": "#fcf3cf",
        "承德市": "#e8f6f3",
        "沧州市": "#ebf5fb",
        "廊坊市": "#fef5e7",
        "衡水市": "#f9ebea"
    }

    for _, row in hb_cities.iterrows():
        cname = row.get("name", "")
        fc = city_colors.get(cname, "#f4f6f7")
        gpd.GeoSeries([row.geometry]).plot(ax=ax, facecolor=fc, edgecolor="#566573", lw=0.8, zorder=4)

    # 雄安新区特殊高亮标注
    gpd.GeoSeries([xiongan_geom]).plot(ax=ax, facecolor="#d4efdf", edgecolor="#1e8449", lw=1.5, ls="-", zorder=6)
    xa_cx, xa_cy = xiongan_geom.centroid.x, xiongan_geom.centroid.y
    ax.plot(xa_cx, xa_cy, "o", color="#1e8449", markersize=6.0, markeredgecolor="white", markeredgewidth=0.8, zorder=12)
    ax.annotate("雄安新区\n(国家级新区)", xy=(xa_cx, xa_cy), xytext=(-35, 25), textcoords="offset points",
                fontsize=7.2, fontweight="bold", color="#145a32", ha="right", va="bottom", zorder=14,
                path_effects=[pe.withStroke(linewidth=2.0, foreground="#ffffff")],
                arrowprops=dict(arrowstyle="->", color="#1e8449", lw=0.8))

    # 辛集市与定州市高亮标注
    gpd.GeoSeries([xinji_geom]).plot(ax=ax, facecolor="#fadbd8", edgecolor="#b03a2e", lw=1.2, zorder=6)
    xj_cx, xj_cy = xinji_geom.centroid.x, xinji_geom.centroid.y
    ax.plot(xj_cx, xj_cy, "s", color="#b03a2e", markersize=4.5, zorder=12)
    ax.annotate("辛集市 (省直管)", xy=(xj_cx, xj_cy), xytext=(0, 26), textcoords="offset points",
                fontsize=6.8, fontweight="bold", color="#78281f", ha="center", va="bottom", zorder=14,
                path_effects=[pe.withStroke(linewidth=1.8, foreground="#ffffff")],
                arrowprops=dict(arrowstyle="->", color="#b03a2e", lw=0.6))

    gpd.GeoSeries([dingzhou_geom]).plot(ax=ax, facecolor="#fdebd0", edgecolor="#b9770e", lw=1.2, zorder=6)
    dz_cx, dz_cy = dingzhou_geom.centroid.x, dingzhou_geom.centroid.y
    ax.plot(dz_cx, dz_cy, "s", color="#b9770e", markersize=4.5, zorder=12)
    ax.annotate("定州市 (省直管)", xy=(dz_cx, dz_cy), xytext=(-30, 25), textcoords="offset points",
                fontsize=6.8, fontweight="bold", color="#7e5109", ha="right", va="bottom", zorder=14,
                path_effects=[pe.withStroke(linewidth=1.8, foreground="#ffffff")],
                arrowprops=dict(arrowstyle="->", color="#b9770e", lw=0.6))

    # 京津参考
    gpd.GeoSeries([bj_union]).plot(ax=ax, facecolor="#e5e8e8", edgecolor="#95a5a6", lw=1.0, ls="--", zorder=5)
    gpd.GeoSeries([tj_union]).plot(ax=ax, facecolor="#e5e8e8", edgecolor="#95a5a6", lw=1.0, ls="--", zorder=5)
    bj_cx, bj_cy = to_alb(116.40, 39.90)
    tj_cx, tj_cy = to_alb(117.20, 39.12)
    ax.text(bj_cx, bj_cy, "北京市", ha="center", va="center", fontsize=8.0, fontweight="bold", color="#555555",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="#ffffff", edgecolor="#bdc3c7", alpha=0.85), zorder=12)
    ax.text(tj_cx, tj_cy, "天津市", ha="center", va="center", fontsize=8.0, fontweight="bold", color="#555555",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="#ffffff", edgecolor="#bdc3c7", alpha=0.85), zorder=12)

    # 11个地级市行政中心（采用市政府权威驻地坐标，标签偏移杜绝遮挡符号与行政边界）
    city_label_offsets = {
        "石家庄市": (-28, -18, "right"),
        "唐山市": (18, 16, "left"),
        "秦皇岛市": (18, 14, "left"),
        "邯郸市": (-20, 0, "right"),
        "邢台市": (-20, 0, "right"),
        "保定市": (-28, 18, "right"),
        "张家口市": (20, 16, "left"),
        "承德市": (20, 16, "left"),
        "沧州市": (22, 16, "left"),
        "廊坊市": (18, -18, "left"), # 廊坊往东南偏移避让北京与边界
        "衡水市": (20, -10, "left")
    }

    for cname, (clon, clat) in CITY_GOV_COORDS.items():
        cx_pt, cy_pt = to_alb(clon, clat)
        is_prov_cap = (cname == "石家庄市")
        marker = "s" if is_prov_cap else "o"
        mcolor = "#c0392b" if is_prov_cap else "#2980b9"
        msize = 7.5 if is_prov_cap else 5.2
        label_text = f"★ {cname}\n(省会)" if is_prov_cap else cname

        ax.plot(cx_pt, cy_pt, marker, color=mcolor, markersize=msize, markeredgecolor="white", markeredgewidth=0.8, zorder=12)
        ox, oy, ha = city_label_offsets.get(cname, (18, 15, "left"))
        ax.annotate(label_text, xy=(cx_pt, cy_pt), xytext=(ox, oy), textcoords="offset points",
                    ha=ha, va="center", fontsize=7.6 if not is_prov_cap else 8.2,
                    fontweight="bold", color="#78281f" if is_prov_cap else "#1a252f", zorder=13,
                    path_effects=[pe.withStroke(linewidth=2.2, foreground="#ffffff")],
                    arrowprops=dict(arrowstyle="-", color="#7f8c8d", lw=0.5))

    # 边界加粗
    gpd.GeoSeries([hb_union]).boundary.plot(ax=ax, color="#1a252f", lw=1.4, zorder=7)

    # 标题与排版
    ax.set_title("河北省行政区划与空间骨架图", fontsize=13.0, fontweight="bold", color=C_TEXT, pad=18)
    ax.text(0.5, 1.015, "Administrative Divisions and Spatial Framework of Hebei Province",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=8.2, color="#555555")

    # 罗盘与比例尺
    add_compass(ax, x=0.94, y=0.92)
    add_scalebar(ax, ax_xlim[0] + (ax_xlim[1] - ax_xlim[0]) * 0.05, ax_ylim[0] + (ax_ylim[1] - ax_ylim[0]) * 0.04, length_km=100)

    # 图例
    legend_elements = [
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#c0392b", markeredgecolor="w", markersize=8, label="省会极核 (石家庄市)"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#2980b9", markeredgecolor="w", markersize=6.5, label="地级市行政中心 (10市)"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#1e8449", markeredgecolor="w", markersize=7, label="雄安新区 (国家级新区)"),
        Patch(facecolor="#fadbd8", edgecolor="#b03a2e", label="辛集市 (省直管县级市)"),
        Patch(facecolor="#fdebd0", edgecolor="#b9770e", label="定州市 (省直管县级市)"),
        Patch(facecolor="#e5e8e8", edgecolor="#95a5a6", linestyle="--", label="京津邻接直辖市")
    ]
    leg = ax.legend(handles=legend_elements, loc="lower right", fontsize=7.0, framealpha=0.92,
                    title="区划要素图例", title_fontsize=7.6)
    leg.set_zorder(20)

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")
    out_path = os.path.join(OUT_DIR, "fig03-00-2_河北省行政区划与空间骨架图.png")
    plt.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close()
    print(f"Saved: {out_path}")

# =============================================================================
# 3. fig03-00-3_河北省综合立体交通网与海陆空枢纽图
# =============================================================================
def gen_fig3():
    print("Generating fig03-00-3_河北省综合立体交通网与海陆空枢纽图.png...")
    fig, ax = plt.subplots(figsize=(10.5, 10.5), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    # 底图
    hb_cities.plot(ax=ax, facecolor="#f8f9fa", edgecolor="#bdc3c7", lw=0.6, zorder=3)
    bj_all.plot(ax=ax, facecolor="#f2f3f4", edgecolor="#bdc3c7", lw=0.5, zorder=3)
    tj_all.plot(ax=ax, facecolor="#f2f3f4", edgecolor="#bdc3c7", lw=0.5, zorder=3)
    gpd.GeoSeries([hb_union]).boundary.plot(ax=ax, color="#2c3e50", lw=1.2, zorder=4)

    # 叠置高速公路与干线
    motorways.plot(ax=ax, color="#f39c12", lw=0.8, alpha=0.85, zorder=5)

    # 叠置铁路网络
    main_rails.plot(ax=ax, color="#2c3e50", lw=1.0, ls="-", zorder=6)

    # 图面零文字：全部枢纽与廊道只画「符号 + 编号」，名称与含义进图外图例。
    # 旧版是逐个 annotate(offset points) 手调偏移——秦皇岛一带港口、机场、
    # 高铁三种要素挤在 20 km 内（图上不足 40 px），手调偏移必叠。
    sl = mapkit.SymbolLabels(ax, fig)
    sl.reserve([(0.80, 0.0, 1.0, 0.10),     # 比例尺
                (0.88, 0.86, 1.0, 1.0)])    # 指北针

    hsr_corridors = [
        ("京广高速铁路", 114.85, 38.65),
        ("京沪高速铁路", 116.85, 37.95),
        ("京哈高速铁路", 117.75, 40.75),
        ("京张城际铁路", 115.35, 40.45),
        ("京雄城际铁路", 116.12, 39.25),
        ("津秦高速铁路", 119.25, 39.85),
        ("石济客专", 115.45, 37.85),
        ("大秦重载运煤铁路", 118.25, 40.35),
        ("朔黄重载运煤铁路", 115.80, 38.45),
    ]
    for cname, clon, clat in hsr_corridors:
        cx_c, cy_c = to_alb(clon, clat)
        sl.add(cx_c, cy_c, cname, "corridor")

    ports = [
        ("唐山港·曹妃甸港区", 118.915, 39.025, "世界级大宗散货港"),
        ("唐山港·京唐港区", 119.015, 39.215, ""),
        ("黄骅港", 117.875, 38.325, "北方综合大港 · 煤炭枢纽"),
        ("秦皇岛港", 119.635, 39.915, "世界能源输出大港"),
    ]
    for pname, plon, plat, pnote in ports:
        px, py = to_alb(plon, plat)
        nm, nt = mapkit.split_note(pname)
        sl.add(px, py, nm, "port", note=pnote or nt)

    airports = [
        ("石家庄正定国际机场", 114.695, 38.281, "4E 级"),
        ("北京大兴国际机场", 116.415, 39.515, "跨京冀"),
        ("秦皇岛北戴河机场", 119.065, 39.665, ""),
        ("张家口宁远机场", 114.935, 40.745, ""),
        ("承德普宁机场", 118.075, 41.125, ""),
        ("邯郸机场", 114.425, 36.525, ""),
        ("唐山三女河机场", 118.005, 39.715, ""),
        ("邢台褡裢机场", 114.425, 36.885, ""),
    ]
    for aname, alon, alat, anote in airports:
        ax_pt, ay_pt = to_alb(alon, alat)
        nm, nt = mapkit.split_note(aname)
        sl.add(ax_pt, ay_pt, nm, "airport", note=anote or nt)

    dryports = [
        ("雄安高铁站枢纽", 116.145, 39.065, ""),
        ("石家庄国际陆港", 114.605, 37.608, "中欧班列"),
    ]
    for dname, dlon, dlat, dnote in dryports:
        dx_pt, dy_pt = to_alb(dlon, dlat)
        nm, nt = mapkit.split_note(dname)
        sl.add(dx_pt, dy_pt, nm, "dryport", note=dnote or nt)
    sym_type_h, sym_idx_h = sl.flush()

    # 标题与排版
    # pad 必须给足：原来 pad=18 时中文标题底边约在 1.02，英文副标题
    # （y=1.015、va=bottom）正好顶上来，两个标题直接叠字。
    ax.set_title("河北省综合立体交通网与海陆空枢纽格局图", fontsize=13.0,
                 fontweight="bold", color=C_TEXT, pad=32)
    ax.text(0.5, 1.004, "Integrated Multi-Modal Transport Network & Sea-Land-Air Hubs of Hebei",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=8.2, color="#555555")

    # 罗盘与比例尺
    add_compass(ax, x=0.94, y=0.92)
    add_scalebar(ax, ax_xlim[0] + (ax_xlim[1] - ax_xlim[0]) * 0.05, ax_ylim[0] + (ax_ylim[1] - ax_ylim[0]) * 0.04, length_km=100)

    # 图例
    legend_elements = [
        Line2D([0], [0], color="#2c3e50", lw=1.5, label="普速与重载运煤铁路 (大秦/朔黄)"),
        Line2D([0], [0], color="#78281f", lw=1.5, ls="--", label="高速铁路与城际客专 (京广/京沪/京张等)"),
        Line2D([0], [0], color="#f39c12", lw=1.2, label="国家高速公路 (G4/G1/G2/G95等)"),
        Line2D([0], [0], marker="h", color="w", markerfacecolor="#1f618d", markersize=7.5, label="环渤海核心港区 (唐山/黄骅/秦皇岛)"),
        Line2D([0], [0], marker="P", color="w", markerfacecolor="#922b21", markersize=7.0, label="民用运输航空机场 (正定/大兴等)"),
        Line2D([0], [0], marker="D", color="w", markerfacecolor="#1e8449", markersize=6.5, label="国家级陆港与综合交通枢纽")
    ]
    leg = mapkit.stacked_legends(ax, [
        dict(handles=legend_elements + sym_type_h, title="线型与符号含义",
             ncol=3, fontsize=6.8, title_fontsize=7.6),
        dict(handles=sym_idx_h, title="图上编号对照（编号标注于符号旁）",
             ncol=3, fontsize=6.8, title_fontsize=7.6),
    ], top=-0.008, gap=0.012)
    mapkit.footer_below_legend(
        ax, leg, "数据源：OpenStreetMap · 中国国家铁路集团 · 交通运输部 · 制作：《中国地理知识手册》",
        fontsize=6.8)

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")
    out_path = os.path.join(OUT_DIR, "fig03-00-3_河北省综合立体交通网与海陆空枢纽图.png")
    plt.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close()
    print(f"Saved: {out_path}")

# =============================================================================
# 4. fig03-00-4_河北省产业经济与先进制造业带分布图
# =============================================================================
def gen_fig4():
    print("Generating fig03-00-4_河北省产业经济与先进制造业带分布图.png...")
    fig, ax = plt.subplots(figsize=(10.5, 10.5), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    # 11市 GDP 色彩填色（以 2024 年 GDP 为阶梯梯度）
    gdp_data = {
        "唐山市": 9580.0,
        "石家庄市": 7924.8,
        "邯郸市": 4710.0,
        "沧州市": 4504.6,
        "保定市": 4252.8,
        "廊坊市": 3712.5,
        "邢台市": 3108.4,
        "秦皇岛市": 2043.2,
        "张家口市": 1918.5,
        "衡水市": 1902.6,
        "承德市": 1865.2
    }
    norm_gdp = Normalize(vmin=1500, vmax=10000)
    cmap_gdp = plt.cm.YlOrRd

    for _, row in hb_cities.iterrows():
        cname = row.get("name", "")
        val = gdp_data.get(cname, 2000.0)
        color = cmap_gdp(norm_gdp(val))
        gpd.GeoSeries([row.geometry]).plot(ax=ax, facecolor=color, edgecolor="#5d6d7e", lw=0.8, alpha=0.85, zorder=4)

    # 京津
    gpd.GeoSeries([bj_union]).plot(ax=ax, facecolor="#eaeded", edgecolor="#95a5a6", lw=1.0, ls="--", zorder=5)
    gpd.GeoSeries([tj_union]).plot(ax=ax, facecolor="#eaeded", edgecolor="#95a5a6", lw=1.0, ls="--", zorder=5)

    # 绘制四大产业空间带骨架
    # 1. 沿海重化工与大港经济带
    coast_pts = [to_alb(119.6, 39.9), to_alb(119.0, 39.2), to_alb(118.9, 39.0), to_alb(117.8, 38.3)]
    cx_arr = [p[0] for p in coast_pts]
    cy_arr = [p[1] for p in coast_pts]
    ax.plot(cx_arr, cy_arr, color="#1a5276", lw=4.5, alpha=0.6, ls="-", zorder=8)
    ax.text(cx_arr[1] + 25000, cy_arr[1] - 25000, "环渤海沿海重化与大港经济带\n(精品钢铁·现代石化·海洋经济)",
            fontsize=7.6, fontweight="bold", color="#154360", zorder=15,
            path_effects=[pe.withStroke(linewidth=2.0, foreground="#ffffff")])

    # 2. 京广与太行山前先进制造与物流走廊（文字移向走廊东侧冲积平原腹地，彻底避开色带与石家庄GDP）
    taihang_pts = [to_alb(115.5, 38.9), to_alb(114.5, 38.0), to_alb(114.5, 37.1), to_alb(114.5, 36.6)]
    tx_arr = [p[0] for p in taihang_pts]
    ty_arr = [p[1] for p in taihang_pts]
    ax.plot(tx_arr, ty_arr, color="#b9770e", lw=4.5, alpha=0.6, ls="-", zorder=8)
    ax.text(tx_arr[2] + 12000, ty_arr[2] - 18000, "太行山前先进智造与现代商贸物流带\n(生物医药·新能源汽车·装备制造)",
            ha="left", va="center", fontsize=7.4, fontweight="bold", color="#7e5109", zorder=15,
            path_effects=[pe.withStroke(linewidth=2.0, foreground="#ffffff")])

    # 3. 冀北绿色生态与清洁能源/冬奥文旅带
    north_pts = [to_alb(114.8, 41.2), to_alb(115.4, 40.9), to_alb(117.2, 42.4), to_alb(118.0, 41.0)]
    nx_arr = [p[0] for p in north_pts]
    ny_arr = [p[1] for p in north_pts]
    ax.plot(nx_arr, ny_arr, color="#1e8449", lw=4.5, alpha=0.6, ls=":", zorder=8)
    ax.text(nx_arr[0], ny_arr[0] + 18000, "冀北绿色能源与冬奥体育文旅带\n(风光储氢·冰雪运动·生态康养)",
            fontsize=7.6, fontweight="bold", color="#145a32", zorder=15,
            path_effects=[pe.withStroke(linewidth=2.0, foreground="#ffffff")])

    # 4. 雄安—廊坊协同创新与临空经济区（文字上移，避免覆盖廊坊 GDP）
    xa_pt = to_alb(115.95, 39.02)
    lf_pt = to_alb(116.50, 39.52)
    ax.plot([xa_pt[0], lf_pt[0]], [xa_pt[1], lf_pt[1]], color="#7d3c98", lw=3.8, alpha=0.7, ls="-.", zorder=8)
    ax.text((xa_pt[0] + lf_pt[0]) / 2 + 10000, (xa_pt[1] + lf_pt[1]) / 2 + 18000, "雄安新区协同创新与临空经济区\n(央企总部·空天信息·数字经济)",
            fontsize=7.4, fontweight="bold", color="#5b2c6f", zorder=15,
            path_effects=[pe.withStroke(linewidth=2.0, foreground="#ffffff")])

    # 标注各市 2024 GDP 气泡数值（精细坐标偏移，确保清晰无遮挡）
    city_gdp_offsets = {
        "廊坊市": (116.70, 39.22), # 廊坊下部清晰位置，杜绝与雄安走廊文字混淆
        "保定市": (115.55, 38.80),
        "石家庄市": (114.28, 38.00),
        "唐山市": (118.25, 39.65),
        "秦皇岛市": (119.50, 39.95),
        "邯郸市": (114.50, 36.55),
        "邢台市": (114.60, 37.10),
        "张家口市": (114.90, 40.80),
        "承德市": (117.95, 40.95),
        "沧州市": (116.85, 38.25),
        "衡水市": (115.70, 37.75)
    }

    for cname, (glon, glat) in city_gdp_offsets.items():
        gx, gy = to_alb(glon, glat)
        val = gdp_data.get(cname, 2000.0)
        ax.text(gx, gy, f"{cname}\n{val:.1f} 亿元", ha="center", va="center",
                fontsize=7.0, fontweight="bold", color="#1a252f", zorder=13,
                path_effects=[pe.withStroke(linewidth=2.0, foreground="#ffffff")])

    gpd.GeoSeries([hb_union]).boundary.plot(ax=ax, color="#1a252f", lw=1.2, zorder=7)

    # 标题与排版
    ax.set_title("河北省产业经济与先进制造业带分布图", fontsize=13.0, fontweight="bold", color=C_TEXT, pad=18)
    ax.text(0.5, 1.015, "Industrial Economy and Advanced Manufacturing Belts in Hebei Province",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=8.2, color="#555555")

    # 罗盘与比例尺
    add_compass(ax, x=0.94, y=0.92)
    add_scalebar(ax, ax_xlim[0] + (ax_xlim[1] - ax_xlim[0]) * 0.05, ax_ylim[0] + (ax_ylim[1] - ax_ylim[0]) * 0.04, length_km=100)

    # GDP 色带图例
    cax = ax.inset_axes([0.05, 0.12, 0.025, 0.22])
    cb = plt.colorbar(plt.cm.ScalarMappable(norm=norm_gdp, cmap=cmap_gdp), cax=cax, orientation="vertical")
    cb.set_label("2024 年 GDP (亿元)", fontsize=7.0, color="#2c3e50")
    cb.ax.tick_params(labelsize=6.2, length=2.5)

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")
    out_path = os.path.join(OUT_DIR, "fig03-00-4_河北省产业经济与先进制造业带分布图.png")
    plt.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close()
    print(f"Saved: {out_path}")

# =============================================================================
# 5. fig03-00-5_河北省生态安全屏障与自然水系格局图
# =============================================================================
def gen_fig5():
    print("Generating fig03-00-5_河北省生态安全屏障与自然水系格局图.png...")
    fig, ax = plt.subplots(figsize=(10.5, 10.5), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    # 底色与地形素描
    hb_cities.plot(ax=ax, facecolor="#f4f6f7", edgecolor="#bdc3c7", lw=0.6, zorder=3)
    bj_all.plot(ax=ax, facecolor="#eaeded", edgecolor="#bdc3c7", lw=0.5, zorder=3)
    tj_all.plot(ax=ax, facecolor="#eaeded", edgecolor="#bdc3c7", lw=0.5, zorder=3)
    gpd.GeoSeries([hb_union]).boundary.plot(ax=ax, color="#2c3e50", lw=1.2, zorder=4)

    # 绘制全要素河流与湖泊湿地（已裁切至省界）
    main_rivers.plot(ax=ax, color="#2980b9", lw=0.8, alpha=0.9, zorder=6)
    main_lakes.plot(ax=ax, facecolor="#85c1e9", edgecolor="#2980b9", lw=0.5, zorder=7)

    # 太行山与燕山生态安全屏障圈（精准错开水源水库位置）
    ranges = [
        ("太行山森林生态屏障区\n(水源涵养·水土保持·生物多样性)", 114.05, 37.35), # 往南移至邢台/邯郸段山区，避开石家庄水库
        ("燕山山地水源涵养屏障区\n(密云/官厅/潘家口水源保障)", 117.65, 41.15), # 往北移至承德腹地，避开潘家口水库
        ("坝上防风固沙与草原生态屏障区\n(阻挡京津风沙前沿屏障)", 115.35, 41.75)
    ]
    for rname, rlon, rlat in ranges:
        rx, ry = to_alb(rlon, rlat)
        ax.text(rx, ry, rname, ha="center", va="center", fontsize=7.8, fontweight="bold",
                color="#196f3d", zorder=12,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#e8f8f5", edgecolor="#27ae60", alpha=0.9),
                path_effects=[pe.withStroke(linewidth=1.8, foreground="#ffffff")])

    # 关键生态极核（引线径向错开）
    eco_nuclei = [
        ("白洋淀“华北明珠”\n(全域水质III类·大清河水系极核)", 115.985, 38.885, 35, 20, "left"),
        ("衡水湖国家级湿地\n(东亚候鸟迁徙关键停歇地)", 115.605, 37.605, 35, -20, "left"),
        ("塞罕坝百万亩林海\n(联合国地球卫士奖·荒原变林海)", 117.255, 42.415, 30, -15, "left"),
        ("官厅水库湿地\n(首都西南生态绿肺)", 115.715, 40.365, -45, 15, "right"),
        ("潘家口水库引滦入津入唐水源地", 118.285, 40.405, 35, 15, "left"),
        ("岗南与黄壁庄水库 (省会水源地)", 114.155, 38.275, -45, 18, "right"),
        ("渤海湾海陆生态交错湿地带", 118.850, 39.150, 25, -25, "left")
    ]
    for ename, elon, elat, ox, oy, ha in eco_nuclei:
        ex, ey = to_alb(elon, elat)
        ax.plot(ex, ey, "p", color="#117864", markersize=7.0, markeredgecolor="white", markeredgewidth=0.7, zorder=14)
        ax.annotate(ename, xy=(ex, ey), xytext=(ox, oy), textcoords="offset points",
                    fontsize=7.0, fontweight="bold", color="#0e6251", ha=ha, va="center", zorder=15,
                    path_effects=[pe.withStroke(linewidth=2.0, foreground="#ffffff")],
                    arrowprops=dict(arrowstyle="->", color="#117864", lw=0.6))

    # 标题与排版
    ax.set_title("河北省生态安全屏障与自然水系格局图", fontsize=13.0, fontweight="bold", color=C_TEXT, pad=18)
    ax.text(0.5, 1.015, "Ecological Security Barriers and Hydrological Patterns of Hebei",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=8.2, color="#555555")

    # 罗盘与比例尺
    add_compass(ax, x=0.94, y=0.92)
    add_scalebar(ax, ax_xlim[0] + (ax_xlim[1] - ax_xlim[0]) * 0.05, ax_ylim[0] + (ax_ylim[1] - ax_ylim[0]) * 0.04, length_km=100)

    # 图例
    legend_elements = [
        Line2D([0], [0], color="#2980b9", lw=1.2, label="骨干河流水系 (滦河/大清河/子牙河等)"),
        Patch(facecolor="#85c1e9", edgecolor="#2980b9", label="湖泊水库水体 (白洋淀/衡水湖/水库)"),
        Patch(facecolor="#e8f8f5", edgecolor="#27ae60", label="太行山/燕山/坝上三大生态屏障区"),
        Line2D([0], [0], marker="p", color="w", markerfacecolor="#117864", markersize=7.5, label="国家级生态水质保护与水源极核")
    ]
    leg = ax.legend(handles=legend_elements, loc="lower right", fontsize=7.0, framealpha=0.92,
                    title="生态水系图例", title_fontsize=7.6)
    leg.set_zorder(20)

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.axis("off")
    out_path = os.path.join(OUT_DIR, "fig03-00-5_河北省生态安全屏障与自然水系格局图.png")
    plt.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close()
    print(f"Saved: {out_path}")

if __name__ == "__main__":
    gen_fig1()
    gen_fig2()
    gen_fig3()
    gen_fig4()
    gen_fig5()
    print("All 5 overview maps for Hebei completed successfully!")
