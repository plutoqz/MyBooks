"""下册地图索引、图例、时序统计图与导出排版。"""
import json
import math
import re
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from matplotlib.text import Annotation, Text

from volume1_layout import wrap_text

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "下册修订"
QA = OUT / "qa"
SAVE = Figure.savefig
PALETTE = ["#B23A38", "#246E9D", "#278266", "#85509B", "#B37A10",
           "#56616A", "#B14C82", "#177F88", "#73563B", "#596D28"]
MARKERS = ["s", "o", "D", "h", "^", "v", "p", "P", "<", ">"]
ACTIVE_NAMES = set()
BADGE_MARKERS = {"*": "s", "P": "h", "X": "D", "x": "D", "+": "D"}
CATEGORY_NAMES = {
    "science": "科技创新", "auto": "汽车制造", "manu": "先进制造",
    "energy": "能源产业", "digital": "数字产业", "pharma": "生物医药",
    "industry": "工业基地", "tech": "科技园区", "eco": "生态保育",
    "wetland": "湿地", "agri": "农业", "culture": "文化遗产",
    "heritage": "历史遗产", "tourism": "旅游", "scenic": "自然名胜",
    "cbd": "商务中心", "chem": "化工产业", "petro": "石油化工",
    "logistics": "物流枢纽", "water": "水源与水利", "education": "教育科研",
    "univ": "高等院校", "medical": "医疗科研", "mining": "矿业",
    "port": "港口", "rail": "铁路", "airport": "机场", "newtown": "新城",
    "mt": "山脉与山地", "peak": "山峰", "peak_max": "最高峰",
    "nature": "自然保护区", "sea": "海洋生态", "forest": "森林生态",
    "core": "核心城市", "node": "节点城市", "sub": "区域副中心",
    "it": "电子信息", "marine": "海洋产业", "med": "医药产业",
    "mfg": "制造业", "zone": "重点园区", "tower": "城市天际地标",
    "caz": "中央活动区", "hub": "交通枢纽", "lead": "重点城区",
    "trans": "交通门户", "bio": "生物医药", "fin": "金融服务",
    "trade": "商贸流通", "biomed": "生物医药",
    "city": "城市驻地", "pref": "州府驻地",
}


def node(fig, ax, x, y, name, kind="", marker="o", color="#246E9D", note=""):
    if not hasattr(fig, "_v2_nodes"):
        fig._v2_nodes = []
    fig._v2_nodes.append(dict(ax=ax, x=float(x), y=float(y), name=str(name),
                              kind=kind, marker=marker, color=mpl.colors.to_hex(color), note=note))


def symbol_flush(self):
    import mapkit
    handles = []
    entries = []
    transport_styles = {
        "rail": ("铁路客运与货运站", "o", "#246E9D"),
        "airport": ("机场", "D", "#177F88"),
        "port": ("港口与码头", "h", "#85509B"),
        "bridge": ("桥梁", "^", "#B37A10"),
        "corridor": ("交通通道控制点", "v", "#56616A"),
    }
    for item in self.items:
        original_style = mapkit.SYMBOL_KINDS[item["kind"]]
        key = None
        if (any(word in original_style["label"] for word in ["交通", "枢纽", "机场", "港", "铁路", "走廊"])
                or item["kind"] in {"station", "rail_hub", "airport", "port", "corridor", "dryport"}):
            name = item["name"]
            if "机场" in name:
                key = "airport"
            elif "港" in name or "码头" in name:
                key = "port"
            elif "桥" in name:
                key = "bridge"
            elif "站" in name:
                key = "rail"
            elif "路" in name or "线" in name:
                key = "corridor"
        kind = f"transport-{key}" if key else item["kind"]
        entries.append((kind, item, transport_styles.get(key)))
    kinds = list(dict.fromkeys(kind for kind, _, _ in entries))
    category_styles = {}
    for index, kind in enumerate(kinds):
        color, marker = PALETTE[index % len(PALETTE)], MARKERS[index % len(MARKERS)]
        subset = [(item, replacement) for key, item, replacement in entries if key == kind]
        label = mapkit.SYMBOL_KINDS[subset[0][0]["kind"]]["label"]
        if subset[0][1]:
            label, marker, color = subset[0][1]
        elif any(mapkit.SYMBOL_KINDS[item["kind"]]["label"] == label
                 for key, item, replacement in entries if key != kind and replacement is None):
            label = CATEGORY_NAMES.get(kind, label)
        if label in category_styles:
            marker, color = category_styles[label]
        else:
            category_styles[label] = marker, color
        handles.append(Line2D([], [], marker=marker, color=color, ls="none",
                              markersize=8, label=label))
        for item, _ in subset:
            node(self.fig, self.ax, item["x"], item["y"], item["name"],
                 label, marker, color, item["note"])
    self.dropped = []
    return handles, []


def placer_flush(self):
    self.placed = []
    for item in self.items:
        node(self.fig, self.ax, item["x"], item["y"], item["text"],
             "地形与水文节点", item["marker"] or "^", item["mcolor"])


def collect_legends(ax, groups, **kwargs):
    fig = ax.figure
    if not hasattr(fig, "_v2_legends"):
        fig._v2_legends = []
    for group in groups:
        if "编号" not in group.get("title", "") and "索引" not in group.get("title", ""):
            fig._v2_legends.extend(group["handles"])
    return None


def collect_footer(ax, legend, text, **kwargs):
    if not hasattr(ax.figure, "_v2_footers"):
        ax.figure._v2_footers = []
    ax.figure._v2_footers.append(text)


def collect_scale(ax, x0, y0, length_km=5, **kwargs):
    ax._v2_scale = length_km


def collect_compass(ax, *args, **kwargs):
    ax._v2_compass = True


def all_axes(fig):
    result = []

    def visit(ax):
        result.append(ax)
        for child in ax.child_axes:
            visit(child)

    for ax in fig.axes:
        visit(ax)
    return result


def _footers(fig):
    result = list(getattr(fig, "_v2_footers", []))
    for text in list(fig.texts):
        value = text.get_text()
        if re.search(r"数据|来源|制作|投影", value):
            result.append(value)
        text.remove()
    normalized = []
    for value in result:
        if "夜光" in value or "夜间灯光" in value:
            value = re.sub(r"1986\s*[—–-]\s*2024", "1986—2013", value)
        normalized.append(value)
    return list(dict.fromkeys(normalized))


def _external_labels(fig, axes, title):
    largest = max(ax.get_position().width * ax.get_position().height for ax in axes)
    for ax in axes:
        for text in list(ax.texts):
            value = text.get_text().strip()
            if not value:
                text.remove()
                continue
            if value == "N":
                if isinstance(text, Annotation) and text.arrow_patch:
                    text.arrow_patch.set_visible(False)
                text.remove()
                ax._v2_compass = True
                continue
            if value == title or (not re.search(r"[\u4e00-\u9fff]", value)
                                  and len(value) > 30
                                  and not isinstance(text, Annotation)):
                text.remove()
                continue
            if text.get_transform() == ax.transAxes:
                if text.get_position()[1] > 0.95 and not re.search(r"[\u4e00-\u9fff]", value):
                    text.remove()
                elif ax.get_position().width * ax.get_position().height > largest * 0.25:
                    if not hasattr(fig, "_v2_note_handles"):
                        fig._v2_note_handles = []
                    fig._v2_note_handles.append(Line2D([], [], color="none",
                                                       ls="none", label=value.replace("\n", " ")))
                    text.remove()
                else:
                    if not hasattr(ax, "_v2_context_captions"):
                        ax._v2_context_captions = []
                    ax._v2_context_captions.append(value)
                    text.remove()
                continue
            if re.fullmatch(r"[\d.,]+\s*(km|m|米|千米)?", value):
                continue
            if isinstance(text, Annotation):
                if text.xycoords != "data":
                    continue
                x, y = text.xy
                if text.arrow_patch:
                    text.arrow_patch.set_visible(False)
            elif text.get_transform() == ax.transData:
                x, y = text.get_position()
            else:
                continue
            color, marker = "#246E9D", "o"
            nearest, distance = None, float("inf")
            anchor = ax.transData.transform((x, y))
            for line in ax.lines:
                if line.get_marker() in {"None", "none", "", " "}:
                    continue
                points = line.get_transform().transform_path(line.get_path()).vertices
                for point in points:
                    current = np.linalg.norm(point - anchor)
                    if current < distance:
                        nearest, distance = line, current
            if nearest is not None and distance < fig.dpi * 0.6:
                color, marker = nearest.get_markerfacecolor(), nearest.get_marker()
                if isinstance(color, str) and color in {"none", "auto"}:
                    color = nearest.get_color()
                if len(nearest.get_xdata()) == 1:
                    x, y = nearest.get_xdata()[0], nearest.get_ydata()[0]
            node(fig, ax, x, y, value.replace("\n", " "), "地理注记", marker, color)
            text.remove()


def _badges(fig, items):
    fig.canvas.draw()
    scale = fig.dpi / 72
    reserved = {}
    for index, item in enumerate(items, 1):
        ax = item["ax"]
        frame = ax.bbox
        insets = [other.bbox.padded(18 * scale) for other in fig.axes
                  if other is not ax and not hasattr(other, "_colorbar")
                  and other.bbox.width * other.bbox.height < frame.width * frame.height * 0.4]
        original = ax.transData.transform((item["x"], item["y"]))
        occupied = reserved.setdefault(ax, [])
        chosen = None
        radius = 12 * scale
        for ring in range(35):
            distance = ring * 14 * scale
            for angle in range(0, 360, 30):
                point = original + distance * np.array(
                    [math.cos(math.radians(angle)), math.sin(math.radians(angle))])
                x, y = point
                if not (frame.x0 + radius < x < frame.x1 - radius
                        and frame.y0 + radius < y < frame.y1 - radius):
                    continue
                if (ax is max(fig.axes, key=lambda a: a.bbox.width * a.bbox.height)
                        and x > frame.x1 - frame.width * 0.11
                        and y > frame.y1 - frame.height * 0.18):
                    continue
                if any(box.x0 - radius <= x <= box.x1 + radius
                       and box.y0 - radius <= y <= box.y1 + radius for box in insets):
                    continue
                if all(np.linalg.norm(point - prior) >= 26 * scale for prior in occupied):
                    chosen = point
                    break
            if chosen is not None:
                break
        if chosen is None:
            raise ValueError(f"地图编号放不下：{item['name']}")
        occupied.append(chosen)
        x, y = ax.transData.inverted().transform(chosen)
        distance = np.linalg.norm(chosen - original)
        if distance > 14 * scale:
            endpoint = original + (chosen - original) * (1 - 13 * scale / distance)
            end = ax.transData.inverted().transform(endpoint)
            ax.plot([item["x"], end[0]], [item["y"], end[1]],
                    color="#5F666B", lw=0.55, zorder=40, rasterized=True)
            ax.plot(item["x"], item["y"], ".", color=item["color"], ms=3,
                    zorder=41, rasterized=True)
        marker = BADGE_MARKERS.get(item["marker"], item["marker"])
        ax.plot(x, y, marker=marker, ms=27 if marker in {"^", "v", "<", ">"} else 23,
                color=item["color"], mew=0, ls="none", zorder=42)
        tx, ty = chosen
        ty += (-3 if marker == "^" else 3 if marker == "v" else 0) * scale
        tx += (3 if marker == "<" else -3 if marker == ">" else 0) * scale
        ax.text(*ax.transData.inverted().transform((tx, ty)), str(index),
                fontsize=9, color="white", weight="bold", ha="center", va="center", zorder=43)
        item["number"] = index
        item["badge_xy"] = list(map(float, ax.transData.inverted().transform(chosen)))


def map_layout(fig, filename):
    footers = _footers(fig)
    for old in all_axes(fig):
        colorbar = getattr(old, "_colorbar", None)
        if colorbar is not None:
            mappable = colorbar.mappable
            ticks = colorbar.get_ticks()
            label = (old.get_ylabel() if colorbar.orientation == "vertical"
                     else old.get_xlabel()) or old.get_title()
            if getattr(mappable, "axes", None) is None:
                colorbar._ax_remove(old)
                mappable.callbacks.disconnect(mappable.colorbar_cid)
                mappable.colorbar = None
                mappable.colorbar_cid = None
            else:
                colorbar.remove()
            replacement = fig.add_axes([0.1, 0.05, 0.35, 0.02])
            new_colorbar = fig.colorbar(mappable, cax=replacement,
                                        orientation="horizontal", ticks=ticks)
            replacement.set_title(label, fontsize=8)
    maps = [ax for ax in all_axes(fig) if not hasattr(ax, "_colorbar")]
    if not maps:
        return
    main = max(maps, key=lambda ax: ax.get_position().width * ax.get_position().height)
    title = main.get_title() or Path(filename).stem.split("_", 1)[-1]
    fig.canvas.draw()
    for text in main.texts:
        if (not isinstance(text, Annotation) and text.get_fontsize() >= 10.5
                and len(text.get_text()) > 12
                and text.get_transform() == main.transData):
            position = main.transAxes.inverted().transform(
                main.transData.transform(text.get_position()))
            if position[1] > 0.95:
                title = text.get_text()
                break
    handles = list(getattr(fig, "_v2_legends", []))
    for ax in maps:
        ax.set_axes_locator(None)
        boxes = [p for p in ax.patches if isinstance(p, Rectangle)
                 and p.get_zorder() >= 20 and p.get_facecolor()[:3] == (1, 1, 1)
                 and p.get_width() > 0 and p.get_height() > 0]
        for box in boxes:
            left, bottom_y = box.get_xy()
            right, top_y = left + box.get_width(), bottom_y + box.get_height()
            for text in list(ax.texts):
                x, y = text.get_position()
                if text.get_zorder() >= box.get_zorder() and left <= x <= right and bottom_y <= y <= top_y:
                    value = text.get_text()
                    if "图例" not in value:
                        marks = [line for line in ax.lines if len(line.get_xdata()) == 1
                                 and line.get_zorder() >= box.get_zorder()
                                 and left <= line.get_xdata()[0] <= right]
                        fills = [patch for patch in ax.patches
                                 if isinstance(patch, Rectangle) and patch is not box
                                 and patch.get_zorder() >= box.get_zorder()
                                 and left <= patch.get_x() <= right]
                        objects = ([(abs(line.get_ydata()[0] - y), line) for line in marks]
                                   + [(abs(patch.get_y() + patch.get_height() / 2 - y), patch)
                                      for patch in fills])
                        if objects:
                            closest = min(objects, key=lambda pair: pair[0])[1]
                            if isinstance(closest, Line2D):
                                handle = Line2D([], [], color=closest.get_color(),
                                                marker=closest.get_marker(), ls="none",
                                                label=value)
                            else:
                                handle = Patch(facecolor=closest.get_facecolor(),
                                               edgecolor=closest.get_edgecolor(), label=value)
                            handles.append(handle)
                    text.remove()
            for line in list(ax.lines):
                if line.get_zorder() >= box.get_zorder() and len(line.get_xdata()) == 1:
                    x, y = line.get_xdata()[0], line.get_ydata()[0]
                    if left <= x <= right and bottom_y <= y <= top_y:
                        line.remove()
            for patch in list(ax.patches):
                if patch.get_zorder() < box.get_zorder() or not isinstance(patch, Rectangle):
                    continue
                x, y = patch.get_xy()
                if left <= x <= right and bottom_y <= y <= top_y:
                    patch.remove()
    for legend in list(fig.legends) + [ax.get_legend() for ax in maps if ax.get_legend()]:
        handles.extend(getattr(legend, "legend_handles", []))
        legend.remove()
    if re.match(r"fig\d{2}-(?!00)\d{2}-3_", filename):
        from matplotlib.collections import LineCollection
        routes = any(len(line.get_xdata()) >= 2 for ax in maps for line in ax.lines)
        routes |= any(isinstance(collection, LineCollection)
                      and len(collection.get_segments()) > 50
                      for ax in maps for collection in ax.collections)
        if not routes:
            name = filename.split("_", 1)[1].replace("道路交通图.png", "")
            title = f"{name}交通枢纽与通道节点图"
            handles = [handle for handle in handles
                       if not isinstance(handle, Line2D)
                       or handle.get_marker() not in {"None", "none", "", " "}]
    _external_labels(fig, maps, title)
    handles.extend(getattr(fig, "_v2_note_handles", []))
    items = list(getattr(fig, "_v2_nodes", []))
    # 相同名称与坐标只列一次；同址不同地点全部保留。
    unique = []
    for item in items:
        if not any(item["ax"] is old["ax"] and item["name"] == old["name"]
                   and abs(item["x"] - old["x"]) < 0.01
                   and abs(item["y"] - old["y"]) < 0.01 for old in unique):
            unique.append(item)
    items = unique
    detailed_inset = any(item["ax"] is not main for item in items)
    has_insets = len(maps) > 1
    columns = 3
    rows = math.ceil(len(items) / columns)
    labels = [wrap_text(
        f"{i + 1:02d}  {item['name']}" + (f"（{item['note']}）" if item["note"] else ""),
        25) for i, item in enumerate(items)]
    row_heights = [
        max([len(labels[col * rows + row].splitlines())
             for col in range(columns) if col * rows + row < len(labels)] or [1]) * 12 + 5
        for row in range(rows)]
    index_h = sum(row_heights) + 24 if items else 0
    clean_handles = []
    seen = set()
    for handle in handles:
        label = handle.get_label()
        if not label or label.startswith("_") or re.match(r"\d+\s", label) or label in seen:
            continue
        seen.add(label)
        handle.set_label(wrap_text(label, 28))
        if isinstance(handle, Line2D):
            handle.set_marker(BADGE_MARKERS.get(handle.get_marker(), handle.get_marker()))
        clean_handles.append(handle)
    legend_rows = math.ceil(len(clean_handles) / 2)
    legend_h = 0
    if clean_handles:
        legend_h = 12 + sum(
            max(len(clean_handles[index].get_label().splitlines())
                for index in [row, row + legend_rows] if index < len(clean_handles)) * 12 + 9
            for row in range(legend_rows))
    colorbars = [ax for ax in fig.axes if hasattr(ax, "_colorbar")]
    for ax in colorbars:
        colorbar = ax._colorbar
        ticks = np.linspace(colorbar.norm.vmin, colorbar.norm.vmax, 5)
        colorbar.set_ticks(ticks)
        colorbar.set_ticklabels([f"{tick:g}" for tick in ticks])
    cbar_h = 46 if colorbars else 0
    footer_lines = [wrap_text(value, 90) for value in footers]
    footer_h = sum(len(s.splitlines()) for s in footer_lines) * 11 + 16
    aspect = abs(np.diff(main.get_ylim())[0] / np.diff(main.get_xlim())[0])
    map_w = 10.0
    map_h = max(4.5, min(8.0, map_w * aspect))
    bottom = footer_h + index_h + legend_h + cbar_h + 30
    height_pt = bottom + map_h * 72 + 62
    fig.set_size_inches(10.8, height_pt / 72)
    for ax in maps:
        old = ax.get_position().frozen()
        if ax is main:
            ax.set_position([0.035, bottom / height_pt, 0.65 if has_insets else 0.93,
                             map_h * 72 / height_pt])
        else:
            populated = any(item["ax"] is ax for item in items)
            inset_height = 230 if populated else 100
            ax.set_position([0.71,
                             (bottom + map_h * 72 - inset_height - 10) / height_pt,
                             0.25, inset_height / height_pt])
            captions = list(getattr(ax, "_v2_context_captions", []))
            if ax.get_title():
                captions.append(ax.get_title())
            if captions:
                position = ax.get_position()
                fig.text(position.x0 + position.width / 2, position.y0 - 6 / height_pt,
                         wrap_text("；".join(dict.fromkeys(captions)), 22),
                         ha="center", va="top", fontsize=8, color="#28383F")
        ax.set_title("")
        ax.set_axis_off()
        for collection in ax.collections:
            collection.set_rasterized(True)
        for line in ax.lines:
            line.set_rasterized(True)
        for patch in ax.patches:
            patch.set_rasterized(True)
    fig.text(0.035, 1 - 12 / height_pt, wrap_text(title, 49),
             fontsize=14, weight="bold", va="top", color="#28383F")
    for i, ax in enumerate(colorbars):
        ax.set_position([0.52 + i * 0.42 / len(colorbars), (bottom - 24) / height_pt,
                         0.38 / len(colorbars), 9 / height_pt])
        ax.tick_params(labelsize=8)
        ax.set_title(ax.get_title(), fontsize=8, pad=3)
    if clean_handles:
        fig.legend(handles=clean_handles, loc="upper left",
                   bbox_to_anchor=(0.035, (footer_h + index_h + legend_h) / height_pt),
                   ncol=2, fontsize=8, frameon=False, columnspacing=2,
                   handlelength=2, labelspacing=0.75)
    top = footer_h + index_h
    if items:
        fig.text(0.04, top / height_pt, "地点与要素索引", fontsize=9, weight="bold", va="top")
        for i, label in enumerate(labels):
            col, row = divmod(i, rows)
            y = top - 20 - sum(row_heights[:row])
            fig.text(0.04 + col * 0.322, y / height_pt, label,
                     fontsize=8.5, color=items[i]["color"], va="top", linespacing=1.4)
    y = footer_h - 8
    for value in footer_lines:
        fig.text(0.035, y / height_pt, value, fontsize=8, va="top", color="#626B70")
        y -= len(value.splitlines()) * 11 + 3
    _badges(fig, items)
    fig.canvas.draw()
    # 比例尺使用最终图面变换，图例和索引的高度不会改变比例关系。
    length = getattr(main, "_v2_scale", None)
    if length:
        xlim = main.get_xlim()
        px = abs(main.transData.transform((xlim[0] + length * 1000, 0))[0]
                 - main.transData.transform((xlim[0], 0))[0])
        extent = px / fig.bbox.width
        if px / fig.dpi * 72 < 55 or extent > 0.45:
            desired = abs(xlim[1] - xlim[0]) / 1000 * 0.16
            magnitude = 10 ** math.floor(math.log10(desired))
            length = min([magnitude * k for k in (1, 2, 5, 10)],
                         key=lambda value: abs(value - desired))
            px = abs(main.transData.transform((xlim[0] + length * 1000, 0))[0]
                     - main.transData.transform((xlim[0], 0))[0])
            extent = px / fig.bbox.width
        if extent < 0.45:
            left = 0.055
            sy = (bottom - 15) / height_pt
            for i, color in enumerate(["#28383F", "white"]):
                fig.add_artist(Rectangle((left + i * extent / 2, sy),
                                          extent / 2, 4 / height_pt,
                                          transform=fig.transFigure, fc=color,
                                          ec="#28383F", lw=0.6))
            fig.text(left, sy - 4 / height_pt, "0", fontsize=8, va="top")
            fig.text(left + extent, sy - 4 / height_pt, f"{length:g} km",
                     fontsize=8, va="top", ha="center")
    # 指北针留在编号禁放区内。
    main.annotate("N", xy=(0.96, 0.95), xytext=(0.96, 0.88),
                  xycoords="axes fraction", ha="center", va="center",
                  fontsize=10, weight="bold",
                  arrowprops=dict(arrowstyle="-|>", color="#28383F", lw=1))
    serial = [{key: value for key, value in item.items() if key != "ax"} for item in items]
    (QA / f"{Path(filename).stem}.nodes.json").write_text(
        json.dumps(serial, ensure_ascii=False, indent=2), encoding="utf-8")


def chart_layout(fig, filename):
    """时序各自保留年份间隔和原始观测，不把夜光当成 GDP 的因果证据。"""
    from matplotlib.container import BarContainer
    original_axes = list(fig.axes)
    title = fig._suptitle.get_text() if fig._suptitle else Path(filename).stem.split("_", 1)[-1]
    title = re.sub(r"\s*[（(]?1986[—–-]2024\s*年?[）)]?", "", title)
    footers = _footers(fig)
    series, events, descriptions = [], [], []
    for ax in original_axes:
        panel = dict(title=ax.get_title(), ylabel=ax.get_ylabel(), xlabel=ax.get_xlabel(),
                     lines=[], bars=[])
        for container in ax.containers:
            if isinstance(container, BarContainer):
                horizontal = container.orientation == "horizontal"
                points = [(float(p.get_y() + p.get_height() / 2), float(p.get_width()))
                          if horizontal else
                          (float(p.get_x() + p.get_width() / 2), float(p.get_height()))
                          for p in container.patches]
                points = [(position, value if math.isfinite(value) else None)
                          for position, value in points]
                ticks = ax.get_yticklabels() if horizontal else ax.get_xticklabels()
                panel["bars"].append(dict(points=points, horizontal=horizontal,
                                           ticks=[t.get_text() for t in ticks],
                                           colors=[mpl.colors.to_hex(p.get_facecolor())
                                                   for p in container.patches]))
        for line in ax.lines:
            if len(line.get_xdata()) < 3:
                continue
            x = np.asarray(line.get_xdata(), dtype=float)
            y = np.asarray(line.get_ydata(), dtype=float)
            if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
                raise ValueError(f"图表存在非有限观测：{filename}")
            if panel["bars"]:
                continue
            panel["lines"].append(dict(x=x.tolist(), y=y.tolist(), label=line.get_label()))
        for text in ax.texts:
            if isinstance(text, Annotation):
                events.append(text.get_text().replace("\n", " "))
            elif (not re.fullmatch(r"[\d.,]+\s*(万)?", text.get_text().strip())
                  or re.fullmatch(r"(19|20)\d{2}", text.get_text().strip())):
                descriptions.append(text.get_text())
        if panel["bars"] or panel["lines"]:
            series.append(panel)
    if Path(filename).name.startswith("fig27-00-5_"):
        comparison = series.pop()
        metric_units = ["km²", "万人", "亿元人民币", "万 TEU"]
        for index, unit in enumerate(metric_units):
            metric = comparison["bars"][0]["ticks"][index].splitlines()[0]
            series.append(dict(
                title=f"2024 年{metric}对比", ylabel=unit, xlabel="",
                lines=[], bars=[dict(
                    points=[[group, bar["points"][index][1]]
                            for group, bar in enumerate(comparison["bars"])],
                    horizontal=False,
                    ticks=["香港特别行政区", "广东省深圳市"],
                    colors=[bar["colors"][index] for bar in comparison["bars"]])]))
    data = dict(name=Path(filename).name, title=title, footers=footers,
                panels=series, events=events, qualitative_notes=descriptions)
    (QA / f"{Path(filename).stem}.data.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return render_chart_data(data)


def render_chart_data(data):
    filename = data["name"]
    title = data.get("title", Path(filename).stem.split("_", 1)[-1])
    title = re.sub(r"\s*[（(]?1986[—–-]2024\s*年?[）)]?", "", title)
    footers = data.get("footers", [])
    series = data["panels"]
    events = data.get("events", [])
    descriptions = data.get("qualitative_notes", [])
    missing = []
    for panel in series:
        for bar in panel["bars"]:
            valid = [i for i, point in enumerate(bar["points"])
                     if point[1] is not None and math.isfinite(point[1])]
            for i, point in enumerate(bar["points"]):
                if i not in valid:
                    label = bar["ticks"][i] if len(bar["ticks"]) == len(bar["points"]) else str(point[0])
                    missing.append(f"{label}：原表没有独立观测值，未计入数值比较。")
            if len(valid) != len(bar["points"]):
                if len(bar["ticks"]) == len(bar["points"]):
                    bar["ticks"] = [bar["ticks"][i] for i in valid]
                if "colors" in bar:
                    bar["colors"] = [bar["colors"][i] for i in valid]
                bar["points"] = [bar["points"][i] for i in valid]
            if len(bar["points"]) > 12 and not all(1900 <= p[0] <= 2100 for p in bar["points"]):
                bar["horizontal"] = True
    descriptions = list(descriptions) + missing
    if not series:
        lines = [wrap_text(value, 70) for value in descriptions + events]
        height = (85 + sum(len(s.splitlines()) * 15 + 8 for s in lines)) / 72
        new = plt.figure(figsize=(10.6, max(3, height)))
        heading = re.sub(r"卫星夜间灯光|夜间灯光|夜光", "空间发展阶段", title)
        new.text(0.04, 0.96, wrap_text(heading, 47), fontsize=14,
                 weight="bold", va="top")
        y = new.get_figheight() * 72 - 65
        for value in lines:
            new.text(0.04, y / (new.get_figheight() * 72), value, fontsize=9,
                     va="top", color="#28383F")
            y -= len(value.splitlines()) * 15 + 8
        return new
    captions = list(dict.fromkeys(events + [
        s.replace("\n", " ") for s in descriptions if len(s) > 20]))
    # 所有事件文字保留于图外，不用配置中的注释高度充当观测值。
    event_lines = [wrap_text(note, 85) for note in captions]
    note_height = sum(len(s.splitlines()) for s in event_lines) * 16 + 35
    panel_heights = []
    for panel in series:
        categories = max([len(bar["points"]) for bar in panel["bars"]
                          if bar["horizontal"]] or [0])
        panel_heights.append(max(3.3, (categories * 22 + 100) / 72,
                                 (len(panel["lines"]) * 22 + 100) / 72))
    new = plt.figure(figsize=(10.6, sum(panel_heights) + (note_height + 45) / 72))
    total_h = new.get_figheight() * 72
    axes = new.subplots(len(series), 1, squeeze=False,
                        gridspec_kw=dict(height_ratios=panel_heights)).ravel()
    many_lines = any(len(panel["lines"]) > 3 for panel in series)
    new.subplots_adjust(left=0.13, right=0.72 if many_lines else 0.96, top=1 - 65 / total_h,
                        bottom=(note_height + 35) / total_h, hspace=0.55)
    for ax, panel in zip(axes, series):
        for i, line in enumerate(panel["lines"]):
            label = line["label"] if not line["label"].startswith("_") else None
            ax.plot(line["x"], line["y"], color=PALETTE[(i + 1) % 10],
                    linestyle=["-", "--", "-.", ":"][i % 4],
                    marker=["o", "s", "^", "D", "v", "P", "h", "p", "<", ">", "X"][i % 11],
                    lw=1.5, ms=3, label=label)
            ax.set_xlim(min(line["x"]) - 0.5, max(line["x"]) + 0.5)
        for i, bar in enumerate(panel["bars"]):
            points = bar["points"]
            x, y = np.array(points).T
            if bar["horizontal"]:
                artists = ax.barh(x, y, color=bar.get("colors", PALETTE[(i + 1) % 10]), height=0.62)
                if len(bar["ticks"]) == len(x):
                    ax.set_yticks(x, bar["ticks"], fontsize=9)
                ax.set_xlim(0, max(y) * 1.22)
                for mark, value in zip(artists, y):
                    label = ax.annotate(
                        f"{value:,.6f}".rstrip("0").rstrip("."),
                        xy=(value, mark.get_y() + mark.get_height() / 2),
                        xytext=(7, 0), textcoords="offset points",
                        va="center", ha="left", fontsize=8.5)
                    label._v2_value_orientation = "horizontal"
            else:
                categorical = not (len(x) and min(x) >= 1900 and max(x) <= 2100)
                gap = min(np.diff(sorted(set(x))), default=1)
                width = 0.62 if categorical else gap * 0.62
                artists = ax.bar(x, y, width=width, color=bar.get("colors", PALETTE[(i + 1) % 10]))
                if categorical and len(bar["ticks"]) == len(x):
                    ax.set_xticks(x, bar["ticks"])
                else:
                    ax.set_xticks(x, [f"{v:g}" for v in x])
                    if len(x) >= 7 and x[-1] - x[-3] <= 3:
                        ax.tick_params(axis="x", labelrotation=45)
                ax.set_ylim(0, max(y) * 1.2 if max(y) > 0 else 1)
                if not categorical:
                    panel["title"] = re.sub(
                        r"20\d{2}\s*[—–-]\s*20\d{2}",
                        f"{min(x):g}—{max(x):g}", panel["title"])
                for mark, value in zip(artists, y):
                    label = ax.annotate(
                        f"{value:,.6f}".rstrip("0").rstrip("."),
                        xy=(mark.get_x() + mark.get_width() / 2, value),
                        xytext=(0, 7), textcoords="offset points",
                        ha="center", va="bottom", fontsize=8.5)
                    label._v2_value_orientation = "vertical"
        horizontal = any(bar["horizontal"] for bar in panel["bars"])
        ylabel = "" if horizontal else panel["ylabel"]
        numeric_label = (panel.get("xlabel") or panel["ylabel"]) if horizontal else ylabel
        if "夜光" in panel["title"] or "灯光" in panel["title"]:
            panel["title"] = re.sub(r"\s*[（(][^()（）]*DMSP[^()（）]*[）)]", "",
                                     panel["title"], flags=re.I)
            panel["title"] = re.sub(r"夜间灯光辐射总[值量]|夜光辐射总量|夜间灯光总辐射量",
                                     "汇编夜光指标总量", panel["title"])
            scale_text = ""
            if "百万" in numeric_label or "10⁶" in numeric_label:
                scale_text = " ÷ 10⁶"
            elif "万" in numeric_label or "10⁴" in numeric_label:
                scale_text = " ÷ 10⁴"
            elif "千" in numeric_label or "10³" in numeric_label:
                scale_text = " ÷ 10³"
            numeric_label = f"汇编夜光指标总量（原表 sum{scale_text}）"
            if not horizontal:
                ylabel = numeric_label
            years = [v for line in panel["lines"] for v in line["x"]]
            if years:
                panel["title"] = re.sub(r"1986[—–-]2024|1986[—–-]2013",
                                        f"{min(years):g}—{max(years):g}", panel["title"])
        ax.set_title(wrap_text(panel["title"], 48), fontsize=11, loc="left", pad=14)
        ax.set_ylabel(wrap_text(ylabel, 16), fontsize=9)
        ax.set_xlabel(numeric_label if horizontal else "年份" if any(
            min(line["x"]) > 1900 for line in panel["lines"])
                      or any(min(p[0] for p in bar["points"]) > 1900
                             for bar in panel["bars"]) else "", fontsize=9)
        ax.tick_params(labelsize=9)
        from matplotlib.ticker import ScalarFormatter
        numeric_axis = ax.xaxis if any(bar["horizontal"] for bar in panel["bars"]) else ax.yaxis
        formatter = ScalarFormatter(useOffset=False)
        formatter.set_scientific(False)
        numeric_axis.set_major_formatter(formatter)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(False)
        if len(panel["lines"]) > 1:
            ax.legend(fontsize=8, loc="upper left", frameon=False,
                      bbox_to_anchor=(1.02, 1), borderaxespad=0, labelspacing=0.7)
    new.text(0.05, 1 - 12 / total_h, wrap_text(title, 48),
             fontsize=14, weight="bold", va="top")
    cursor = note_height + 16
    for line in event_lines:
        new.text(0.05, cursor / total_h, line, fontsize=8.5, va="top", color="#4C565C")
        cursor -= len(line.splitlines()) * 13 + 3
    footer = "；".join(footers)
    new.text(0.05, 10 / total_h, wrap_text(footer, 92), fontsize=8,
             va="bottom", color="#626B70")
    return new


def space_chart_values(fig):
    """数值始终停留在本柱外侧；密集年份的标注只向外错开。"""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    scale = fig.dpi / 72
    for ax in fig.axes:
        labels = [text for text in ax.texts if hasattr(text, "_v2_value_orientation")]
        for _ in range(2):
            occupied = []
            for label in labels:
                horizontal = label._v2_value_orientation == "horizontal"
                for distance in range(7, 151, 12):
                    label.set_position((distance, 0) if horizontal else (0, distance))
                    box = label.get_window_extent(renderer).padded(2 * scale)
                    if not any(box.overlaps(prior) for prior in occupied):
                        occupied.append(box)
                        break
                else:
                    raise ValueError(f"柱状图数值没有足够空间：{label.get_text()}")
            vertical = [label for label in labels if label._v2_value_orientation == "vertical"]
            if vertical:
                height = ax.bbox.height / scale
                limits = []
                for label in vertical:
                    needed = label.get_position()[1] + label.get_window_extent(renderer).height / scale + 5
                    if needed >= height:
                        raise ValueError("柱状图面板高度不足")
                    limits.append(label.xy[1] / (1 - needed / height))
                lower, upper = ax.get_ylim()
                if limits and max(limits) > upper:
                    ax.set_ylim(lower, max(limits))
            else:
                width = ax.bbox.width / scale
                limits = []
                for label in labels:
                    needed = label.get_position()[0] + label.get_window_extent(renderer).width / scale + 5
                    if needed >= width:
                        raise ValueError("横向柱图面板宽度不足")
                    limits.append(label.xy[0] / (1 - needed / width))
                lower, upper = ax.get_xlim()
                if limits and max(limits) > upper:
                    ax.set_xlim(lower, max(limits))
            fig.canvas.draw()


def export_figure(fig, filename, **kwargs):
    name = Path(filename).name
    if name not in ACTIVE_NAMES:
        return
    target = OUT / "figures" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    for text in fig.findobj(Text):
        if text.get_fontsize() < 8:
            text.set_fontsize(8)
    time_chart = any(value in name for value in ["夜间灯光", "夜光演变", "经济总量与空间夜光"])
    is_map = not time_chart and (hasattr(fig, "_v2_nodes") or any(
        (not ax.axison or ax.images or ax.get_aspect() != "auto")
        and not hasattr(ax, "_colorbar") for ax in fig.axes))
    if is_map:
        map_layout(fig, name)
        rendered = fig
    else:
        rendered = chart_layout(fig, name)
        space_chart_values(rendered)
    tools = Path.home() / ".codex" / "skills" / "nature-figure" / "scripts"
    sys.path.insert(0, str(tools))
    from audit_panel_alignment import require_matplotlib_panel_alignment
    if not is_map:
        require_matplotlib_panel_alignment(
            rendered, json_out=str(QA / f"{target.stem}.alignment.json"),
            tolerance_pt=1.5, strict=True)
    for suffix in [".png", ".pdf", ".svg"]:
        SAVE(rendered, target.with_suffix(suffix), dpi=300,
             bbox_inches="tight", pad_inches=0.15)
    if rendered is not fig:
        plt.close(rendered)
    print(f"EXPORT {name}", flush=True)


def install(names):
    import mapkit
    import style
    ACTIVE_NAMES.update(names)
    QA.mkdir(parents=True, exist_ok=True)
    mpl.rcParams.update({"pdf.fonttype": 42, "svg.fonttype": "none",
                         "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
                         "axes.unicode_minus": False})
    style.FIGURES = str(OUT / "figures")
    style.DPI = 300
    mapkit.SymbolLabels.flush = symbol_flush
    mapkit.LabelPlacer.flush = placer_flush
    mapkit.stacked_legends = collect_legends
    mapkit.footer_below_legend = collect_footer
    mapkit.add_scalebar = collect_scale
    mapkit.add_compass = collect_compass
    Figure.savefig = export_figure
