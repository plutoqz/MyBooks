# -*- coding: utf-8 -*-
"""分省（省级政区）地理管线：DataV 界线 + AWS Terrain 高分辨率 DEM。

prov_dem(adcode, zoom=9, res=300)
    下载省级政区范围的 terrarium 瓦片，重投影到 Albers 网格，
    缓存 data/dem/province/{adcode}_z{zoom}.npz（dem/minx/maxy/res）。
    陆地掩膜与全国管线一致：政区 + 邻国之外为 NaN。

hillshade_p(dem, res) / relief_rgba_p(dem, res)
    省级分辨率版本的山体阴影与高程分层设色（颜色与 ch03_terrain 一致）。

prov_load(adcode)
    读 DataV {adcode}_full.json（地级/县级政区，已投影 Albers）。
"""
import math
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from urllib.request import urlopen

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import ALBERS, DATA
from ch03_terrain import ELEV_BINS, ELEV_COLORS, _tile_xy
from pyproj import Transformer
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject

_T = Transformer.from_crs("EPSG:4326", ALBERS, always_xy=True)

DEM_PROV_DIR = os.path.join(DATA, "dem", "province")


def to_albers(lon, lat):
    return _T.transform(lon, lat)


def prov_path(adcode):
    """政区矢量文件路径：优先带下级政区的 _full.json，缺失时退回省级轮廓。"""
    full = os.path.join(DATA, "boundaries", "datav", f"{adcode}_full.json")
    if os.path.exists(full):
        return full
    return os.path.join(DATA, "boundaries", "datav", f"{adcode}.json")


def prov_load(adcode):
    import geopandas as gpd
    return gpd.read_file(prov_path(adcode)).to_crs(ALBERS)


def prov_dem(adcode, zoom=9, res=300.0, pad_frac=0.06):
    cache = os.path.join(DEM_PROV_DIR, f"{adcode}_z{zoom}.npz")
    if os.path.exists(cache):
        d = np.load(cache)
        return d["dem"], float(d["minx"]), float(d["maxy"]), float(d["res"])

    import geopandas as gpd
    raw = gpd.read_file(prov_path(adcode))
    b = raw.total_bounds  # lonlat
    dx, dy = (b[2] - b[0]) * pad_frac, (b[3] - b[1]) * pad_frac
    lon0, lat0, lon1, lat1 = b[0] - dx, b[1] - dy, b[2] + dx, b[3] + dy

    xr = _tile_xy(lon0, 0, zoom)[0], _tile_xy(lon1, 0, zoom)[0]
    yr = _tile_xy(0, lat1, zoom)[1], _tile_xy(0, lat0, zoom)[1]
    x0, x1 = int(math.floor(xr[0])), int(math.floor(xr[1]))
    y0, y1 = int(math.floor(yr[0])), int(math.floor(yr[1]))
    nx, ny = x1 - x0 + 1, y1 - y0 + 1
    mosaic = np.zeros((ny * 256, nx * 256), dtype=np.float32)
    tile_dir = os.path.join(DEM_PROV_DIR, "terrain", f"z{zoom}")
    os.makedirs(tile_dir, exist_ok=True)

    def fetch(tx, ty):
        path = os.path.join(tile_dir, f"{tx}_{ty}.png")
        if os.path.exists(path):
            return path
        url = (f"https://s3.amazonaws.com/elevation-tiles-prod/"
               f"terrarium/{zoom}/{tx}/{ty}.png")
        for _ in range(3):
            try:
                raw_bytes = urlopen(url, timeout=60).read()
                with open(path, "wb") as f:
                    f.write(raw_bytes)
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

    from PIL import Image
    for (tx, ty), p in paths.items():
        arr = np.asarray(Image.open(p), dtype=np.float64)
        elev = arr[:, :, 0] * 256 + arr[:, :, 1] + arr[:, :, 2] / 256 - 32768
        r, c = ty - y0, tx - x0
        mosaic[r * 256:(r + 1) * 256, c * 256:(c + 1) * 256] = elev

    n = 2 ** zoom
    res_deg = 360 / n / 256
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

    # 陆地掩膜（政区 + 全国 + 邻国之外为 NaN，海面自然露出底色）
    _raw = raw.to_crs(ALBERS)
    _raw["geometry"] = _raw.geometry.buffer(0)  # 修复 DataV 界线的无效几何
    prov_u = _raw.union_all()
    china = gpd.read_file(os.path.join(DATA, "boundaries", "datav",
                                       "100000_full.json")).to_crs(ALBERS)
    world = gpd.read_file(os.path.join(DATA, "boundaries", "natural_earth",
                                       "ne_50m",
                                       "ne_50m_admin_0_countries.shp")
                          ).to_crs(ALBERS)
    geoms = [prov_u] + list(china.geometry) + list(world.geometry)
    from rasterio.features import rasterize
    mask = rasterize([(g, 1) for g in geoms], out_shape=(h, w),
                     transform=dst_tf, fill=0, dtype="uint8")
    dem[mask == 0] = np.nan

    os.makedirs(DEM_PROV_DIR, exist_ok=True)
    np.savez_compressed(cache, dem=dem, minx=minx, maxy=maxy, res=res)
    return dem, minx, maxy, res


def hillshade_p(dem, res):
    gy, gx = np.gradient(dem, res)
    normal = np.sqrt(1 + gx ** 2 + gy ** 2)
    az, alt = math.radians(315.0), math.radians(45.0)
    slope = np.arctan(1 / normal)
    aspect = np.arctan2(gx, -gy)
    sh = (np.sin(alt) * np.sin(slope)
          + np.cos(alt) * np.cos(slope) * np.cos(az - aspect))
    return np.clip(sh, 0, 1)


def relief_rgba_p(dem, res, shade_alpha=0.6):
    lut = np.array([[int(c[i:i + 2], 16) for i in (1, 3, 5)]
                    for c in ELEV_COLORS], dtype=np.float64)
    idx = np.searchsorted(ELEV_BINS, np.nan_to_num(dem, nan=0.0),
                          side="right") - 1
    idx = np.clip(idx, 0, len(lut) - 1)
    rgb = lut[idx] / 255.0
    sh = hillshade_p(dem, res)
    w = shade_alpha + (1 - shade_alpha) * sh
    alpha = np.where(np.isnan(dem), 0.0, 1.0)
    return np.concatenate([rgb * w[..., None], alpha[..., None]], axis=2)
