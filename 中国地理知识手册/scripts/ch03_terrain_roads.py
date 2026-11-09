"""河北省道路骨架高程分带及地形剖面。"""

import json
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from pyproj import Geod, Transformer
from rasterio.features import rasterize
from rasterio.transform import from_origin
from shapely import contains_xy

import volume1_layout
from style import ALBERS, load_china, setup
from volume1_layout import save_volume_figure

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "上册修订"
CLASSES = ["motorway", "trunk", "primary"]
BINS = [0, 200, 500, 1000, 100000]
LABELS = ["不足 200 m", "200—500 m", "500—1000 m", "1000 m 及以上"]


def main():
    setup()
    china = load_china()
    province = china[china["name"] == "河北省"].copy()
    province.geometry = province.geometry.make_valid().buffer(0)
    polygon = province.geometry.union_all()
    roads = gpd.read_file(
        ROOT / "data" / "transport" / "hebei" / "gis_osm_roads_free_1.shp",
        bbox=tuple(province.total_bounds),
        where="fclass IN ('motorway', 'trunk', 'primary')",
    )
    roads = gpd.clip(roads, polygon).explode(index_parts=False).reset_index(drop=True)
    roads = roads[roads.geometry.geom_type == "LineString"].copy()
    distance_roads = roads.to_crs("EPSG:32650")
    province_albers = province.to_crs(ALBERS)
    projected = roads.to_crs(ALBERS)
    cache = np.load(ROOT / "data" / "dem" / "china_dem_albers_z7.npz")
    dem, minx, maxy, resolution = (
        cache["dem"], float(cache["minx"]), float(cache["maxy"]), float(cache["res"]))
    transform = from_origin(minx, maxy, resolution, resolution)
    mask = rasterize([(province_albers.geometry.union_all(), 1)],
                     out_shape=dem.shape, transform=transform,
                     dtype="uint8").astype(bool)
    valid = mask & np.isfinite(dem)
    values = np.maximum(dem[valid], 0)
    area = np.histogram(values, bins=BINS)[0] * resolution ** 2 / 1e6
    to_dem = Transformer.from_crs("EPSG:32650", ALBERS, always_xy=True)

    def sample(x, y):
        cols = np.floor((np.asarray(x) - minx) / resolution).astype(int)
        rows = np.floor((maxy - np.asarray(y)) / resolution).astype(int)
        result = np.full(np.asarray(x).shape, np.nan)
        inside = ((rows >= 0) & (rows < dem.shape[0]) &
                  (cols >= 0) & (cols < dem.shape[1]))
        result[inside] = dem[rows[inside], cols[inside]]
        return result

    lengths = np.zeros(4)
    unobserved = 0.0
    for geometry in distance_roads.geometry:
        count = max(1, int(np.ceil(geometry.length / 900)))
        distances = (np.arange(count) + 0.5) * geometry.length / count
        points = [geometry.interpolate(float(d)) for d in distances]
        x, y = to_dem.transform([p.x for p in points], [p.y for p in points])
        elevation = sample(x, y)
        finite = np.isfinite(elevation)
        weight = geometry.length / count / 1000
        lengths += np.histogram(np.maximum(elevation[finite], 0), bins=BINS)[0] * weight
        unobserved += (~finite).sum() * weight
    result = pd.DataFrame(dict(
        elevation_band=LABELS, area_km2=area, road_km=lengths,
        area_share_percent=area / area.sum() * 100,
        road_share_percent=lengths / lengths.sum() * 100,
    ))
    result.to_csv(OUT / "qa" / "河北道路高程分带.csv", index=False, encoding="utf-8-sig")

    fig = plt.figure(figsize=(12.5, 9))
    grid = fig.add_gridspec(2, 2, width_ratios=[1.25, 1], hspace=0.42, wspace=0.24)
    ax_map = fig.add_subplot(grid[:, 0])
    min_px, min_py, max_px, max_py = province_albers.total_bounds
    col0 = max(0, int((min_px - minx) / resolution) - 4)
    col1 = min(dem.shape[1], int((max_px - minx) / resolution) + 5)
    row0 = max(0, int((maxy - max_py) / resolution) - 4)
    row1 = min(dem.shape[0], int((maxy - min_py) / resolution) + 5)
    image = dem[row0:row1, col0:col1].copy()
    image[~mask[row0:row1, col0:col1]] = np.nan
    height_colors = LinearSegmentedColormap.from_list(
        "height", ["#dbeacb", "#a4c292", "#c4b77b", "#91694b", "#f0f0ea"])
    relief = ax_map.imshow(
        image, extent=(minx + col0 * resolution, minx + col1 * resolution,
                       maxy - row1 * resolution, maxy - row0 * resolution),
        cmap=height_colors, vmin=0, vmax=2200, origin="upper", interpolation="nearest")
    colors = ["#922c3b", "#245e9c", "#5c4e91"]
    for road_class, color in zip(CLASSES, colors):
        projected[projected["fclass"] == road_class].plot(
            ax=ax_map, color=color, linewidth=0.45, label=road_class)
    province_albers.boundary.plot(ax=ax_map, color="#333333", linewidth=0.6)
    ax_map.set_axis_off()
    ax_map.set_title("河北省地形与 OSM 道路骨架", loc="left", fontsize=13)
    ax_map.legend(loc="upper left", frameon=True, facecolor="white", fontsize=9)
    ax_bar = fig.add_subplot(grid[0, 1])
    y = np.arange(4)
    ax_bar.barh(y - 0.17, result.area_share_percent, height=0.30,
                color="#79a595", label="省域有效栅格面积占比")
    ax_bar.barh(y + 0.17, result.road_share_percent, height=0.30,
                color="#8b4051", label="所选道路线长占比")
    ax_bar.set_yticks(y, LABELS)
    ax_bar.set_xlabel("占比（%）")
    ax_bar.set_title("同一高程带的面积与道路长度", loc="left", fontsize=12)
    ax_bar.legend(frameon=False, fontsize=8.5)
    ax_bar.invert_yaxis()

    ax_profile = fig.add_subplot(grid[1, 1])
    geod = Geod(ellps="WGS84")
    geographic_to_dem = Transformer.from_crs("EPSG:4326", ALBERS, always_xy=True)
    profiles = []
    for latitude, color in [(38.0, "#af6330"), (40.8, "#247d85")]:
        longitude = np.linspace(113.7, 119.3, 450)
        latitudes = np.full_like(longitude, latitude)
        x, y_coords = geographic_to_dem.transform(longitude, latitudes)
        elevation = sample(x, y_coords)
        elevation[~contains_xy(polygon, longitude, latitudes)] = np.nan
        step = geod.inv(longitude[:-1], latitudes[:-1], longitude[1:], latitudes[1:])[2]
        distance = np.r_[0, np.cumsum(step)] / 1000
        ax_profile.plot(distance, elevation, color=color, label=f"{latitude:g}°N")
        visible = np.isfinite(elevation)
        ax_map.plot(np.asarray(x)[visible], np.asarray(y_coords)[visible],
                    color=color, linewidth=1.1, linestyle="--")
        profiles.extend(dict(latitude=latitude, longitude=float(lon),
                             distance_km=float(d), elevation_m=float(z) if np.isfinite(z) else None)
                        for lon, d, z in zip(longitude, distance, elevation))
    ax_profile.set_xlabel("从 113.7°E 起沿纬线累计距离（km）", fontsize=9)
    ax_profile.set_ylabel("栅格高程（m）", fontsize=9)
    ax_profile.set_title("两条实际采样剖面", loc="left", fontsize=12)
    ax_profile.legend(frameon=False, fontsize=9)
    pd.DataFrame(profiles).to_csv(OUT / "qa" / "河北地形剖面.csv",
                                 index=False, encoding="utf-8-sig")
    fig.suptitle("地形与交通的空间关系：河北案例", x=0.07, ha="left",
                 fontsize=17, weight="bold")
    fig.subplots_adjust(top=0.90, bottom=0.14, left=0.04, right=0.97)
    colorbar_ax = fig.add_axes([0.07, 0.10, 0.37, 0.012])
    fig.colorbar(relief, cax=colorbar_ax, orientation="horizontal",
                 ticks=[0, 500, 1000, 1500, 2000])
    colorbar_ax.set_title("栅格高程（m）", fontsize=8.5, loc="left")
    fig.text(0.055, 0.055, "数据：本地 OSM 道路、DataV 2021.5 省界、Terrain Tiles 地形缓存（1800 m）。",
             fontsize=8.5, color="#555555")
    volume1_layout.OUTPUT_DIR = OUT / "figures"
    volume1_layout.AUDIT_DIR = OUT / "qa"
    save_volume_figure(fig, "fig3-18_河北地形与道路高程分带.png")
    plt.close(fig)
    report = dict(
        clipped_lines=len(roads), selected_classes=CLASSES, resolution_m=resolution,
        length_crs="EPSG:32650", dem_crs=ALBERS, sample_spacing_max_m=900,
        unobserved_road_km=unobserved, total_road_km=float(lengths.sum()),
        elevation_bands=result.to_dict("records"),
    )
    (OUT / "qa" / "河北地形交通专题结果.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
