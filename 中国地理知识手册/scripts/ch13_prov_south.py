# -*- coding: utf-8 -*-
"""13.5 分省详述·南方线通用绘图模块（自包含，不依赖 ch13_prov_common）。

北方线正在并行推进，其 ch13_prov_common.py 处于活跃修改中；南方线使用本模块，
仅依赖稳定的共享基础设施（style / prov_pipeline / ch03_terrain / ch13_regions）。

fig_relief(...)  省级地势与政区图：z9 DEM 晕渲、区外淡出、编号标记 +
                  图下编号列表（TagBoard）；密集小政区可选放大插图。
fig_pop(...)     分区常住人口（七普）与人口密度双联条形图（nd 控制小数位）。

政区标注点一律取自 DataV 原始文件（EPSG:4326）的 representative_point()。
"""
import math
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
from prov_pipeline import prov_dem, prov_load, prov_path, relief_rgba_p
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


def _load_lakes():
    return gpd.read_file(os.path.join(
        DATA, "boundaries", "natural_earth", "ne_50m_lakes",
        "ne_50m_lakes.shp")).to_crs(ALBERS)


def prov_dem_excl(adcode, exclude=(), zoom=9, res=300.0, pad_frac=0.06):
    """prov_dem 的过滤版：范围与缓存键排除指定政区（如三沙市诸岛）。

    逻辑与 prov_pipeline.prov_dem 相同，仅 bounds 取过滤后的政区。
    """
    import geopandas as gpd
    from concurrent.futures import ThreadPoolExecutor
    from urllib.request import urlopen
    from PIL import Image
    from ch03_terrain import _tile_xy
    from rasterio.warp import Resampling, reproject

    cache = os.path.join(
        DATA, "dem", "province",
        f"{adcode}_z{zoom}_excl{'-'.join(exclude)}.npz")
    if os.path.exists(cache):
        d = np.load(cache)
        return d["dem"], float(d["minx"]), float(d["maxy"]), float(d["res"])

    raw = gpd.read_file(prov_path(adcode))
    keep = raw[~raw["name"].isin(exclude)]
    b = keep.total_bounds
    dx, dy = (b[2] - b[0]) * pad_frac, (b[3] - b[1]) * pad_frac
    lon0, lat0, lon1, lat1 = b[0] - dx, b[1] - dy, b[2] + dx, b[3] + dy

    xr = _tile_xy(lon0, 0, zoom)[0], _tile_xy(lon1, 0, zoom)[0]
    yr = _tile_xy(0, lat1, zoom)[1], _tile_xy(0, lat0, zoom)[1]
    x0, x1 = int(math.floor(xr[0])), int(math.floor(xr[1]))
    y0, y1 = int(math.floor(yr[0])), int(math.floor(yr[1]))
    nx, ny = x1 - x0 + 1, y1 - y0 + 1
    mosaic = np.zeros((ny * 256, nx * 256), dtype=np.float32)
    tile_dir = os.path.join(DATA, "dem", "province", "terrain", f"z{zoom}")
    os.makedirs(tile_dir, exist_ok=True)

    def fetch(tx, ty):
        path = os.path.join(tile_dir, f"{tx}_{ty}.png")
        if os.path.exists(path):
            return path
        url = (f"https://s3.amazonaws.com/elevation-tiles-prod/"
               f"terrarium/{zoom}/{tx}/{ty}.png")
        for _ in range(3):
            try:
                buf = urlopen(url, timeout=60).read()
                with open(path, "wb") as f:
                    f.write(buf)
                return path
            except Exception:
                continue
        return None

    paths = {}
    with ThreadPoolExecutor(max_workers=16) as ex:
        futs = {(tx, ty): ex.submit(fetch, tx, ty)
                for ty in range(y0, y1 + 1) for tx in range(x0, x1 + 1)}
        for k, fu in futs.items():
            p = fu.result()
            if p:
                paths[k] = p

    for (tx, ty), p in paths.items():
        arr = np.asarray(Image.open(p), dtype=np.float64)
        elev = arr[:, :, 0] * 256 + arr[:, :, 1] + arr[:, :, 2] / 256 - 32768
        r, c = ty - y0, tx - x0
        mosaic[r * 256:(r + 1) * 256, c * 256:(c + 1) * 256] = elev

    res_deg = 360 / 2 ** zoom / 256
    res_m = res_deg * 111319.4908
    west_m = -180 * 111319.4908 + x0 * 256 * res_m
    north_m = 20037508.3428 - y0 * 256 * res_m
    src_tf = from_origin(west_m, north_m, res_m, res_m)

    corners = [to_albers(lon0, lat0), to_albers(lon1, lat0),
               to_albers(lon0, lat1), to_albers(lon1, lat1)]
    xs = [c[0] for c in corners]
    ys = [c[1] for c in corners]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    w = int((maxx - minx) / res) + 1
    h = int((maxy - miny) / res) + 1
    dst_tf = from_origin(minx, maxy, res, res)

    dem = np.full((h, w), np.nan, dtype=np.float32)
    dem, _ = reproject(mosaic, dem,
                       src_transform=src_tf, src_crs="EPSG:3857",
                       dst_transform=dst_tf, dst_crs=ALBERS,
                       src_nodata=None, dst_nodata=np.nan,
                       resampling=Resampling.bilinear)

    _keep = keep.to_crs(ALBERS)
    _keep["geometry"] = _keep.geometry.buffer(0)  # 修复无效几何
    prov_u = _keep.union_all()
    china = gpd.read_file(os.path.join(
        DATA, "boundaries", "datav", "100000_full.json")).to_crs(ALBERS)
    world = gpd.read_file(os.path.join(
        DATA, "boundaries", "natural_earth", "ne_50m",
        "ne_50m_admin_0_countries.shp")).to_crs(ALBERS)
    geoms = [prov_u] + list(china.geometry) + list(world.geometry)
    mask = rasterize([(g, 1) for g in geoms], out_shape=(h, w),
                     transform=dst_tf, fill=0, dtype="uint8")
    dem[mask == 0] = np.nan

    np.savez_compressed(cache, dem=dem, minx=minx, maxy=maxy, res=res)
    return dem, minx, maxy, res


def fig_relief(fig_no, adcode, fname, title, subtitle, geo_tags=(),
               inset_names=None, inset_label=None, footer_lines=(),
               tag_top=0.25, cols=2, chunk=4, aliases=None, exclude_names=(),
               number_cities=True, zoom=9):
    """省级地势与政区编号图。

    geo_tags: (kind, name, lon, lat[, kwargs]) 序列，kind ∈ k/r/l/c/m/p/h。
    inset_names: 密集小政区名单——画入放大插图并先编号，主图红框指示。
    aliases: {政区全称: 图上显示名}，避免超长政区名撑出图例画布。
    exclude_names: 不参与编号与图幅范围的政区（如三沙市）。
    number_cities: False 时不对下级政区编号（区县过多者改用地理要素标注）。
    zoom: DEM 瓦片级别。面积小的城市政区（港澳）用 11—12 级提高地形分辨率，
          网格分辨率随级别同步细化（9 级 300 m，11 级 75 m，12 级 37.5 m）。
    返回 {政区名: 面积 km²}（Albers 量算）。
    """
    aliases = aliases or {}
    exclude_names = list(exclude_names)
    res = 300.0 * 2 ** (9 - zoom)
    if exclude_names:
        dem, minx, maxy, res = prov_dem_excl(
            adcode, exclude_names, zoom=zoom, res=res)
    else:
        dem, minx, maxy, res = prov_dem(adcode, zoom=zoom, res=res)
    h, w = dem.shape
    extent = (minx, minx + w * res, maxy - h * res, maxy)
    prov = prov_load(adcode)
    raw = gpd.read_file(prov_path(adcode))  # EPSG:4326
    if exclude_names:
        prov = prov[~prov["name"].isin(exclude_names)]
        raw = raw[~raw["name"].isin(exclude_names)]
    prov["geometry"] = prov.geometry.buffer(0)  # 修复无效几何
    union = prov.union_all()

    bx0, by0, bx1, by1 = prov.total_bounds
    ratio = (bx1 - bx0) / (by1 - by0)
    fw = 10.6 if ratio >= 1 else 9.8
    fh = min(max(fw / ratio * 0.82, 8.6), 11.4)
    fig, ax = new_map_axes((fw, fh))
    right = 0.73 if inset_names else 0.985
    fig.subplots_adjust(bottom=0.30, top=0.985, left=0.005, right=right)
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
    # 湖面画在淡出层之下：省内清晰、省外随纸色淡出
    lakes = _load_lakes()
    view_l = lakes.cx[x0:x1, y0:y1]
    if len(view_l):
        view_l.plot(ax=ax, color=C_SEA, ec="#5d8ca8", lw=0.4, zorder=2.4)

    tb = TagBoard()
    n0 = 0
    if inset_names:
        core = prov[prov["name"].isin(inset_names)]
        core["geometry"] = core.geometry.buffer(0)
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
            tb.add(axin, "c", aliases.get(name, name), pt.x, pt.y)
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

    outer = [n for n in prov["name"] if not inset_names or n not in inset_names]
    if number_cities:
        for name in outer:
            pt = raw.loc[raw["name"] == name, "geometry"].iloc[0] \
                .representative_point()
            tb.add(ax, "c", aliases.get(name, name), pt.x, pt.y)
    print(f"fig13-{fig_no}: {n0} inset + {len(outer) if number_cities else 0} main = "
          f"{n0 + (len(outer) if number_cities else 0)} tags")

    for tag in geo_tags:
        kind, name, lon, lat = tag[0], tag[1], tag[2], tag[3]
        kw = tag[4] if len(tag) > 4 else {}
        tb.add(ax, kind, name, lon, lat, **kw)

    add_title(ax, title, subtitle)
    tb.render(fig, fs=8.8, cols=cols, top=tag_top, chunk=chunk)
    _save_with_legend(fig, fname, list(footer_lines))
    areas = dict(zip(prov["name"], prov.geometry.area / 1e6))
    return {k: round(v, 0) for k, v in areas.items()}


def fig_pop(fig_no, adcode, pop7, fname, suptitle, footer, panel_titles=None,
            unit_note="", nd=1):
    """分区常住人口（七普）与人口密度双联条形图。nd=1/2 控制人数小数位。"""
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
        bars = ax.barh(dd["name"], dd[col], color="#6f9e6f",
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

    panel(axes[0], "pop", t1, "万人", "{:,." + str(nd) + "f}")
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
