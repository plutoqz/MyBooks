# -*- coding: utf-8 -*-
"""第 4 章 气候 —— 专题图。

等值线依据通行地理教材口径（示意勾绘于 AWS Terrain 底图）；
城市气候图数据取 Open-Meteo Archive（ERA5 再分析，2004—2023 平均）；
台风数据取 NOAA IBTrACS v04r01。

fig4-3 1月平均气温等值线   fig4-7 干湿区与季风区界线
fig4-4 7月平均气温等值线   fig4-5 温度带划分（示意）
fig4-6 年降水量等值线      fig4-1 六城气候图（climograph）
                           fig4-8 影响中国的台风路径（IBTrACS）
"""
import json
import os
import sys
from urllib.request import urlopen

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from pyproj import Transformer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import (ALBERS, C_SEA, C_TEXT, DATA, DPI, FIGURES, add_title,
                   new_map_axes, save_fig, set_extent_from, setup)
from geo_features import CITIES, PLATEAUS
from ch03_terrain import RES_A, hillshade, load_cache

IBTRACS = os.path.join(DATA, "climatology", "ibtracs")
_T = Transformer.from_crs("EPSG:4326", ALBERS, always_xy=True)


def to_albers(lon, lat):
    return _T.transform(lon, lat)


MONSOON_LINE = [(121.5, 53.2), (120.0, 47.5), (116.0, 43.5), (111.0, 41.0),
                (107.5, 40.8), (106.0, 39.2), (105.9, 37.8), (103.5, 36.2),
                (99.5, 34.5), (96.0, 34.3), (91.5, 33.2), (86.0, 31.2),
                (82.5, 30.2)]
PREC400 = [(121.5, 53.2), (118.0, 46.0), (114.0, 42.0), (111.0, 40.5),
           (107.5, 40.8), (106.0, 39.2), (104.5, 37.0), (103.8, 36.0),
           (101.0, 35.2), (97.0, 33.5), (93.0, 31.0), (91.0, 29.7), (93.5, 28.8), (95.5, 28.4)]
PREC200 = [(116.5, 47.0), (112.0, 43.0), (108.0, 41.0), (105.5, 39.0),
           (103.0, 38.2), (98.0, 37.0), (92.0, 36.0), (88.0, 34.0)]
PREC800 = [(101.0, 31.0), (104.5, 32.8), (107.0, 33.8), (110.0, 33.9),
           (113.0, 34.2), (116.0, 34.4), (118.5, 34.5), (120.5, 34.2)]
PREC1600 = [(121.0, 28.5), (117.5, 26.3), (114.5, 25.3), (111.5, 25.5),
            (108.5, 24.8), (105.0, 24.0), (102.5, 23.5)]
T1_M28 = [(122.5, 53.3), (124.5, 52.5), (122.0, 51.4), (120.3, 52.3)]
T1_M16 = [(119.0, 46.5), (124.0, 45.5), (129.0, 44.0), (133.0, 45.5),
          (130.0, 47.5), (124.0, 48.5)]
T1_M8 = [(124.5, 40.8), (120.0, 41.0), (116.5, 41.3), (112.5, 40.2),
         (108.5, 39.3), (105.5, 38.6), (102.0, 38.2)]
T1_0 = PREC800[1:]
T1_8 = [(121.0, 28.3), (116.5, 25.5), (112.0, 25.0), (108.0, 24.3)]
T1_16S = [(109.8, 21.4), (113.5, 21.6)]
T1_16T = [(120.2, 22.6), (121.0, 22.0)]
T7_16 = [(86.0, 36.5), (92.0, 35.5), (97.0, 33.5), (99.0, 31.0), (97.0, 28.5),
         (93.0, 28.2), (88.0, 28.6), (82.0, 30.5), (80.0, 33.0)]
T7_24 = [(126.0, 49.5), (124.0, 47.0), (121.0, 44.5), (118.0, 42.5),
         (115.0, 41.5), (112.0, 40.5), (106.0, 40.0), (101.0, 40.2)]
T7_28 = [(121.0, 33.0), (117.0, 33.5), (114.0, 33.0), (111.0, 32.0),
         (106.0, 31.5), (104.0, 30.5)]


def _map_frame(figsize=(10.5, 10.8)):
    fig, ax = new_map_axes(figsize)
    ax.set_facecolor(C_SEA)
    dem, minx, maxy = load_cache()
    h, w = dem.shape
    extent = (minx, minx + w * RES_A, maxy - h * RES_A, maxy)
    sh = hillshade(dem)
    rgba = np.zeros((h, w, 4))
    f = 0.55 + 0.45 * sh
    rgba[:, :, 0], rgba[:, :, 1], rgba[:, :, 2] = 0.93 * f, 0.91 * f, 0.87 * f
    rgba[:, :, 3] = np.where(np.isnan(dem), 0.0, 1.0)
    ax.imshow(rgba, extent=extent, origin="upper", interpolation="bilinear",
              zorder=1)
    return fig, ax


def _borders(ax, z=3):
    gdf = gpd.read_file(os.path.join(DATA, "boundaries", "datav",
                                     "100000_full.json"))
    prov = gdf[gdf["name"].notna() & (gdf["name"].str.len() > 0)].to_crs(ALBERS)
    dash = gdf[gdf["name"].isna() | (gdf["name"].str.len() == 0)].to_crs(ALBERS)
    prov.boundary.plot(ax=ax, color="#6a6a6a", linewidth=0.28, alpha=0.55, zorder=z)
    if len(dash):
        dash.plot(ax=ax, facecolor="none", edgecolor="#3b5872", linewidth=0.7,
                  ls="--", zorder=z + 1)
    return gdf, prov, dash


def _iso(ax, pts, color, label, label_at, rot=0, lw=1.7, ls="-"):
    xs, ys = zip(*[to_albers(lo, la) for lo, la in pts])
    ax.plot(xs, ys, color=color, lw=lw, ls=ls, zorder=6)
    if label:
        x, y = to_albers(*label_at)
        ax.text(x, y, label, fontsize=8.6, color=color, rotation=rot,
                ha="center", va="center", zorder=8,
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none",
                          alpha=0.85))


def _zone_label(ax, lon, lat, text, fs=9, color="#2c3e50"):
    x, y = to_albers(lon, lat)
    ax.text(x, y, text, fontsize=fs, color=color, ha="center", va="center",
            zorder=8, linespacing=1.5,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#999999",
                      alpha=0.88))


def _finish(fig, ax, title, subtitle, fname, footer):
    _borders(ax)
    set_extent_from(ax, gpd.read_file(os.path.join(
        DATA, "boundaries", "datav", "100000_full.json")).to_crs(ALBERS))
    add_title(ax, title, subtitle)
    save_fig(fig, ax, fname, footer=footer)


FOOT_BETA = ("等值线为通行地理教材口径的示意勾绘，底图：AWS Terrain Tiles；投影：Albers 等积圆锥\n"
             "示意地图，不作为权属划界依据")


def fig4_1_t_jan():
    fig, ax = _map_frame()
    _iso(ax, T1_M28, "#08306b", "−28 ℃", (122.2, 53.7))
    _iso(ax, T1_M16, "#2166ac", "−16 ℃", (129.5, 43.4), rot=10)
    _iso(ax, T1_M8, "#67a9cf", "−8 ℃", (110.0, 40.0), rot=3)
    _iso(ax, T1_0, "#c0392b", "0 ℃（秦岭—淮河）", (112.6, 34.8), lw=2.2)
    _iso(ax, T1_8, "#ef8a62", "8 ℃", (117.0, 26.0), rot=-25)
    _iso(ax, T1_16S, "#b2182b", "16 ℃", (111.6, 22.0), rot=3)
    _iso(ax, T1_16T, "#b2182b", "16 ℃", (121.2, 21.5), rot=-45)
    _finish(fig, ax, "1 月平均气温（等值线示意）",
            "0 ℃ 等温线大致沿秦岭—淮河一线，是南与北的分界",
            "fig4-3_1月平均气温.png", FOOT_BETA)


def fig4_2_t_jul():
    fig, ax = _map_frame()
    _iso(ax, T7_16, "#2166ac", "16 ℃", (90.0, 30.0), rot=-45)
    _iso(ax, T7_24, "#e08a3c", "24 ℃", (117.0, 42.2), rot=25)
    _iso(ax, T7_28, "#d7301f", "28 ℃", (110.0, 31.5), rot=3)
    _zone_label(ax, 89.0, 43.4, "吐鲁番盆地：7 月均温 >32 ℃，全国最热", fs=8.5)
    _zone_label(ax, 86.5, 31.5, "青藏高原是全国夏季最凉的地区", fs=8.5)
    _finish(fig, ax, "7 月平均气温（等值线示意）",
            "除青藏高原外全国普遍高温——夏季风的馈赠",
            "fig4-4_7月平均气温.png", FOOT_BETA)


def fig4_3_prec():
    fig, ax = _map_frame()
    _iso(ax, PREC1600, "#01665e", "1 600 mm", (118.8, 27.0), rot=-25)
    _iso(ax, PREC800, "#35978f", "800 mm", (112.6, 34.8), lw=2.2)
    _iso(ax, PREC400, "#bf812d", "400 mm", (106.2, 39.0), lw=2.2)
    _iso(ax, PREC200, "#b35a1f", "200 mm", (114.8, 45.4), rot=25)
    _finish(fig, ax, "年降水量（等值线示意）",
            "自东南沿海向西北内陆递减；800 与 400 mm 线是南北方向与农牧业的重要界线",
            "fig4-6_年降水量.png", FOOT_BETA)


def fig4_4_zones():
    fig, ax = _map_frame()
    _iso(ax, PREC200, "#b35a1f", "200 mm", (110.5, 40.0), rot=3)
    _iso(ax, PREC400, "#8a6d1d", "400 mm", (106.2, 39.0), lw=2.0)
    _iso(ax, PREC800, "#1d6b3c", "800 mm", (112.6, 34.8), lw=2.0)
    _zone_label(ax, 84.0, 41.0, "干旱区\n（<200 mm）", color="#8a4a10")
    _zone_label(ax, 111.5, 42.3, "半干旱区\n（200—400 mm）", color="#6d5a10")
    _zone_label(ax, 113.8, 35.9, "半湿润区\n（400—800 mm）", color="#1d5a30")
    _zone_label(ax, 110.5, 24.6, "湿润区\n（>800 mm）", color="#1d5a30")
    xs, ys = zip(*[to_albers(lo, la) for lo, la in MONSOON_LINE])
    ax.plot(xs, ys, color="#1d6b3c", lw=2.0, ls=(0, (7, 4)), zorder=7)
    ax.text(*to_albers(118.2, 45.8), "季风区与非季风区分界", fontsize=8.5,
            color="#1d6b3c", rotation=-30, ha="center", zorder=8,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85))
    _finish(fig, ax, "干湿地区划分（示意）",
            "按年降水量阈值划分四区；绿色虚线为季风区与非季风区界线",
            "fig4-7_干湿区划分.png", FOOT_BETA)


def fig4_5_belts():
    fig, ax = _map_frame()
    _iso(ax, T1_M28, "#4a5fa5", "寒温带南界（−28 ℃）", (121.8, 50.4), lw=1.4)
    _iso(ax, T1_M8, "#6fa8dc", "中温带南界（≈1 月 −8 ℃）", (110.0, 40.0), lw=1.6)
    _iso(ax, T1_0, "#c0392b", "暖温带南界（秦岭—淮河）", (112.6, 34.8), lw=2.0)
    _iso(ax, T1_16S, "#c25b4e", "亚热带南界", (111.6, 21.0), lw=1.4)
    _iso(ax, T1_16T, "#c25b4e", None, None, lw=1.4)
    xs, ys = zip(*[to_albers(lo, la) for lo, la in PLATEAUS["青藏高原"]])
    ax.plot(list(xs) + [xs[0]], list(ys) + [ys[0]], color="#8e7cc3", lw=2.0,
            ls="--", zorder=6)
    _zone_label(ax, 123.6, 52.1, "寒温带")
    _zone_label(ax, 124.5, 43.4, "中温带")
    _zone_label(ax, 114.5, 36.8, "暖温带")
    _zone_label(ax, 112.0, 26.8, "亚热带")
    _zone_label(ax, 109.8, 20.2, "热带")
    _zone_label(ax, 88.5, 33.0, "青藏高寒区", color="#5b4a9e")
    _finish(fig, ax, "温度带划分（示意）",
            "以 1 月平均气温为主要依据的近似划分；正式区划以 ≥10 ℃ 积温为准",
            "fig4-5_温度带划分.png", FOOT_BETA)


def city_series(city):
    lo, la = CITIES[city]
    url = ("https://archive-api.open-meteo.com/v1/archive"
           f"?latitude={la}&longitude={lo}"
           "&start_date=2004-01-01&end_date=2023-12-31"
           "&daily=temperature_2m_mean,precipitation_sum&timezone=auto")
    with urlopen(url, timeout=120) as r:
        data = json.loads(r.read())
    daily = data["daily"]
    temps = [[] for _ in range(12)]
    precs = [[] for _ in range(12)]
    for i, day in enumerate(daily["time"]):
        m = int(day[5:7]) - 1
        if daily["temperature_2m_mean"][i] is not None:
            temps[m].append(daily["temperature_2m_mean"][i])
        if daily["precipitation_sum"][i] is not None:
            precs[m].append(daily["precipitation_sum"][i])
    t = np.array([np.mean(x) if x else np.nan for x in temps])
    years = len(set(d[0:4] for d in daily["time"]))
    p = np.array([np.nansum(x) / years if x else np.nan for x in precs])
    return t, p


def fig4_6_climographs():
    cities = ["哈尔滨", "北京", "武汉", "海口", "乌鲁木齐", "拉萨"]
    captions = ["温带季风", "暖温带季风", "亚热带季风", "热带季风",
                "温带大陆性", "高原山地"]
    fig, axes = plt.subplots(2, 3, figsize=(11.4, 6.8))
    months = np.arange(1, 13)
    for ax, city, cap in zip(axes.flat, cities, captions):
        t, p = city_series(city)
        ax.bar(months, p, color="#7fb3d5", width=0.62, zorder=2)
        ax.set_ylim(0, max(320, np.nanmax(p) * 1.12))
        ax2 = ax.twinx()
        ax2.plot(months, t, color="#c0392b", lw=1.8, marker="o", ms=3.4, zorder=3)
        ax2.set_ylim(-32, 42)
        ax2.axhline(0, color="#bbbbbb", lw=0.6)
        ax.set_title(f"{city}（{cap}）", fontsize=11, color=C_TEXT)
        ax.set_xlim(0.4, 12.6)
        ax.set_xticks([1, 4, 7, 10])
        ax.tick_params(labelsize=8)
        ax.grid(axis="y", color="#dde3e8", lw=0.6, zorder=0)
        ax.set_axisbelow(True)
        ax2.tick_params(labelsize=8, colors="#c0392b")
    for r in range(2):
        axes[r, 0].set_ylabel("降水量（mm）", fontsize=9, color="#33566b")
        axes[r, 0].tick_params(axis="y", colors="#33566b")
    fig.text(0.995, 0.965, "红线：月平均气温（右轴，℃）\n蓝柱：月降水量（左轴，mm）",
             ha="right", va="top", fontsize=9.5, color="#33566b", linespacing=1.6)
    fig.text(0.02, 0.985, "六城气候图：一年之内，中国有六种天气剧本", fontsize=14.5,
             fontweight="bold", color=C_TEXT, va="top")
    fig.text(0.02, 0.925, "2004—2023 年逐日再分析资料的月度平均",
             fontsize=9.3, color="#666666", va="top")
    fig.text(0.02, 0.012,
             "数据：Open-Meteo Archive（基于 ERA5 再分析），城市坐标取市驻地", fontsize=8,
             color="#555555")
    fig.tight_layout(rect=(0, 0.05, 1, 0.90))
    fig.savefig(os.path.join(FIGURES, "fig4-1_六城气候图.png"), dpi=DPI)
    plt.close(fig)


def fetch_ibtracs():
    os.makedirs(IBTRACS, exist_ok=True)
    fp = os.path.join(IBTRACS, "ibtracs.WP.list.v04r01.csv")
    if os.path.exists(fp):
        return
    url = ("https://www.ncei.noaa.gov/data/international-best-track-"
           "archive-for-climate-stewardship-ibtracs/v04r01/access/csv/"
           "ibtracs.WP.list.v04r01.csv")
    print("downloading IBTrACS WP ...")
    with urlopen(url, timeout=300) as r:
        open(fp, "wb").write(r.read())
    print("done", os.path.getsize(fp))


def fig4_7_typhoon():
    import pandas as pd
    fetch_ibtracs()
    fp = os.path.join(IBTRACS, "ibtracs.WP.list.v04r01.csv")
    df = pd.read_csv(fp, low_memory=False, skiprows=[1],
                     usecols=["SID", "SEASON", "BASIN", "LAT", "LON"])
    df = df[(df["SEASON"] >= 1949) & (df["SEASON"] <= 2024)]
    df["LAT"] = pd.to_numeric(df["LAT"], errors="coerce")
    df["LON"] = pd.to_numeric(df["LON"], errors="coerce")
    df = df.dropna(subset=["LAT", "LON"])
    df = df[(df.LAT > 2) & (df.LAT < 48) & (df.LON > 100) & (df.LON < 145)]

    gdf = gpd.read_file(os.path.join(DATA, "boundaries", "datav", "100000.json"))
    land = gdf[gdf["name"].notna() & (gdf["name"].str.len() > 0)].to_crs(ALBERS)
    coast = land.boundary.union_all()
    pts = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.LON, df.LAT),
                           crs="EPSG:4326").to_crs(ALBERS)
    near = gpd.sjoin_nearest(pts, gpd.GeoDataFrame(geometry=[coast], crs=ALBERS),
                             max_distance=150000, distance_col="d")
    storm_ids = set(near["SID"])

    dem, minx, maxy = load_cache()
    h, w = dem.shape
    fig, ax = new_map_axes((11.0, 9.2))
    ax.set_facecolor("#dfe8f0")
    sh = hillshade(dem)
    rgba = np.zeros((h, w, 4))
    f = 0.55 + 0.45 * sh
    rgba[:, :, 0], rgba[:, :, 1], rgba[:, :, 2] = 0.93 * f, 0.91 * f, 0.87 * f
    rgba[:, :, 3] = np.where(np.isnan(dem), 0.0, 1.0)
    ax.imshow(rgba, extent=(minx, minx + w * RES_A, maxy - h * RES_A, maxy),
              origin="upper", interpolation="bilinear", zorder=1)
    land.boundary.plot(ax=ax, color="#6a6a6a", linewidth=0.3, zorder=3)
    dash = gdf[gdf["name"].isna() | (gdf["name"].str.len() == 0)].to_crs(ALBERS)
    if len(dash):
        dash.plot(ax=ax, facecolor="none", edgecolor="#3b5872", linewidth=0.7,
                  ls="--", zorder=4)
    df2 = pts[pts["SID"].isin(storm_ids)]
    for sid, g in df2.groupby("SID"):
        ax.plot(g.geometry.x, g.geometry.y, color="#c0392b", lw=0.25,
                alpha=0.35, zorder=5, solid_capstyle="round")
    ax.plot([], [], color="#c0392b", lw=1.2, alpha=0.6,
            label=f"1949—2024 年距中国海岸线 150 km 以内的热带气旋路径（{len(storm_ids)} 个）")
    ax.legend(loc="lower left", bbox_to_anchor=(0.01, 0.10), fontsize=9,
              framealpha=0.9, edgecolor="#cccccc")
    set_extent_from(ax, land, pad_frac=0.03)
    add_title(ax, "影响中国的热带气旋路径（1949—2024）",
              "路径距中国海岸线 150 km 以内；西北太平洋是全球热带气旋最活跃的海区")
    save_fig(fig, ax, "fig4-8_台风路径图.png",
             footer="数据：NOAA IBTrACS v04r01（西太平洋盆地全序列）；距离为投影平面近似\n"
                    "示意地图，不作为权属划界依据")


if __name__ == "__main__":
    setup()
    fig4_1_t_jan()
    fig4_2_t_jul()
    fig4_3_prec()
    fig4_4_zones()
    fig4_5_belts()
    fig4_6_climographs()
    fig4_7_typhoon()
    print("ch04 climate done")
