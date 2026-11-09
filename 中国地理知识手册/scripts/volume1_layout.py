"""上册图件的物理尺寸、标题、脚注与导出。"""
import json
import os
import re
import sys
import math
from pathlib import Path

import matplotlib as mpl
from matplotlib.text import Text
from matplotlib.lines import Line2D
from matplotlib.patches import Wedge
from matplotlib.text import Annotation
from matplotlib.transforms import Bbox

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = None
AUDIT_DIR = None
KIND_STYLE = {
    "k": ("^", "#A84722", "山脉与地形区"),
    "r": ("D", "#2369A0", "河流"),
    "l": ("o", "#087E82", "湖泊"),
    "c": ("s", "#3E4652", "城市"),
    "m": ("h", "#8052A0", "主要矿产"),
    "p": ("p", "#A5660C", "陆路口岸"),
    "h": ("v", "#247859", "海港"),
    "mega": ("s", "#B63D32", "超大城市"),
    "huge": ("o", "#2369A0", "特大城市"),
    "cluster": ("o", "#2369A0", "城市群示意中心"),
    "keycity": ("o", "#B63D32", "重点城市／城区"),
    "quake": ("o", "#A7352C", "代表性强震（名称、年份、震级）"),
}


class NumberedMapIndex:
    """保留地理锚点，以异形符号、统一编号和分栏索引表达地图节点。"""

    def __init__(self):
        self.items = []

    def add(self, ax, kind, name, lon, lat, dot=None, dx=0, dy=0, leader=None):
        if dot == "star" and kind == "c":
            kind = "keycity"
        self.items.append(dict(ax=ax, kind=kind, name=name, lon=lon, lat=lat,
                               n=len(self.items) + 1, dx=dx, dy=dy, leader=leader))
        return len(self.items)

    def render(self, fig, bottom=0.045, fs=9.2, cols=2, top=0.165, chunk=5):
        if not self.items:
            return
        width, old_height = fig.get_size_inches()
        cols = 3
        fs = 9
        rows = math.ceil(len(self.items) / cols)
        index_height = (rows * 16 + 38) / 72
        fig.canvas.draw()
        positions = {ax: ax.get_position().frozen() for ax in fig.axes}
        map_bottom = min(pos.y0 for pos in positions.values()) * old_height
        # 索引与地图各有固定物理行距，条目增多时增加纸面高度。
        shift = index_height + 0.85 - map_bottom
        new_height = old_height + shift
        fig.set_size_inches(width, new_height)
        for ax, pos in positions.items():
            ax.set_position([pos.x0, (pos.y0 * old_height + shift) / new_height,
                             pos.width, pos.height * old_height / new_height])
        for text in fig.texts:
            x, y = text.get_position()
            text.set_position((x, (y * old_height + shift) / new_height))
        legend_y = (index_height + 0.63) / new_height
        kinds = list(dict.fromkeys(it["kind"] for it in self.items))
        handles = [
            Line2D([], [], marker=KIND_STYLE[k][0], color=KIND_STYLE[k][1],
                   linestyle="none", markersize=8, label=KIND_STYLE[k][2])
            for k in kinds
        ]
        fig.legend(handles=handles, loc="upper left",
                   bbox_to_anchor=(0.025, legend_y + 0.08 / new_height),
                   ncol=min(4, len(kinds)), frameon=False, fontsize=9)
        start = legend_y - (32 if len(kinds) > 4 else 20) / (new_height * 72)
        for i, item in enumerate(self.items):
            col, row = divmod(i, rows)
            x = 0.035 + col * 0.325
            y = start - row * 16 / (new_height * 72)
            fig.text(x, y, f'{item["n"]:02d}  {item["name"]}',
                     fontsize=fs, va="top", color=KIND_STYLE[item["kind"]][1])
        self._draw_badges(fig)
        fig._volume1_nodes = [
            {key: value for key, value in it.items() if key != "ax"}
            for it in self.items
        ]

    def _draw_badges(self, fig):
        from pyproj import Transformer
        from style import ALBERS
        transform = Transformer.from_crs("EPSG:4326", ALBERS, always_xy=True)
        fig.canvas.draw()
        pixels_per_pt = fig.dpi / 72
        occupied = {}
        anchors = {}
        for item in self.items:
            ax = item["ax"]
            xy = transform.transform(item["lon"], item["lat"])
            anchors.setdefault(ax, []).append(
                (item["n"], ax.transData.transform(xy)))
        for item in self.items:
            ax = item["ax"]
            box = ax.get_window_extent()
            point = transform.transform(item["lon"], item["lat"])
            px, py = ax.transData.transform(point)
            radius = 11 * pixels_per_pt
            placed = occupied.setdefault(ax, [])
            spot = None
            for ring in range(12):
                distance = ring * 19 * pixels_per_pt
                for angle in range(0, 360, 30):
                    qx = px + distance * math.cos(math.radians(angle))
                    qy = py + distance * math.sin(math.radians(angle))
                    if not (box.x0 + radius <= qx <= box.x1 - radius and
                            box.y0 + radius <= qy <= box.y1 - radius):
                        continue
                    if any(n != item["n"] and math.hypot(qx - p[0], qy - p[1])
                           < radius + 3 * pixels_per_pt for n, p in anchors[ax]):
                        continue
                    if all(math.hypot(qx - x, qy - y) > 2 * radius
                           for x, y in placed):
                        spot = qx, qy
                        break
                if spot:
                    break
            if spot is None:
                raise ValueError(f'编号没有可用空间：{item["name"]}')
            placed.append(spot)
            x, y = ax.transData.inverted().transform(spot)
            marker, color, _ = KIND_STYLE[item["kind"]]
            distance = math.hypot(spot[0] - px, spot[1] - py)
            if distance > radius:
                t = 1 - radius / distance
                end = ax.transData.inverted().transform(
                    (px + (spot[0] - px) * t, py + (spot[1] - py) * t)
                )
                ax.plot([point[0], end[0]], [point[1], end[1]],
                        color="#687078", lw=0.55, zorder=11)
                ax.plot(*point, marker=".", ms=2.5, color=color, zorder=11.5)
            ax.plot(x, y, marker=marker, ms=22 if marker in {"^", "v"} else 17,
                    color=color, mec="white", mew=0.7, zorder=12)
            text_y = ax.transData.inverted().transform(
                (spot[0], spot[1] + (-3 if marker == "^" else 3) * pixels_per_pt)
            )[1] if marker in {"^", "v"} else y
            ax.text(x, text_y, str(item["n"]), fontsize=8, color="white",
                    weight="bold", ha="center", va="center", zorder=13)


def wrap_text(text, max_em):
    lines = []
    for paragraph in text.splitlines():
        line, width = "", 0
        for char in paragraph:
            advance = 1 if ord(char) > 255 else 0.55
            if width + advance > max_em and line:
                lines.append(line)
                line, width = "", 0
            line += char
            width += advance
        lines.append(line)
    return "\n".join(lines)


def figure_name(filename):
    name = Path(filename).name
    if name.startswith("fig13-"):
        suffix = name.split("_", 1)[-1]
        matches = list((ROOT / "figures").glob(f"fig14-*_{suffix}"))
        if len(matches) == 1:
            name = matches[0].name
    return name


def _page_text(fig):
    width, height = fig.get_size_inches()
    headers = sorted(
        [t for t in fig.texts if t.get_visible() and t.get_position()[1] >= 0.90],
        key=lambda t: -t.get_position()[1],
    )
    footers = sorted(
        [t for t in fig.texts if t.get_visible() and t.get_position()[1] <= 0.04],
        key=lambda t: -t.get_position()[1],
    )
    cursor = height * 72 - 10
    for text in headers:
        fs = text.get_fontsize()
        text.set_text(wrap_text(text.get_text(), (width * 72 - 30) / fs))
        text.set_position((0.025, cursor / (height * 72)))
        text.set_ha("left")
        text.set_va("top")
        cursor -= fs * 1.4 * len(text.get_text().splitlines()) + 5
    bottom = 10
    for text in reversed(footers):
        fs = max(text.get_fontsize(), 8)
        text.set_fontsize(fs)
        text.set_text(wrap_text(text.get_text(), (width * 72 - 30) / fs))
        text.set_position((0.025, bottom / (height * 72)))
        text.set_ha("left")
        text.set_va("bottom")
        bottom += fs * 1.4 * len(text.get_text().splitlines()) + 4
    # 标题区和图表标题之间以最终文字范围留空。
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    if headers:
        ceiling = (cursor - 6) * fig.dpi / 72
        top_edge = max(ax.get_position().y1 for ax in fig.axes)
        delta = 0
        for ax in fig.axes:
            bb = ax.get_tightbbox(renderer)
            if bb is None or bb.y1 <= ceiling:
                continue
            delta = max(delta, (bb.y1 - ceiling) / fig.bbox.height)
        if delta:
            for ax in fig.axes:
                pos = ax.get_position()
                if abs(pos.y1 - top_edge) < 0.002:
                    ax.set_position([pos.x0, pos.y0, pos.width,
                                     max(0.08, pos.height - delta)])


def _pie_keys(fig):
    for ax in fig.axes:
        wedges = [patch for patch in ax.patches if isinstance(patch, Wedge)]
        if not wedges:
            continue
        legend = ax.get_legend()
        texts = list(ax.texts)
        percentages = [text.get_text() for text in texts
                       if re.fullmatch(r"\s*[\d.]+\s*%\s*", text.get_text())]
        count = len(wedges) + len(percentages)
        if legend:
            labels = [text.get_text() for text in legend.get_texts()]
            legend.remove()
        else:
            names = [wedge.get_label() for wedge in wedges]
            if not all(names):
                names = [text.get_text() for text in texts
                         if text.get_text() and text.get_text() not in percentages][:len(wedges)]
            if len(names) != len(wedges):
                raise ValueError("饼图扇区与类别名称数量不一致")
            labels = []
            for i, name in enumerate(names):
                pct = percentages[i] if i < len(percentages) else ""
                labels.append(name if not pct or pct in name else f"{name}  {pct}")
        for text in texts[:count]:
            text.remove()
        labels = [wrap_text(label, 23) for label in labels]
        columns = 2 if max(map(len, labels), default=0) < 20 else 1
        ax.legend(wedges, labels, loc="upper center", bbox_to_anchor=(0.5, -0.02),
                  ncol=columns, frameon=False, fontsize=8.5, handlelength=1.2)


def _chart_layout(fig):
    axes = [ax for ax in fig.axes if ax.axison]
    if not axes or any(ax.images for ax in axes):
        return
    if any(ax.get_subplotspec() is None for ax in axes):
        return
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    for ax in axes:
        for title in (ax.title, ax._left_title, ax._right_title):
            if title.get_text():
                max_em = ax.get_window_extent().width / fig.dpi * 72 / title.get_fontsize() * 0.9
                title.set_text(wrap_text(title.get_text(), max_em))
        legend = ax.get_legend()
        if legend and not any(isinstance(p, Wedge) for p in ax.patches):
            legend_box = legend.get_window_extent(renderer)
            if legend_box.width * legend_box.height > ax.bbox.width * ax.bbox.height * 0.22:
                legend.set_loc("upper center")
                legend.set_bbox_to_anchor((0.5, -0.24), transform=ax.transAxes)
        labels = ax.get_xticklabels()
        if not labels or not any(re.search(r"[\u4e00-\u9fff]", t.get_text())
                                 for t in labels):
            continue
        slot_pt = ax.get_window_extent().width / fig.dpi * 72 / max(len(labels), 1)
        if any(t.get_window_extent(renderer).width > slot_pt * fig.dpi / 72
               for t in labels):
            contents = [wrap_text(t.get_text(), max(3, slot_pt / t.get_fontsize() * 0.9))
                        for t in labels]
            ax.set_xticks(ax.get_xticks(), contents)
    header_bottom = 0.98
    footer_top = 0.025
    for text in fig.texts:
        box = text.get_window_extent(renderer)
        if text.get_position()[1] >= 0.85:
            header_bottom = min(header_bottom, box.y0 / fig.bbox.height - 0.025)
        elif text.get_position()[1] <= 0.06:
            footer_top = max(footer_top, box.y1 / fig.bbox.height + 0.025)
    fig.tight_layout(rect=(0.005, footer_top, 0.995, header_bottom),
                     h_pad=2.2, w_pad=3.0)
    # 条端长说明需要真实的数据轴留白，避免伸入相邻面板。
    for _ in range(2):
        fig.canvas.draw()
        for ax in axes:
            if ax.get_xscale() != "linear":
                continue
            if not any(getattr(container, "orientation", "") == "horizontal"
                       for container in ax.containers):
                continue
            right = ax.get_window_extent().x1
            overflow = max((text.get_window_extent(renderer).x1 - right
                            for text in ax.texts if text.get_visible()), default=0)
            if overflow > 1:
                lower, upper = ax.get_xlim()
                ax.set_xlim(lower, upper + (upper - lower) * (
                    overflow + 10) / ax.get_window_extent().width * 1.3)
            left = ax.get_window_extent().x0
            left_overflow = max((left - text.get_window_extent(renderer).x0
                                 for text in ax.texts if text.get_visible()), default=0)
            if left_overflow > 1:
                lower, upper = ax.get_xlim()
                ax.set_xlim(lower - (upper - lower) * (
                    left_overflow + 10) / ax.get_window_extent().width * 1.3, upper)


def _space_labels(fig):
    """仅移动发生碰撞的图内文字，以物理距离避让并保留指向关系。"""
    from shapely.geometry import LineString, box as rectangle
    from matplotlib.collections import PathCollection
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    scale = fig.dpi / 72
    groups = {}
    for ax in fig.axes:
        if not ax.axison:
            continue
        texts = [text for text in ax.texts if text.get_visible() and text.get_text()]
        if not texts:
            continue
        strokes = []
        marker_boxes = []
        marker_points = []
        for line in ax.lines:
            if not line.get_visible():
                continue
            points = line.get_transform().transform_path(line.get_path()).vertices
            if line.get_linestyle() not in {"None", "none", "", " "} and len(points) >= 2:
                strokes.append(LineString(points))
            if line.get_marker() not in {"None", "none", "", " "}:
                radius = (line.get_markersize() / 2 + 2) * scale
                for px, py in points:
                    marker_boxes.append(Bbox.from_extents(
                        px - radius, py - radius, px + radius, py + radius))
        for patch in list(ax.patches) + list(ax.spines.values()):
            if (not patch.get_visible() or patch.get_linewidth() == 0
                    or patch.get_edgecolor()[-1] == 0 or isinstance(patch, Wedge)):
                continue
            points = patch.get_transform().transform_path(patch.get_path()).interpolated(12).vertices
            if len(points) >= 2:
                strokes.append(LineString(points))
        for collection in ax.collections:
            if not isinstance(collection, PathCollection):
                continue
            offsets = collection.get_offset_transform().transform(collection.get_offsets())
            sizes = collection.get_sizes()
            radius = max(math.sqrt(max(sizes, default=16)) / 2 + 2, 4) * scale
            for px, py in offsets:
                marker_boxes.append(Bbox.from_extents(px - radius, py - radius,
                                                      px + radius, py + radius))
                marker_points.append((px, py))
        key = tuple(round(v, 3) for v in ax.get_position().bounds)
        occupied = groups.setdefault(key, [])
        occupied.extend(marker_boxes)
        for label in ([ax.title, ax._left_title, ax._right_title,
                       ax.xaxis.label, ax.yaxis.label]
                      + ax.get_xticklabels() + ax.get_yticklabels()):
            if label.get_visible() and label.get_text():
                occupied.append(label.get_window_extent(renderer).padded(scale))
        legend = ax.get_legend()
        if legend:
            occupied.append(legend.get_window_extent(renderer).padded(3 * scale))
        for text in texts:
            # 编号位于实心符号内部，由地图索引的节点间距独立控制。
            if hasattr(fig, "_volume1_nodes") and text.get_color() == "white":
                continue
            original = Text.get_window_extent(text, renderer=renderer)
            padded = original.padded(2 * scale)
            def clear(box):
                if any(box.overlaps(other) for other in occupied):
                    return False
                interior = rectangle(box.x0 + scale, box.y0 + scale,
                                     box.x1 - scale, box.y1 - scale)
                return not any(line.intersects(interior) for line in strokes)
            if clear(padded):
                occupied.append(padded)
                continue
            transform = text.get_transform()
            position = transform.transform(text.get_position())
            chosen = None
            orientations = {getattr(c, "orientation", "") for c in ax.containers}
            angles = (90, 270, 0, 180, 45, 135, 315, 225)
            if re.match(r"^[+\-−]?\d", text.get_text()):
                if "horizontal" in orientations:
                    angles = (0, 180)
                elif "vertical" in orientations:
                    angles = (90, 270)
            for radius in (4, 8, 13, 20, 30, 44, 60):
                for angle in angles:
                    dx = radius * scale * math.cos(math.radians(angle))
                    dy = radius * scale * math.sin(math.radians(angle))
                    candidate = Bbox.from_extents(
                        padded.x0 + dx, padded.y0 + dy,
                        padded.x1 + dx, padded.y1 + dy)
                    if (candidate.x0 < 6 * scale or
                            candidate.x1 > fig.bbox.width - 6 * scale or
                            candidate.y0 < 12 * scale or
                            candidate.y1 > fig.bbox.height - 12 * scale):
                        continue
                    if clear(candidate):
                        chosen = dx, dy, candidate
                        break
                if chosen:
                    break
            if chosen is None:
                occupied.append(padded)
                continue
            dx, dy, candidate = chosen
            new_position = transform.inverted().transform(position + (dx, dy))
            text.set_position(new_position)
            occupied.append(candidate)
            if (not isinstance(text, Annotation) and (ax.images or marker_points)
                    and text.get_bbox_patch() is None and abs(text.get_rotation()) < 1
                    and math.hypot(dx, dy) > 8 * scale):
                anchor = ((original.x0 + original.x1) / 2,
                          (original.y0 + original.y1) / 2)
                if marker_points:
                    nearest = min(marker_points, key=lambda p: math.dist(p, anchor))
                    if math.dist(nearest, anchor) < 50 * scale:
                        anchor = nearest
                start = ax.transData.inverted().transform(anchor)
                center = ((candidate.x0 + candidate.x1) / 2,
                          (candidate.y0 + candidate.y1) / 2)
                vx, vy = anchor[0] - center[0], anchor[1] - center[1]
                ratios = []
                if abs(vx) > 0.001:
                    ratios.append(candidate.width / 2 / abs(vx))
                if abs(vy) > 0.001:
                    ratios.append(candidate.height / 2 / abs(vy))
                fraction = min(ratios, default=0)
                end = ax.transData.inverted().transform(
                    (center[0] + fraction * vx, center[1] + fraction * vy))
                ax.annotate("", xy=start, xytext=end,
                            arrowprops=dict(arrowstyle="-", color="#687078",
                                            lw=0.45, shrinkA=2, shrinkB=2),
                            zorder=8)


def save_volume_figure(fig, filename, **kwargs):
    """保存 300 dpi 图件与矢量 PDF/SVG，并记录渲染尺寸。"""
    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
        "pdf.fonttype": 42,
        "svg.fonttype": "none",
    })
    for text in fig.findobj(Text):
        if text.get_text() and text.get_fontsize() < 8:
            text.set_fontsize(8)
    for ax in fig.axes:
        ax.grid(False, which="both")
    _pie_keys(fig)
    _page_text(fig)
    _chart_layout(fig)
    _space_labels(fig)
    name = figure_name(filename)
    target = (Path(OUTPUT_DIR) / name if OUTPUT_DIR else Path(filename).with_name(name))
    target.parent.mkdir(parents=True, exist_ok=True)
    # 地理面与河网作为底图栅格化，编号、图例与文字保留矢量。
    for ax in fig.axes:
        if ax.images or ax.get_aspect() != "auto":
            for collection in ax.collections:
                collection.set_rasterized(True)
        if hasattr(fig, "_volume1_nodes"):
            for line in ax.lines:
                if line.get_zorder() < 12:
                    line.set_rasterized(True)
            for patch in ax.patches:
                if patch.get_zorder() < 12:
                    patch.set_rasterized(True)
    tools = Path(os.environ.get(
        "NATURE_FIGURE_TOOLS",
        str(Path.home() / ".codex" / "skills" / "nature-figure" / "scripts"),
    ))
    audit_dir = Path(AUDIT_DIR) if AUDIT_DIR else target.parent / "qa"
    audit_dir.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(tools))
    from audit_panel_alignment import require_matplotlib_panel_alignment
    # 带地理长宽比的主图与放大图不是可比统计面板。
    geographic = [ax for ax in fig.axes if ax.images or ax.get_aspect() != "auto"]
    axes = [ax for ax in fig.axes if ax not in geographic]
    unique = []
    for ax in axes:
        bounds = ax.get_position().bounds
        if not any(all(abs(a - b) < 0.001 for a, b in zip(
                bounds, other.get_position().bounds)) for other in unique):
            unique.append(ax)
    exclude = [ax for ax in fig.axes if ax not in unique]
    if unique:
        require_matplotlib_panel_alignment(
            fig, exclude_axes=exclude,
            json_out=str(audit_dir / f"{target.stem}.alignment.json"),
            tolerance_pt=1.5, strict=True,
        )
    kwargs.pop("dpi", None)
    fig.savefig(target.with_suffix(".png"), dpi=300, bbox_inches="tight",
                pad_inches=0.16, **kwargs)
    fig.savefig(target.with_suffix(".pdf"), dpi=300, bbox_inches="tight",
                pad_inches=0.16)
    fig.savefig(target.with_suffix(".svg"), dpi=300, bbox_inches="tight",
                pad_inches=0.16)
    if hasattr(fig, "_volume1_nodes"):
        (audit_dir / f"{target.stem}.nodes.json").write_text(
            json.dumps(fig._volume1_nodes, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    print(f"EXPORT {name}", flush=True)
