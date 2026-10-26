# -*- coding: utf-8 -*-
"""第 3 章 地形地貌 —— DEM 基础图（3.1 节）。

数据：AWS Terrain Tiles（terrarium 编码，公开无注册），z7 全国拼接后
重投影到 Albers 等积圆锥，缓存为 npz 供其他章节脚本复用。

fig3-1 全国地势晕渲图（高程分级设色 + 山体阴影 + 三级阶梯界线）
fig3-2 沿 30°N 与 40°N 地形剖面
fig3-3 三级阶梯示意（块状图）
"""
import math
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from urllib.request import urlopen

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Polygon as MplPolygon
from pyproj import Transformer, Geod
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject
from rasterio.features import rasterize

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import (ALBERS, C_SEA, C_TEXT, DATA, DPI, FIGURES, add_north_arrow,
                   add_title, new_map_axes, save_fig, set_extent_from, setup)
from geo_features import STAIR1, STAIR2

SEGS1 = [  # 第一级阶梯界线：昆仑山 / 祁连山 / 横断山东缘
    STAIR1[:5], STAIR1[5:9], STAIR1[9:],
]
SEGS2 = [  # 第二级阶梯界线：大兴安岭 / 太行山 / 巫山 / 雪峰山
    STAIR2[:5], STAIR2[5:8], STAIR2[8:10], STAIR2[10:],
]

DEM_DIR = os.path.join(DATA, "dem")
CACHE = os.path.join(DEM_DIR, "china_dem_albers_z7.npz")
Z = 7
RES_A = 1800.0  # 目标网格分辨率（m/px）

_T = Transformer.from_crs("EPSG:4326", ALBERS, always_xy=True)


def to_albers(lon, lat):
    return _T.transform(lon, lat)


# ---------------------------------------------------------------- 瓦片下载与拼接
def _tile_xy(lon, lat, z):
    n = 2 ** z
    x = (lon + 180) / 360 * n
    la = math.radians(max(-85.05, min(85.05, lat)))
    y = (1 - math.asinh(math.tan(la)) / math.pi) / 2 * n
    return x, y


def _fetch_tile(url, tries=3):
    for _ in range(tries):
        try:
            with urlopen(url, timeout=45) as r:
                return r.read()
        except Exception:
            continue
    return None


def build_mosaic():
    lon0, lon1, lat0, lat1 = 72.5, 135.5, 3.2, 53.8
    xr = _tile_xy(lon0, 0, Z)[0], _tile_xy(lon1, 0, Z)[0]
    yr = _tile_xy(0, lat1, Z)[1], _tile_xy(0, lat0, Z)[1]
    x0, x1 = int(math.floor(xr[0])), int(math.floor(xr[1]))
    y0, y1 = int(math.floor(yr[0])), int(math.floor(yr[1]))
    nx, ny = x1 - x0 + 1, y1 - y0 + 1
    mosaic = np.zeros((ny * 256, nx * 256), dtype=np.float32)
    tile_dir = os.path.join(DEM_DIR, "terrain", f"z{Z}")
    os.makedirs(tile_dir, exist_ok=True)

    jobs = []
    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            path = os.path.join(tile_dir, f"{tx}_{ty}.png")
            if os.path.exists(path):
                jobs.append((tx, ty, path, True))
            else:
                jobs.append((tx, ty,
                             f"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{Z}/{tx}/{ty}.png",
                             False))

    def work(job):
        tx, ty, src, local = job
        if not local:
            raw = _fetch_tile(src)
            if raw is None:
                return None
            with open(os.path.join(tile_dir, f"{tx}_{ty}.png"), "wb") as f:
                f.write(raw)
            src = os.path.join(tile_dir, f"{tx}_{ty}.png")
        from PIL import Image
        return tx, ty, np.asarray(Image.open(src), dtype=np.float64)

    with ThreadPoolExecutor(max_workers=24) as ex:
        for res in ex.map(work, jobs):
            if res is None:
                continue
            tx, ty, arr = res
            elev = arr[:, :, 0] * 256 + arr[:, :, 1] + arr[:, :, 2] / 256 - 32768
            r, c = ty - y0, tx - x0
            mosaic[r * 256:(r + 1) * 256, c * 256:(c + 1) * 256] = elev
    return mosaic, x0, y0, Z


def build_cache():
    mosaic, tx0, ty0, z = build_mosaic()
    n = 2 ** z
    res_deg = 360 / n / 256
    res_m = res_deg * 111319.4908
    west_m = -180 * 111319.4908 + tx0 * 256 * res_m
    north_m = 20037508.3428 - ty0 * 256 * res_m
    src_tf = from_origin(west_m, north_m, res_m, res_m)

    # 目标 Albers 网格
    corners = [to_albers(lon, lat) for lon, lat in
               [(72.5, 3.2), (135.5, 3.2), (72.5, 53.8), (135.5, 53.8)]]
    xs = [c[0] for c in corners]; ys = [c[1] for c in corners]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    w = int((maxx - minx) / RES_A) + 1
    h = int((maxy - miny) / RES_A) + 1
    dst_tf = from_origin(minx, maxy, RES_A, RES_A)

    dem = np.full((h, w), np.nan, dtype=np.float32)
    dem, _ = reproject(mosaic, dem,
                       src_transform=src_tf, src_crs="EPSG:3857",
                       dst_transform=dst_tf, dst_crs=ALBERS,
                       src_nodata=None, dst_nodata=np.nan,
                       resampling=Resampling.bilinear)

    # 陆地掩膜：省界 + 邻国
    gdf = gpd.read_file(os.path.join(DATA, "boundaries", "datav", "100000_full.json"))
    land = gdf[gdf["name"].notna() & (gdf["name"].str.len() > 0)]
    world = gpd.read_file(os.path.join(DATA, "boundaries", "natural_earth",
                                       "ne_50m", "ne_50m_admin_0_countries.shp"))
    geoms = list(land.to_crs(ALBERS).geometry) + list(world.to_crs(ALBERS).geometry)
    mask = rasterize([(g, 1) for g in geoms], out_shape=(h, w),
                     transform=dst_tf, fill=0, dtype="uint8")
    dem[mask == 0] = np.nan

    np.savez_compressed(CACHE, dem=dem, minx=minx, maxy=maxy, res=RES_A)
    return dem, minx, maxy


def load_cache():
    d = np.load(CACHE)
    return d["dem"], float(d["minx"]), float(d["maxy"])


# ---------------------------------------------------------------- 绘图工具
def hillshade(dem):
    gy, gx = np.gradient(dem, RES_A)
    slope = np.pi / 2 - np.arctan(np.sqrt(gx ** 2 + gy ** 2))
    aspect = np.arctan2(-gx, gy)
    az, alt = math.radians(315), math.radians(45)
    sh = np.sin(alt) * np.sin(slope) + np.cos(alt) * np.cos(slope) * np.cos(az - aspect)
    return np.clip(sh, 0, 1)


ELEV_BINS = [0, 50, 200, 500, 1000, 1500, 2000, 3000, 4000, 5000, 6000, 8000]
ELEV_COLORS = ["#bfe3b4", "#b6dcae", "#e2e2a9", "#e8d59a", "#ddc08a", "#d3a670",
               "#c08a58", "#a96a42", "#9c5535", "#b1b1b1", "#e8e8e8"]


def relief_rgba(dem, shade_alpha=0.6):
    lut = np.array([[int(c[i:i + 2], 16) for i in (1, 3, 5)]
                    for c in ELEV_COLORS], dtype=np.float64)
    idx = np.searchsorted(ELEV_BINS, np.nan_to_num(dem, nan=0.0), side="right") - 1
    idx = np.clip(idx, 0, len(lut) - 1)
    rgb = lut[idx] / 255.0
    sh = hillshade(dem)
    w = shade_alpha + (1 - shade_alpha) * sh
    alpha = np.where(np.isnan(dem), 0.0, 1.0)
    return np.concatenate([rgb * w[..., None], alpha[..., None]], axis=2)


# ---------------------------------------------------------------- fig 3-1
def fig3_1_relief():
    dem, minx, maxy = load_cache()
    h, w = dem.shape
    extent = (minx, minx + w * RES_A, maxy - h * RES_A, maxy)

    fig, ax = new_map_axes((10.5, 10.8))
    ax.set_facecolor(C_SEA)
    ax.imshow(relief_rgba(dem), extent=extent, origin="upper",
              interpolation="bilinear", zorder=1)

    gdf = gpd.read_file(os.path.join(DATA, "boundaries", "datav", "100000_full.json"))
    prov = gdf[gdf["name"].notna() & (gdf["name"].str.len() > 0)].to_crs(ALBERS)
    dash = gdf[gdf["name"].isna() | (gdf["name"].str.len() == 0)].to_crs(ALBERS)
    prov.boundary.plot(ax=ax, color="#5a5a5a", linewidth=0.3, alpha=0.55, zorder=3)
    if len(dash):
        dash.plot(ax=ax, facecolor="none", edgecolor="#3b5872", linewidth=0.8,
                  ls="--", zorder=4)

    # 境外陆地改为中性灰，突出中国本体
    china_mask = rasterize(list(prov.geometry), out_shape=dem.shape,
                           transform=from_origin(minx, maxy, RES_A, RES_A),
                           fill=0, dtype="uint8")
    nb = (~np.isnan(dem)) & (china_mask == 0)
    rgba = relief_rgba(dem)
    rgba[nb, 0] = 0.898 * (0.35 + 0.65 * hillshade(dem))[nb]
    rgba[nb, 1] = 0.886 * (0.35 + 0.65 * hillshade(dem))[nb]
    rgba[nb, 2] = 0.866 * (0.35 + 0.65 * hillshade(dem))[nb]
    ax.imshow(rgba, extent=extent, origin="upper", interpolation="bilinear", zorder=2)

    for seg in SEGS1 + SEGS2:
        xs, ys = zip(*[_T.transform(lo, la) for lo, la in seg])
        ax.plot(xs, ys, color="#1a1a1a", lw=2.0, ls=(0, (6, 3)), zorder=6)
    ax.text(*to_albers(86.5, 37.3), "昆仑山—祁连山", fontsize=8.5, color="#1a1a1a",
            rotation=8, ha="center", zorder=7,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.75))
    ax.text(*to_albers(122.6, 48.2), "大兴安岭", fontsize=8.5, color="#1a1a1a",
            rotation=-52, ha="center", va="center", zorder=7,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.75))
    ax.text(*to_albers(113.2, 36.2), "太行山", fontsize=8.5, color="#1a1a1a",
            rotation=-85, ha="center", zorder=7,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.75))

    tier_specs = [("第一级阶梯\n青藏高原 >4 000 m", 88.5, 32.6),
                  ("第二级阶梯\n1 000—2 000 m", 108.5, 38.8),
                  ("第三级阶梯\n<500 m", 117.0, 33.2)]
    for txt, lo, la in tier_specs:
        x, y = to_albers(lo, la)
        ax.text(x, y, txt, fontsize=10, fontweight="bold", color="#2c3e50",
                ha="center", va="center", zorder=8, linespacing=1.5,
                bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="#999999",
                          alpha=0.85))
    add_north_arrow(ax, 0.955, 0.90, 0.05)
    set_extent_from(ax, prov)
    add_title(ax, "中国地势晕渲图", "西高东低、呈三级阶梯；虚线为两级阶梯界线（示意），断续线为南海九段线")

    # 图例色带
    from matplotlib.cm import ScalarMappable
    cmap = ListedColormap(ELEV_COLORS)
    norm = BoundaryNorm(ELEV_BINS, cmap.N)
    sm = ScalarMappable(cmap=cmap, norm=norm)
    cax = fig.add_axes([0.115, 0.075, 0.42, 0.014])
    cb = fig.colorbar(sm, cax=cax, orientation="horizontal",
                      boundaries=ELEV_BINS + [9000], ticks=ELEV_BINS)
    cb.ax.tick_params(labelsize=7.5)
    cb.set_label("海拔（m）", fontsize=8.5)

    save_fig(fig, ax, "fig3-1_中国地势晕渲图.png",
             footer="数据：AWS Terrain Tiles（ terrarium，Mapzen/OpenStreetMap 等公开数据，重采样至 1.8 km）；投影：Albers 等积圆锥\n"
                    "示意地图，阶梯界线与注记为示意，不作为权属划界依据")


# ---------------------------------------------------------------- fig 3-2
def fig3_2_profile():
    npz = np.load(os.path.join(DEM_DIR, "china_lonlat_z7.npz"))
    grid, glon0, glat0, gres = npz["grid"], float(npz["lon0"]), float(npz["lat0"]), float(npz["res"])

    fig, axes = plt.subplots(2, 1, figsize=(10.2, 6.4))
    geod = Geod(ellps="WGS84")
    specs = [
        (30.0, 80.0, 123.0, axes[0], "沿 30°N 地形剖面（西—东）",
         [("90°E 青藏高原", 90), ("99.5°E 横断山", 99.5), ("105°E 四川盆地", 105),
          ("110°E 巫山", 110), ("116°E 长江中下游平原", 116)]),
        (40.0, 73.5, 127.0, axes[1], "沿 40°N 地形剖面（西—东）",
         [("74°E 帕米尔", 74), ("83°E 塔里木盆地", 83), ("100°E 河西走廊", 100),
          ("110°E 阿拉善高原", 110), ("116.5°E 华北平原", 116.5), ("121.5°E 渤海", 121.5)]),
    ]
    for lat, lo0, lo1, ax, title, marks in specs:
        lons = np.arange(lo0, lo1, 0.02)
        cols = ((lons - glon0) / gres).astype(int)
        rows = np.full(len(lons), int((glat0 - lat) / gres))
        vals = grid[rows, cols]
        dist = np.zeros(len(lons))
        for i in range(1, len(lons)):
            _, _, d = geod.inv(lons[i - 1], lat, lons[i], lat)
            dist[i] = dist[i - 1] + d / 1000
        ax.fill_between(dist, vals, 0, color="#d3a670", lw=0)
        ax.plot(dist, vals, color="#8a5a2a", lw=0.9)
        ax.set_facecolor("#eaf2f8")
        ax.set_ylim(-200, 7000)
        ax.set_xlim(0, dist[-1])
        ax.grid(axis="y", color="#dde3e8", lw=0.7)
        ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.set_title(title, fontsize=11.5, color=C_TEXT, loc="left")
        ax.set_ylabel("海拔（m）", fontsize=9)
        for lab, lon in marks:
            dd = dist[min(len(dist) - 1, int(np.searchsorted(lons, lon)))]
            ax.axvline(dd, color="#666666", lw=0.7, ls=":", zorder=2)
            ax.text(dd, 6600, lab, fontsize=7.8, ha="center", va="top",
                    color="#444444", zorder=5)
    axes[1].set_xlabel("自西向东累计距离（km）", fontsize=9)

    fig.text(0.02, 0.012,
             "数据：AWS Terrain Tiles（z7，约 1.2 km 分辨率）；距离沿纬线按 WGS84 椭球计算",
             fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(os.path.join(FIGURES, "fig3-2_地形剖面图.png"), dpi=DPI)
    plt.close(fig)


def build_lonlat_cache():
    """沿经纬度规则网格缓存 DEM（供剖面与气候叠加使用）。"""
    mosaic, tx0, ty0, z = build_mosaic()
    n = 2 ** z
    res_deg = 360 / n / 256
    lon0 = -180 + tx0 * 256 * res_deg
    lat_top = 0.0
    # 顶部纬度：y 像素 → 纬度
    ypix = ty0 * 256
    lat0_top = math.degrees(2 * math.atan(math.exp(math.pi * (1 - 2 * ypix / (n * 256)))) - math.pi / 2)
    grid = mosaic[::4, ::4].astype(np.float32)  # 降采样 4 倍减小体积
    np.savez_compressed(os.path.join(DEM_DIR, "china_lonlat_z7.npz"),
                        grid=grid, lon0=lon0, lat0=lat0_top, res=res_deg * 4)
    return grid, lon0, lat0_top, res_deg * 4


    print("ch03 terrain done")


# ---------------------------------------------------------------- fig 3-3
def fig3_3_stairs():
    fig, ax = plt.subplots(figsize=(10.4, 5.4))
    blocks = [
        (0.0, 3.1, 4400, "#c08a58", "第一级阶梯：青藏高原", "平均海拔 4 000 m 以上"),
        (3.1, 3.5, 1500, "#e8d59a", "第二级阶梯：高原与大盆地", "海拔多为 1 000—2 000 m"),
        (6.6, 2.6, 420, "#bfe3b4", "第三级阶梯：平原与丘陵", "海拔多在 500 m 以下"),
    ]
    for x0, wd, h, c, t1, t2 in blocks:
        ax.add_patch(MplPolygon([(x0, 0), (x0, h), (x0 + wd, h), (x0 + wd, 0)],
                                closed=True, fc=c, ec="#8a5a2a", lw=1.4, zorder=3))
        ax.text(x0 + wd / 2, h + 260, t1, ha="center", va="bottom", fontsize=11.5,
                fontweight="bold", color=C_TEXT, zorder=5)
        y2 = h + 1000 if h < 1000 else h - 720
        ax.text(x0 + wd / 2, y2, t2, ha="center", va="center", fontsize=9.5,
                color="#4a3520", zorder=5)
    ax.add_patch(MplPolygon([(9.2, 0), (11.6, 0), (11.6, -200), (9.2, -200)],
                            closed=True, fc=C_SEA, ec="none", zorder=2))
    ax.text(10.4, -105, "大陆架（水深 <200 m）— 继续向大洋倾斜", ha="center",
            va="center", fontsize=9, color="#33566b", zorder=4)
    ax.axhline(0, color="#33566b", lw=0.8, zorder=1)

    for x, lab in [(3.1, "昆仑山—祁连山—横断山"), (6.6, "大兴安岭—太行山—巫山—雪峰山")]:
        ax.axvline(x, color="#1a1a1a", lw=1.6, ls=(0, (6, 3)), ymax=0.96, zorder=4)
        ax.text(x, 5750, lab, ha="center", va="bottom", fontsize=9.5,
                color="#1a1a1a", zorder=5,
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#999999", alpha=0.9))
    ax.annotate("", xy=(11.2, 3900), xytext=(10.1, 3900),
                arrowprops=dict(arrowstyle="->", color="#888888", lw=1.2))
    ax.text(10.65, 4150, "地势自西\n向东倾斜", ha="center", fontsize=9.5, color="#555555")
    ax.text(-0.15, -330, "西", fontsize=11, ha="left")
    ax.text(11.5, -330, "东", fontsize=11, ha="right")
    ax.set_xlim(-0.4, 11.8)
    ax.set_ylim(-420, 6600)
    ax.set_yticks([0, 1000, 2000, 3000, 4000, 5000])
    ax.set_yticklabels(["0", "1 000", "2 000", "3 000", "4 000", "5 000"])
    ax.set_ylabel("海拔（m，示意）", fontsize=9.5)
    ax.set_xticks([])
    for s in ("top", "right", "bottom"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color="#dde3e8", lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    fig.text(0.02, 0.012, "示意图：阶梯高差不按垂直比例绘制", fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(os.path.join(FIGURES, "fig3-3_三级阶梯示意图.png"), dpi=DPI)
    plt.close(fig)


if __name__ == "__main__":
    setup()
    fig3_1_relief()
    fig3_2_profile()
    fig3_3_stairs()
    print("ch03 terrain done")
