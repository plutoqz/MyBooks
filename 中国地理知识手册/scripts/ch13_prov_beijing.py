# -*- coding: utf-8 -*-
"""13.5.1 北京市 —— 省域地势图与分区统计图。

fig13-7 北京市地势图（z9 DEM，300 m/px；编号标记+图下图例；
        中心城区六区过密，另设放大插图，主图以红框指示范围）
fig13-8 分区常住人口（七普）与常住人口密度（七普口径，面积按 DataV 界线量算）

注意：政区标注点一律取自 DataV 原始文件（EPSG:4326）的
representative_point()，不得用投影后坐标再作投影。
"""
import os
import sys

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from rasterio.features import rasterize
from rasterio.transform import from_origin

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import (ALBERS, C_SEA, C_TEXT, DATA, DPI, FIGURES, add_title,
                   new_map_axes, setup)
from ch03_terrain import to_albers
from prov_pipeline import (prov_dem, prov_load, relief_rgba_p, to_albers)
from ch13_regions import (TagBoard, _save_with_legend)

ADCODE = "110000"
CORE6 = ["东城区", "西城区", "朝阳区", "丰台区", "石景山区", "海淀区"]
OUTER10 = ["门头沟区", "房山区", "通州区", "顺义区", "昌平区", "大兴区",
           "怀柔区", "平谷区", "密云区", "延庆区"]

POP7 = {  # 七普常住人口（万人，2020-11-01，北京市第七次全国人口普查公报）
    "东城区": 70.9, "西城区": 110.6, "朝阳区": 345.2, "丰台区": 202.0,
    "石景山区": 56.8, "海淀区": 313.3, "门头沟区": 39.3, "房山区": 131.3,
    "通州区": 184.0, "顺义区": 132.4, "昌平区": 226.9, "大兴区": 199.4,
    "怀柔区": 44.1, "平谷区": 45.7, "密云区": 52.8, "延庆区": 34.6,
}


def _paper_overlay(shape, land, keep_mask, alpha=0.9):
    """land 上、keep_mask 之外的像素淡为纸色。"""
    flat = np.zeros(shape + (4,))
    flat[..., 0], flat[..., 1], flat[..., 2] = 0.949, 0.941, 0.918
    flat[..., 3] = np.where(land & (keep_mask == 0), alpha, 0.0)
    return flat


# ---------------------------------------------------------------- fig 13-7
def fig07_relief():
    dem, minx, maxy, res = prov_dem(ADCODE, zoom=9, res=300.0)
    h, w = dem.shape
    extent = (minx, minx + w * res, maxy - h * res, maxy)
    prov = prov_load(ADCODE)                      # Albers
    raw = gpd.read_file(os.path.join(DATA, "boundaries", "datav",
                                     f"{ADCODE}_full.json"))  # EPSG:4326
    union = prov.union_all()
    core = prov[prov["name"].isin(CORE6)]
    core_union = core.union_all()

    fig, ax = new_map_axes((9.8, 10.1))
    fig.subplots_adjust(bottom=0.315, top=0.985, left=0.005, right=0.73)
    ax.set_facecolor(C_SEA)
    ax.imshow(relief_rgba_p(dem, res), extent=extent, origin="upper",
              interpolation="bilinear", zorder=1)

    tf = from_origin(minx, maxy, res, res)
    inside = rasterize([(union, 1)], out_shape=(h, w), transform=tf,
                       fill=0, dtype="uint8")
    ax.imshow(_paper_overlay((h, w), ~np.isnan(dem), inside), extent=extent,
              origin="upper", zorder=2.5)

    prov.boundary.plot(ax=ax, color="#4a4a4a", lw=0.45, zorder=5)
    gpd.GeoSeries([union], crs=ALBERS).boundary.plot(
        ax=ax, color="#2c3e50", lw=1.1, zorder=5.5)

    riv = gpd.read_file(os.path.join(DATA, "boundaries", "natural_earth",
                                     "ne_50m_rivers_lake_centerlines",
                                     "ne_50m_rivers_lake_centerlines.shp")
                        ).to_crs(ALBERS)
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    view = riv.cx[x0:x1, y0:y1]
    if len(view):
        view.plot(ax=ax, color="#3d6fa8", lw=1.0, zorder=6)

    tb = TagBoard()
    # 中心城区六区（1—6，标注于放大插图）
    cb = raw[raw["name"].isin(CORE6)].total_bounds
    padx, pady = 0.035, 0.022
    ilon0, ilat0, ilon1, ilat1 = cb[0] - padx, cb[1] - pady, cb[2] + padx, cb[3] + pady
    ic = [to_albers(ilon0, ilat0), to_albers(ilon1, ilat0),
          to_albers(ilon0, ilat1), to_albers(ilon1, ilat1)]
    iminx, imaxx = min(c[0] for c in ic), max(c[0] for c in ic)
    iminy, imaxy = min(c[1] for c in ic), max(c[1] for c in ic)
    iw = int((imaxx - iminx) / res) + 1
    ih = int((imaxy - iminy) / res) + 1
    itf = from_origin(iminx, imaxy, res, res)
    c0 = int((iminx - minx) / res)
    r0 = int((maxy - imaxy) / res)
    sub = dem[r0:r0 + ih, c0:c0 + iw]
    inside_c = rasterize([(core_union, 1)], out_shape=sub.shape,
                         transform=itf, fill=0, dtype="uint8")

    axin = fig.add_axes([0.755, 0.56, 0.215, 0.21])
    axin.set_xticks([])
    axin.set_yticks([])
    axin.set_facecolor(C_SEA)
    axin.imshow(relief_rgba_p(sub, res), extent=(iminx, iminx + iw * res,
                                                 imaxy - ih * res, imaxy),
                origin="upper", interpolation="bilinear", zorder=1)
    axin.imshow(_paper_overlay(sub.shape, ~np.isnan(sub), inside_c),
                extent=(iminx, iminx + iw * res, imaxy - ih * res, imaxy),
                origin="upper", zorder=2.5)
    core.boundary.plot(ax=axin, color="#4a4a4a", lw=0.7, zorder=5)
    gpd.GeoSeries([core_union], crs=ALBERS).boundary.plot(
        ax=axin, color="#2c3e50", lw=1.0, zorder=5.5)
    riv_c = riv.cx[iminx:imaxx, iminy:imaxy]
    if len(riv_c):
        riv_c.plot(ax=axin, color="#3d6fa8", lw=1.0, zorder=6)
    for name in CORE6:
        pt = raw.loc[raw["name"] == name, "geometry"].iloc[0] \
            .representative_point()
        tb.add(axin, "c", name, pt.x, pt.y)
    for spine in axin.spines.values():
        spine.set_color("#b03a2e")
        spine.set_linewidth(1.2)
    fig.text(0.755 + 0.1075, 0.548, "中心城区六区（放大）", fontsize=8.5,
             color="#b03a2e", ha="center", va="top")

    # 外围十区（7—16，标注于主图）
    for name in OUTER10:
        pt = raw.loc[raw["name"] == name, "geometry"].iloc[0] \
            .representative_point()
        tb.add(ax, "c", name, pt.x, pt.y)
    # 地理要素
    tb.add(ax, "k", "西山", 115.80, 39.90)
    tb.add(ax, "k", "军都山", 116.30, 40.52)
    tb.add(ax, "k", "北京平原", 116.70, 39.70)
    tb.add(ax, "r", "永定河", 115.95, 39.86)
    tb.add(ax, "r", "潮白河", 116.90, 40.30)
    tb.add(ax, "r", "北运河", 116.68, 39.83)
    tb.add(ax, "l", "密云水库", 116.86, 40.48, dot="lake")
    tb.add(ax, "l", "官厅水库", 115.72, 40.34, dot="lake")

    # 主图上以红框标出中心城区范围（对应放大插图）
    bx0, by0, bx1, by1 = core.total_bounds
    pad = 2200
    rect = plt.Rectangle((bx0 - pad, by0 - pad), (bx1 - bx0) + 2 * pad,
                         (by1 - by0) + 2 * pad, fill=False, ec="#b03a2e",
                         lw=1.4, zorder=8.5)
    ax.add_patch(rect)

    add_title(ax, "北京市地势与16区",
              "西山东屏、湾状平原——暖温带半湿润季风气候下的首都")


    tb.render(fig, bottom=0.315, fs=9.2, cols=2, top=0.26, chunk=4)
    _save_with_legend(fig, "fig13-7_北京市地势图.png",
                      ["红框为中心城区六区（编号 1—6），位置见右下放大图",
                       "界线：DataV.GeoAtlas（2021.5，仅供学习交流）；面积与高程按 DEM（AWS Terrain z9）量算；"
                       "示意地图，不作为权属划界依据；投影：Albers 等积圆锥"])
    inside_elev = dem[(inside == 1) & ~np.isnan(dem)]
    print("北京市域内高程 min/max：", inside_elev.min().round(0),
          inside_elev.max().round(0))
    areas = dict(zip(prov["name"], prov.geometry.area / 1e6))
    for name in CORE6 + OUTER10:
        print(name, round(areas[name], 0))


# ---------------------------------------------------------------- fig 13-8
def fig08_stats():
    prov = prov_load(ADCODE)
    areas = dict(zip(prov["name"], prov.geometry.area / 1e6))
    d = pd.DataFrame({"name": list(POP7.keys()),
                      "pop": [POP7[k] for k in POP7]})
    d["area"] = d["name"].map(areas)
    d["dens"] = d["pop"] * 1e4 / d["area"]
    d = d.sort_values("pop", ascending=False).reset_index(drop=True)
    print(d.to_string())
    print("七普合计（万）：", d["pop"].sum().round(1))
    print("密度最大/最小：", d.loc[d["dens"].idxmax(), "name"],
          round(d["dens"].max()),
          d.loc[d["dens"].idxmin(), "name"], round(d["dens"].min()))

    fig, axes = plt.subplots(1, 2, figsize=(12.4, 6.8))

    def panel(ax, col, title, xlabel, fmt):
        dd = d.sort_values(col, ascending=True)
        bars = ax.barh(dd["name"], dd[col], color="#5d8aa8",
                       edgecolor="white", lw=0.4, height=0.62, zorder=3)
        for b, v in zip(bars, dd[col]):
            ax.text(b.get_width() + dd[col].max() * 0.015,
                    b.get_y() + b.get_height() / 2, fmt.format(v),
                    va="center", ha="left", fontsize=8.2, color=C_TEXT,
                    zorder=4)
        ax.set_xlim(0, dd[col].max() * 1.14)
        ax.grid(axis="x", color="#dde3e8", lw=0.7, zorder=0)
        ax.set_axisbelow(True)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.spines["bottom"].set_color("#999999")
        ax.tick_params(axis="y", length=0, labelsize=9)
        ax.tick_params(axis="x", labelsize=8.2, colors="#666666")
        ax.set_xlabel(xlabel, fontsize=9, color="#666666")
        ax.set_title(title, fontsize=11.5, color=C_TEXT, pad=10)

    panel(axes[0], "pop", "分区常住人口（2020 年七普）", "万人", "{:,.1f}")
    panel(axes[1], "dens", "分区人口密度（七普口径）", "人/km²", "{:,.0f}")
    fig.text(0.02, 0.965, "北京市分区人口格局", fontsize=14.5,
             fontweight="bold", color=C_TEXT)
    fig.text(0.02, 0.938,
             "人口为第七次全国人口普查（2020-11-01）口径；面积按 DataV 界线在 Albers 投影下量算",
             fontsize=9.0, color="#666666")
    fig.text(0.02, 0.02,
             "数据：北京市第七次全国人口普查公报；界线：DataV.GeoAtlas areas_v3（2021.5，仅供学习交流）",
             fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.045, 1, 0.92))
    fig.savefig(os.path.join(FIGURES, "fig13-8_北京分区人口.png"), dpi=DPI)
    plt.close(fig)


if __name__ == "__main__":
    setup()
    fig07_relief()
    fig08_stats()
    print("beijing figures done")
