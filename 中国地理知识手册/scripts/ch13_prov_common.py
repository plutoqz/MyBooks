# -*- coding: utf-8 -*-
"""13.5 分省详述通用绘图模块。

fig_relief(...)  省级地势与政区图：z9 DEM 晕渲、区外淡出、编号标记 +
                  图下编号列表（TagBoard）；密集小政区可选放大插图。
fig_pop(...)     分区常住人口（七普）与人口密度双联条形图。

政区标注点一律取自 DataV 原始文件（EPSG:4326）的 representative_point()。
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
                   new_map_axes)
from ch03_terrain import to_albers
from prov_pipeline import prov_dem, prov_load, relief_rgba_p, to_albers
from ch13_regions import TagBoard, _save_with_legend


def _paper_overlay(shape, land, keep_mask, alpha=0.9):
    """land 上、keep_mask 之外的像素淡为纸色。"""
    flat = np.zeros(shape + (4,))
    flat[..., 0], flat[..., 1], flat[..., 2] = 0.949, 0.941, 0.918
    flat[..., 3] = np.where(land & (keep_mask == 0), alpha, 0.0)
    return flat


def _load_rivers():
    return gpd.read_file(os.path.join(
        DATA, "boundaries", "natural_earth", "ne_50m_rivers_lake_centerlines",
        "ne_50m_rivers_lake_centerlines.shp")).to_crs(ALBERS)


def fig_relief(fig_no, adcode, fname, title, subtitle, geo_tags=(),
               inset_names=None, inset_label=None, footer_lines=(),
               tag_top=0.25, cols=2, chunk=4, tag_fs=8.8, footer_y0=0.012,
               map_bottom=0.30, skip_names=(), rename_map=None):
    """省级地势与政区编号图。

    geo_tags: (kind, name, lon, lat[, kwargs]) 序列，kind ∈ k/r/l/c/m/p。
    inset_names: 密集小政区名单——画入放大插图并先编号，主图红框指示。
    map_bottom: 地图区下边距；政区多、编号列表占两段时调大防与脚注叠压。
    skip_names: 不参与编号标注的政区名（界线照画，如兵团直辖县级市）。
    rename_map: 编号列表中的政区名替换（如长自治州全称→简称），仅影响图下图例。
    """
    dem, minx, maxy, res = prov_dem(adcode, zoom=9, res=300.0)
    h, w = dem.shape
    extent = (minx, minx + w * res, maxy - h * res, maxy)
    prov = prov_load(adcode)
    raw = gpd.read_file(os.path.join(DATA, "boundaries", "datav",
                                     f"{adcode}_full.json"))  # EPSG:4326
    union = prov.union_all()

    bx0, by0, bx1, by1 = prov.total_bounds
    ratio = (bx1 - bx0) / (by1 - by0)
    fw = 10.6 if ratio >= 1 else 9.8
    fh = min(max(fw / ratio * 0.82, 8.6), 11.4)
    fig, ax = new_map_axes((fw, fh))
    right = 0.73 if inset_names else 0.985
    fig.subplots_adjust(bottom=map_bottom, top=0.985, left=0.005, right=right)
    ax.set_facecolor(C_SEA)
    ax.imshow(relief_rgba_p(dem, res), extent=extent, origin="upper",
              interpolation="bilinear", zorder=1)
    ax.set_xlim(extent[0], extent[1])
    ax.set_ylim(extent[2], extent[3])

    tf = from_origin(minx, maxy, res, res)
    inside = rasterize([(union, 1)], out_shape=(h, w), transform=tf,
                       fill=0, dtype="uint8")
    ax.imshow(_paper_overlay((h, w), ~np.isnan(dem), inside), extent=extent,
              origin="upper", zorder=2.5)

    prov.boundary.plot(ax=ax, color="#4a4a4a", lw=0.5, zorder=5)
    gpd.GeoSeries([union], crs=ALBERS).boundary.plot(
        ax=ax, color="#2c3e50", lw=1.2, zorder=5.5)

    riv = _load_rivers()
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    view = riv.cx[x0:x1, y0:y1]
    if len(view):
        view.plot(ax=ax, color="#3d6fa8", lw=1.0, zorder=6)

    tb = TagBoard()
    n0 = 0
    if inset_names:
        core = prov[prov["name"].isin(inset_names)]
        core_union = core.union_all()
        cb = raw[raw["name"].isin(inset_names)].total_bounds  # EPSG:4326
        padx = (cb[2] - cb[0]) * 0.12 + 0.01
        pady = (cb[3] - cb[1]) * 0.12 + 0.008
        ilon0, ilat0, ilon1, ilat1 = (cb[0] - padx, cb[1] - pady,
                                      cb[2] + padx, cb[3] + pady)
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

        axin = fig.add_axes([0.745, 0.55, 0.225, 0.215])
        axin.set_xticks([])
        axin.set_yticks([])
        axin.set_facecolor(C_SEA)
        axin.imshow(relief_rgba_p(sub, res),
                    extent=(iminx, iminx + iw * res, imaxy - ih * res, imaxy),
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
        for name in inset_names:
            pt = raw.loc[raw["name"] == name, "geometry"].iloc[0] \
                .representative_point()
            tb.add(axin, "c", name, pt.x, pt.y)
        for spine in axin.spines.values():
            spine.set_color("#b03a2e")
            spine.set_linewidth(1.2)
        fig.text(0.745 + 0.1125, 0.538, inset_label, fontsize=8.5,
                 color="#b03a2e", ha="center", va="top")
        n0 = len(inset_names)
        # 红框用 Albers 坐标的政区范围（勿用经纬度 bounds，会把 xlim 撑出图外）
        abx0, aby0, abx1, aby1 = core.total_bounds
        padm = ((bx1 - bx0) + (by1 - by0)) * 0.008
        rect = plt.Rectangle((abx0 - padm, aby0 - padm),
                             (abx1 - abx0) + 2 * padm,
                             (aby1 - aby0) + 2 * padm, fill=False,
                             ec="#b03a2e", lw=1.4, zorder=8.5)
        ax.add_patch(rect)

    outer = [n for n in prov["name"]
             if (not inset_names or n not in inset_names)
             and n not in skip_names]
    for name in outer:
        pt = raw.loc[raw["name"] == name, "geometry"].iloc[0] \
            .representative_point()
        tb.add(ax, "c", rename_map.get(name, name) if rename_map else name,
               pt.x, pt.y)
    print(f"fig13-{fig_no}: {n0} inset + {len(outer)} main = {n0+len(outer)} tags")

    for tag in geo_tags:
        kind, name, lon, lat = tag[0], tag[1], tag[2], tag[3]
        kw = tag[4] if len(tag) > 4 else {}
        tb.add(ax, kind, name, lon, lat, **kw)

    add_title(ax, title, subtitle)
    tb.render(fig, fs=tag_fs, cols=cols, top=tag_top, chunk=chunk)
    _save_with_legend(fig, fname, list(footer_lines), footer_y0=footer_y0)
    areas = dict(zip(prov["name"], prov.geometry.area / 1e6))
    return {k: round(v, 0) for k, v in areas.items()}


def fig_pop(fig_no, adcode, pop7, fname, suptitle, footer, panel_titles=None,
            unit_note=""):
    """分区常住人口（七普）与人口密度双联条形图。"""
    prov = prov_load(adcode)
    areas = dict(zip(prov["name"], prov.geometry.area / 1e6))
    d = pd.DataFrame({"name": list(pop7.keys()),
                      "pop": [pop7[k] for k in pop7]})
    d["area"] = d["name"].map(areas)
    d["dens"] = d["pop"] * 1e4 / d["area"]
    d = d.sort_values("pop", ascending=False).reset_index(drop=True)
    print(d.to_string())
    print("七普合计（万）：", d["pop"].sum().round(1))
    print("密度最大/最小：", d.loc[d["dens"].idxmax(), "name"],
          round(d["dens"].max()), d.loc[d["dens"].idxmin(), "name"],
          round(d["dens"].min()))

    t1, t2 = panel_titles or ("分区常住人口（2020 年七普）", "分区人口密度（七普口径）")
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

    panel(axes[0], "pop", t1, "万人", "{:,.1f}")
    panel(axes[1], "dens", t2, "人/km²", "{:,.0f}")
    fig.text(0.02, 0.965, suptitle, fontsize=14.5, fontweight="bold",
             color=C_TEXT)
    fig.text(0.02, 0.938, unit_note or
             "人口为第七次全国人口普查（2020-11-01）口径；面积按 DataV 界线在 Albers 投影下量算",
             fontsize=9.0, color="#666666")
    fig.text(0.02, 0.02, footer, fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.045, 1, 0.92))
    fig.savefig(os.path.join(FIGURES, fname), dpi=DPI)
    plt.close(fig)
