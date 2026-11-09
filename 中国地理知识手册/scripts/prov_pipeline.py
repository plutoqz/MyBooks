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
from style import ALBERS, DATA, safe_union
from ch03_terrain import ELEV_BINS, ELEV_COLORS, _tile_xy
from pyproj import Transformer
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject

_T = Transformer.from_crs("EPSG:4326", ALBERS, always_xy=True)

DEM_PROV_DIR = os.path.join(DATA, "dem", "province")


def to_albers(lon, lat):
    return _T.transform(lon, lat)


_LAND_LAYERS = {}


def land_layers():
    """中国省级 + 全球国界（Albers），进程内缓存。

    用于「图幅内哪些像素是陆地」。分省地势图的 DEM 栅格只覆盖政区的
    经纬度外包矩形，在 Albers 下这个矩形是斜置四边形，其外包框的四角
    必然落在栅格之外（值为 NaN）。若直接用 ~isnan(dem) 当陆地掩膜，
    这些角上的陆地区域会漏成底色（海蓝），在内陆省份图上表现为显眼的
    蓝色楔形块（青海左上角即如此）。
    """
    if "g" in _LAND_LAYERS:
        return _LAND_LAYERS["g"]
    import geopandas as gpd
    geoms = []
    cp = os.path.join(DATA, "boundaries", "datav", "100000_full.json")
    if os.path.exists(cp):
        cn = gpd.read_file(cp).to_crs(ALBERS)
        # 100000_full.json 的最后一行是南海断续线的窄条面（name 为空）。
        # 它是**线**不是陆地，若参与栅格化会在台湾以东、南海画出一条
        # 细长"陆地"条带，被 _paper_overlay 涂成纸色（台湾图上那道竖线）。
        if "name" in cn.columns:
            keep = cn["name"].notna() & (cn["name"].astype(str).str.strip() != "")
            cn = cn[keep]
        geoms += list(cn.geometry)
    base = os.path.join(DATA, "boundaries", "natural_earth")
    for fp in (os.path.join(base, "ne_50m", "ne_50m_admin_0_countries.shp"),
               os.path.join(base, "ne_50m_admin_0_countries.geojson"),
               os.path.join(base, "ne_50m_admin_0_countries.shp")):
        if os.path.exists(fp):
            geoms += list(gpd.read_file(fp).to_crs(ALBERS).geometry)
            break
    _LAND_LAYERS["g"] = geoms
    return geoms


def china_solid():
    """中国省级政区并集，并**填掉内部空洞**的一整块面（Albers）。

    DataV 数据里内蒙古境内有一块归属不明的空洞（加格达奇—松岭一带，
    黑龙江实际管辖、图上却既不算内蒙古也不算黑龙江），内蒙古图上
    表现为一块纯白缺口。这里用「只取外环」的简化面兜住这类缝隙。
    """
    if "c" in _LAND_LAYERS:
        return _LAND_LAYERS["c"]
    import geopandas as gpd
    from shapely.geometry import MultiPolygon, Polygon
    cp = os.path.join(DATA, "boundaries", "datav", "100000_full.json")
    if not os.path.exists(cp):
        _LAND_LAYERS["c"] = None
        return None
    cn = gpd.read_file(cp).to_crs(ALBERS)
    if "name" in cn.columns:
        keep = cn["name"].notna() & (cn["name"].astype(str).str.strip() != "")
        cn = cn[keep]
    u = safe_union(cn)
    if u is None:
        _LAND_LAYERS["c"] = None
        return None
    if u.geom_type == "Polygon":
        u = Polygon(u.exterior)
    elif u.geom_type == "MultiPolygon":
        u = MultiPolygon([Polygon(p.exterior) for p in u.geoms])
    _LAND_LAYERS["c"] = u
    return u


def raster_land(h, w, tf, union):
    """在图幅网格上栅格化「陆地」掩膜（政区 + 中国 + 邻国）。"""
    from rasterio.features import rasterize
    geoms = [union, china_solid()] + land_layers()
    try:
        m = rasterize([(g, 1) for g in geoms if g is not None and not g.is_empty],
                      out_shape=(h, w), transform=tf, fill=0, dtype="uint8")
        return m.astype(bool)
    except Exception:
        return None


def raster_china(h, w, tf):
    """中国境内掩膜（用于区分「邻省」与「境外陆地」）。

    省级图幅是矩形的，四角往往落在邻国境内；若把整块陆地都涂成纸色，
    图上就会出现一个与页面不同色的米白矩形（新疆图最明显）。
    """
    from rasterio.features import rasterize
    c = china_solid()
    if c is None or c.is_empty:
        return None
    try:
        m = rasterize([(c, 1)], out_shape=(h, w), transform=tf,
                      fill=0, dtype="uint8")
        return m.astype(bool)
    except Exception:
        return None


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

    paths, missing = {}, []
    with ThreadPoolExecutor(max_workers=16) as ex:
        futs = {(tx, ty): ex.submit(fetch, tx, ty)
                for ty in range(y0, y1 + 1) for tx in range(x0, x1 + 1)}
        for k, fu in futs.items():
            p = fu.result()
            if p:
                paths[k] = p
            else:
                # 旧实现静默跳过失败的瓦片，mosaic 该处保留 np.zeros 初值，
                # 结果在成图上表现为"海拔 0 m"的绿色矩形块（宁夏中部即如此）。
                missing.append(k)
    if missing:
        raise RuntimeError(
            f"{adcode} 有 {len(missing)} 个 DEM 瓦片下载失败（示例 {missing[:4]}），"
            f"已中止缓存写入，请重试")

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
    prov_u = safe_union(_raw)
    geoms = [prov_u]
    china_path = os.path.join(DATA, "boundaries", "datav", "100000_full.json")
    if os.path.exists(china_path):
        china = gpd.read_file(china_path).to_crs(ALBERS)
        geoms += list(china.geometry)
    world_path = os.path.join(DATA, "boundaries", "natural_earth", "ne_50m", "ne_50m_admin_0_countries.shp")
    if os.path.exists(world_path):
        world = gpd.read_file(world_path).to_crs(ALBERS)
        geoms += list(world.geometry)
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
