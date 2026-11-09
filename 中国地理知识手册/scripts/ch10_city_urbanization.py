"""2024 年地级以上城市常住人口城镇化率分布。"""

import io
import json
import zipfile
from pathlib import Path

import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import openpyxl
import pandas as pd
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Patch
from pyproj import Transformer

from style import ALBERS, china_borders, draw_borders, load_china, setup
from volume1_layout import save_volume_figure
import volume1_layout

ROOT = Path(__file__).resolve().parents[1]
BOUNDARIES = ROOT / "data" / "boundaries" / "datav"
DATA = ROOT / "中国省市数据"
OUTPUT = ROOT / "output" / "上册修订"
FIGURE = "fig10-11_地级以上城市城镇化率.png"
MUNICIPALITIES = {110000, 120000, 310000, 500000}


def yearbook():
    archive_path = (
        DATA
        / "005.【出版年份】2025"
        / "中国城市统计年鉴2025（excel）【截面数据】.zip"
    )
    with zipfile.ZipFile(archive_path) as archive:
        name = next(name for name in archive.namelist() if "地级市" in name)
        workbook = openpyxl.load_workbook(
            io.BytesIO(archive.read(name)), read_only=True, data_only=True
        )
        rows = list(workbook.active.iter_rows(values_only=True))
    records = {}
    for row in rows[6:]:
        if not row[0] or not isinstance(row[4], (float, int)):
            continue
        name = str(row[0]).strip()
        if name in records:
            raise ValueError(f"年鉴城市名称重复：{name}")
        records[name] = {
            "常住人口_万人": row[2],
            "城镇化率_百分比": float(row[4]),
            "地区生产总值_亿元": row[17],
            "人均地区生产总值_元": row[19],
        }
    panel = openpyxl.load_workbook(
        DATA / "中国城市数据面板数据（2000-2024年）.xlsx",
        read_only=True,
        data_only=True,
    )
    codes = {}
    for row in panel["原始数据"].iter_rows(min_row=2, values_only=True):
        if row[0] != 2024 or row[2] not in records or row[4] is None:
            continue
        name = row[2]
        code = int(row[4])
        if code in codes:
            raise ValueError(f"城市代码重复：{code}")
        codes[code] = {"name": name, **records[name]}
    return codes


def administrative_units():
    china = load_china()
    provinces, dash = china_borders(china)
    frames = []
    for _, province in provinces.iterrows():
        code = int(province["adcode"])
        if code >= 710000:
            continue
        if code in MUNICIPALITIES:
            frame = gpd.GeoDataFrame([province], geometry="geometry", crs=china.crs)
        else:
            frame = gpd.read_file(BOUNDARIES / f"{code}_full.json")
        frame = frame[frame["name"].notna() & (frame["name"] != "")].copy()
        frame["province_name"] = province["name"]
        frames.append(frame[["adcode", "name", "province_name", "geometry"]])
    units = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs=china.crs)
    if units["adcode"].duplicated().any():
        raise ValueError("行政区代码重复")
    return provinces, dash, units


def main():
    setup()
    matplotlib.rcParams["pdf.fonttype"] = 42
    province, dash, units = administrative_units()
    values = yearbook()
    units["adcode"] = units["adcode"].astype(int)
    for _, row in units.iterrows():
        item = values.get(row["adcode"])
        if item and item["name"] != row["name"]:
            raise ValueError(f"行政代码与名称不一致：{row['adcode']}")
    units["urbanization"] = units["adcode"].map(
        lambda code: values[code]["城镇化率_百分比"] if code in values else np.nan
    )
    for column in ["常住人口_万人", "地区生产总值_亿元", "人均地区生产总值_元"]:
        units[column] = units["adcode"].map(
            lambda code: values[code][column] if code in values else None
        )
    matched = units["urbanization"].notna()
    if not matched.any():
        raise ValueError("没有可匹配的城市城镇化率")
    units.drop(columns="geometry").to_csv(
        OUTPUT / "qa" / "2024城市城镇化率数据.csv", index=False, encoding="utf-8-sig"
    )
    summary = {
        "boundary_units": int(len(units)),
        "matched_units": int(matched.sum()),
        "missing_units": int((~matched).sum()),
        "missing": units.loc[~matched, ["province_name", "name"]].to_dict("records"),
    }
    (OUTPUT / "qa" / "2024城市城镇化率范围.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False), flush=True)

    projected = units.to_crs(ALBERS)
    province = province.to_crs(ALBERS)
    dash = dash.to_crs(ALBERS)
    colors = ["#f0ead1", "#c7dfcb", "#8abca5", "#4a937f", "#28726e", "#b06543"]
    levels = [0, 40, 50, 60, 70, 80, 100.0001]
    cmap = ListedColormap(colors)
    norm = BoundaryNorm(levels, len(colors))
    fig = plt.figure(figsize=(11.5, 9.5))
    ax = fig.add_axes([0.03, 0.18, 0.94, 0.72])
    ax.set_aspect("equal")
    ax.set_axis_off()
    province.plot(ax=ax, color="#d8d9d7", edgecolor="none", zorder=0)
    projected.loc[matched].plot(
        ax=ax, column="urbanization", cmap=cmap, norm=norm,
        edgecolor="#ffffff", linewidth=0.16, zorder=1,
    )
    draw_borders(ax, province, dash, prov_lw=0.3, nat_lw=0.65)
    main = province[province["name"] != "海南省"]
    minx, miny, maxx, maxy = main.total_bounds
    ax.set_xlim(minx - 100000, maxx + 120000)
    ax.set_ylim(miny - 550000, maxy + 100000)
    inset = fig.add_axes([0.825, 0.20, 0.12, 0.23], facecolor="white")
    inset.set_aspect("equal")
    inset.set_xticks([])
    inset.set_yticks([])
    province.plot(ax=inset, color="#d8d9d7", edgecolor="#777777", linewidth=0.3)
    projected.loc[matched].plot(
        ax=inset, column="urbanization", cmap=cmap, norm=norm,
        edgecolor="#ffffff", linewidth=0.1,
    )
    dash.boundary.plot(ax=inset, color="#27343d", linewidth=0.6)
    transform = Transformer.from_crs("EPSG:4326", ALBERS, always_xy=True)
    corners = [transform.transform(lon, lat)
               for lon in (105, 125) for lat in (3, 25)]
    inset.set_xlim(min(x for x, _ in corners), max(x for x, _ in corners))
    inset.set_ylim(min(y for _, y in corners), max(y for _, y in corners))
    inset.set_xlabel("")
    inset.set_ylabel("")
    for spine in inset.spines.values():
        spine.set_edgecolor("#777777")
        spine.set_linewidth(0.5)
    fig.text(0.055, 0.955, "地级以上城市常住人口城镇化率", fontsize=17, weight="bold")
    fig.text(0.055, 0.915, "2024 年全市口径", fontsize=11, color="#4d5a5b")
    handles = [
        Patch(facecolor=colors[i], edgecolor="none", label=label)
        for i, label in enumerate(["低于 40%", "40%—50%", "50%—60%",
                                    "60%—70%", "70%—80%", "80% 及以上"])
    ]
    handles.append(Patch(facecolor="#d8d9d7", edgecolor="#aaa", label="无可比数据"))
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.115),
               ncol=4, frameon=False, fontsize=10)
    fig.text(
        0.055, 0.055,
        f"数据：中国城市统计年鉴 2025 表 2-1；匹配 {int(matched.sum())} 个单元。"
        "边界：DataV 2021.5；示意地图，不作为权属划界依据。",
        fontsize=8.5, color="#555555",
    )
    volume1_layout.OUTPUT_DIR = OUTPUT / "figures"
    volume1_layout.AUDIT_DIR = OUTPUT / "qa"
    save_volume_figure(fig, FIGURE)
    plt.close(fig)


if __name__ == "__main__":
    main()
