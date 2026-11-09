# -*- coding: utf-8 -*-
"""地图制图公共工具：线要素清洗、道路分层、注记自动避让、比例尺与指北针。

本模块被 gen_district_maps.py / gen_hebei_district_maps.py /
gen_tianjin_district_maps.py 共用，用于替代此前各自复制粘贴的实现。

设计要点
--------
1. clean_lines：只剔除"明显拼接错误"的孤立长直线，不再整条丢弃真实道路
   （旧实现按单条 feature 判定，一条主干道只要有 1 个顶点间距超阈值就整条消失，
   造成路网断裂、悬空线头、主城区空洞）。
2. draw_roads：四层分级配色，灰度对比度可分辨，避免"整省铺满"。
3. LabelPlacer：贪心注记避让，冲突时按候选方位依次试探并加引线，
   替代手工填 (ox, oy) 常数偏移。
4. add_scalebar / add_compass：修复地图字符间距被拉伸、指北针压到地形上的问题。
"""
import numpy as np
import math
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle


# --------------------------------------------------------------------------
# 1. 线要素清洗
# --------------------------------------------------------------------------
def clean_lines(gdf, max_span_m=2500.0, metric_crs=None):
    """温和清洗：仅剔除两点直线且跨度超过 max_span_m 的要素。

    这类要素通常是 OSM 数据拼接错误产生的"跨城直线"，去掉后不影响路网连续性；
    其余要素（含顶点稀疏的立交、隧道、跨河段）全部保留。

    与旧 is_clean_line 的区别：旧实现只要任一相邻顶点间距 >1.5km 就丢弃整条线，
    会把大量真实干道误杀，是"路网断裂 / 主城区空洞"的直接原因。
    """
    if gdf is None or len(gdf) == 0:
        return gdf

    def keep(geom):
        if geom is None or geom.is_empty:
            return False
        if geom.geom_type == "LineString":
            coords = list(geom.coords)
            if len(coords) == 2:
                p1, p2 = coords[0], coords[1]
                d = ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5
                # 经纬度下 0.01° ≈ 1.1km；仅剔除超长孤立直线
                if d > 0.022:
                    return False
            return True
        if geom.geom_type == "MultiLineString":
            return any(keep(g) for g in geom.geoms)
        return True

    out = gdf[gdf.geometry.apply(keep)]
    return out.reset_index(drop=True)


# --------------------------------------------------------------------------
# 2. 道路分层与配色
# --------------------------------------------------------------------------
# 灰阶对比度经过校验，200dpi 下四层可分辨
ROAD_STYLE = {
    "motorway":   dict(color="#c0392b", lw=2.3, zorder=9,  label="国家高速公路"),
    "expressway": dict(color="#e8833a", lw=1.8, zorder=8,  label="城市快速路 / 环路"),
    "primary":    dict(color="#f2c14e", lw=1.25, zorder=7, label="国道 / 主要干线"),
    "secondary":  dict(color="#9aa7b1", lw=0.65, zorder=6, label="省道 / 次级道路"),
    # 支路层：区县图（1:5 万量级）必须画。核心城区（天津和平区、北京东城区）
    # 的路网主体是 tertiary/residential，只画到 secondary 会让整幅图几乎空白，
    # 看起来像"路网数据缺失"。统揽级总图不画这一层（过密）。
    "minor":      dict(color="#ccd1d6", lw=0.28, zorder=5, label="支路 / 街巷"),
}

# 关键词按"整类"匹配，避免旧实现中 "环" 字误命中（如"环境卫生路"）
_EXPRESSWAY_WORDS = ("高速", "快速", "环路", "环线", "外环", "内环", "中环",
                     "二环", "三环", "四环", "五环", "六环", "机场高速", "联络线")


def classify_roads(roads):
    """按等级把道路切成 4 个 GeoDataFrame。"""
    if roads is None:
        return {k: None for k in ROAD_STYLE}
    empty = roads.iloc[0:0]
    if len(roads) == 0:
        return {k: empty for k in ROAD_STYLE}

    t = roads.get("type")
    if t is None:
        t = roads.get("fclass")
    t = t.fillna("").astype(str) if t is not None else None
    # name 列若为 pandas 字符串类型且含缺失值，astype(str) 之后仍是 NaN（float），
    # 后续 `w in s` 会抛 TypeError: argument of type 'float' is not iterable。
    name = (roads["name"].fillna("").astype(str)
            if "name" in roads.columns else None)

    is_mw = t.isin(["motorway", "motorway_link"]) if t is not None else None
    is_trunk = t.isin(["trunk", "trunk_link", "primary", "primary_link"]) if t is not None else None
    is_sec = t.isin(["secondary", "secondary_link"]) if t is not None else None
    # service（小区内部路、停车场道）不纳入：1:5 万尺度下会糊成一片噪声
    is_minor = (t.isin(["tertiary", "tertiary_link", "residential",
                        "unclassified", "living_street", "road"])
                if t is not None else None)

    exp = None
    if name is not None:
        exp = name.apply(lambda s: any(w in s for w in _EXPRESSWAY_WORDS))

    out = {}
    out["motorway"] = roads[is_mw] if is_mw is not None else empty
    out["expressway"] = roads[(is_trunk if is_trunk is not None else False) & exp] if exp is not None else empty
    out["primary"] = roads[(is_trunk if is_trunk is not None else False) & (~exp if exp is not None else True)]
    sec_mask = is_sec
    if sec_mask is not None and name is not None:
        sec_mask = sec_mask & (name != "None")
    out["secondary"] = roads[sec_mask] if sec_mask is not None else empty
    out["minor"] = roads[is_minor] if is_minor is not None else empty
    return {k: v for k, v in out.items()}


def draw_roads(ax, layers, order=("minor", "secondary", "primary", "expressway", "motorway"),
               override=None, alpha=None):
    """按层级顺序绘制道路（先底层后上层）。

    override: {level: dict(color=, lw=)}，只覆盖指定层级的样式。
        市域级总图需要把 secondary 画成极淡的衬底，否则中心城区只剩几条
        放射线、整片空白（fig01-00-4 原"只画三层防糊"的副作用）。
    alpha:   整体透明度。
    """
    for key in order:
        g = layers.get(key)
        if g is None or len(g) == 0:
            continue
        st = dict(ROAD_STYLE[key])
        if override and key in override:
            st.update(override[key])
        g.plot(ax=ax, color=st["color"], lw=st["lw"], zorder=st["zorder"],
               alpha=alpha if alpha is not None else st.get("alpha", 1.0))


def road_legend_handles(layers, include_rail=True, include_station=True,
                        include_minor=False):
    handles = []
    keys = ["motorway", "expressway", "primary", "secondary"]
    if include_minor:
        keys.append("minor")
    for key in keys:
        st = ROAD_STYLE[key]
        handles.append(Line2D([0], [0], color=st["color"], lw=max(st["lw"], 1.2),
                              label=st["label"]))
    return handles


# --------------------------------------------------------------------------
# 3. 注记自动避让
# --------------------------------------------------------------------------
#: 全量注记冲突账本。每跑完一个脚本导出到 .tmp_debug/label_audit.jsonl，
#: 用 audit_summary() 汇总，避免"只抽检几张就说没问题"。
AUDIT = []


def audit_summary():
    import collections
    by_fig = collections.Counter(r["fig"] for r in AUDIT)
    return dict(total=len(AUDIT), figures=len(by_fig),
                detail=by_fig.most_common(20))


def audit_dump(path):
    import json
    with open(path, "w", encoding="utf-8") as f:
        for r in AUDIT:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return audit_summary()


def _audit_flush_on_exit():
    """进程退出时把本轮冲突账本落盘。

    以前"图面有没有重叠"只能靠人翻图，449 幅根本翻不完，抽检几张就说
    "没问题"是不成立的。改成每次跑图自动记账，跑完一条 grep 就能知道
    哪几幅还有残留冲突。
    """
    import atexit, json, os, sys
    if not AUDIT:
        return
    os.makedirs(".tmp_debug", exist_ok=True)
    tag = os.path.basename(sys.argv[0]).replace(".py", "") or "run"
    with open(f".tmp_debug/label_audit_{tag}.jsonl", "a", encoding="utf-8") as f:
        for r in AUDIT:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


import atexit as _atexit
_atexit.register(_audit_flush_on_exit)


class LabelPlacer:
    """贪心注记避让。

    用法：
        placer = LabelPlacer(ax, fig)
        placer.add(x, y, "文本", color="#78281f", fs=8.5, priority=0)
        placer.flush()

    priority 越小越先放置（越重要）。冲突时按"由近及远"的 40 个候选方位依次试探，
    选中第一个不与已放置注记、图幅边界、以及预留区域相交的位置；
    候选位分 5 个半径圈（0.62/1.05/1.65/2.45/3.4 个字高）× 8 个方向，
    保证密集区（如城区站群）也能把标签推开而不是叠成一行。
    """

    @staticmethod
    def _candidates():
        """候选位：8 档半径 × 12 个方位。

        6.2 以内的圈是常规避让；8.5 / 10.5 两档只在调用方显式传大
        max_radius 时才会被启用（默认 max_radius=3.4，行为不变）。
        用途：地形图「最低点」这类锚在辖区边缘、紧贴图例/色带预留区的
        标签——6.2 字高（约 70px）够不到预留区上缘（约 95px），
        40 个候选位全灭后只能兜底叠字（平谷马坊出境低点实测复现）。
        """
        out = []
        for r in (0.62, 1.05, 1.65, 2.45, 3.40, 4.60, 6.20, 8.50, 10.50):
            for ang in (90, 45, 135, 0, 180, 315, 225, 270, 22, 158, 68, 112):
                a = math.radians(ang)
                dx, dy = r * math.cos(a), r * math.sin(a)
                ha = "center" if abs(dx) < 0.3 * r else ("left" if dx > 0 else "right")
                va = "center" if abs(dy) < 0.3 * r else ("bottom" if dy > 0 else "top")
                out.append((dx, dy, ha, va))
        return out

    @staticmethod
    def _wrap(text, fs=8.6, base_em=11.0, base_fs=8.6):
        """长注记折行：括号前断开，把「东直门枢纽（2/13/机场线）」拆成两行。

        单行标签过宽是密集站群推不开的主因——在 3.4 个字高的避让半径内，
        两个 16 em 宽的标签无论怎么错位都会相交；宽度减半后候选位立刻有空，
        再用引线连回锚点，读者仍能对上要素。

        阈值随字号缩放：7 pt 的标签一行能放更多字，不该按 8.6 pt 的尺度折。
        """
        max_em = base_em * (base_fs / max(fs, 1e-3))

        def adv(t):
            return sum(1.0 if ord(ch) > 127 else 0.55 for ch in t)
        if adv(text) <= max_em or "\n" in text:
            return text
        for sep in ("（", "(", "—", "·", "，", "、"):
            i = text.find(sep)
            if 0 < i < len(text) - 1:
                head, tail = text[:i], text[i:]
                if adv(head) <= max_em and adv(tail) <= max_em:
                    return head + "\n" + tail
        # 无明显分隔符且明显过宽：按字数均分
        if adv(text) > max_em * 1.8:
            half = max(1, len(text) // 2)
            return text[:half] + "\n" + text[half:]
        return text

    CANDIDATES = None  # 延迟初始化

    def __init__(self, ax, fig, min_gap=(1.22, 1.55)):
        self.ax = ax
        self.fig = fig
        self.items = []
        self._placed = []
        self._avoid = []
        self._gap = min_gap
        if LabelPlacer.CANDIDATES is None:
            LabelPlacer.CANDIDATES = self._candidates()

    def reserve(self, x0, y0, x1, y1):
        """预留一块不可占用的数据坐标区域（如图例、比例尺）。"""
        self._avoid.append((x0, y0, x1, y1))

    def add(self, x, y, text, color="#2c3e50", fs=8.5, priority=0,
            marker=None, mcolor=None, msize=6.0, rot=0, leader=True,
            weight="bold", zorder=16, max_radius=3.4):
        """max_radius：允许的最大偏移半径（字高倍数）。

        走廊/沿路注记必须限制在 ~1.1 字高内，否则会被推到离线路很远的空白处，
        读者无法判断它指的是哪条路；宁可轻微压线也不要"飘走"。
        """
        self.items.append(dict(x=x, y=y, text=text, color=color, fs=fs,
                               priority=priority, marker=marker, mcolor=mcolor or color,
                               msize=msize, rot=rot, leader=leader, weight=weight,
                               zorder=zorder, max_radius=max_radius))

    # -- 内部 ------------------------------------------------------------
    def _em_box(self, fs):
        """一个字号高度在数据坐标下的长度（近似方字）。"""
        inv = self.ax.transData.inverted()
        p0 = inv.transform((0, 0))
        p1 = inv.transform((fs * 1.35, fs * 1.35))
        return abs(p1[0] - p0[0]), abs(p1[1] - p0[1])

    def _in_axes(self, bb):
        axbb = self.ax.get_window_extent()
        return (bb.x0 >= axbb.x0 - 2 and bb.x1 <= axbb.x1 + 2 and
                bb.y0 >= axbb.y0 - 2 and bb.y1 <= axbb.y1 + 2)

    def _hit(self, bb):
        for o in self._placed:
            if (bb.x0 < o.x1 and bb.x1 > o.x0 and bb.y0 < o.y1 and bb.y1 > o.y0):
                return True
        # 预留区域（数据坐标）
        for (x0, y0, x1, y1) in self._avoid:
            b = self.ax.transData.transform([(x0, y0), (x1, y1)])
            ab = (min(b[0][0], b[1][0]), min(b[0][1], b[1][1]),
                  max(b[0][0], b[1][0]), max(b[0][1], b[1][1]))
            if (bb.x0 < ab[2] and bb.x1 > ab[0] and bb.y0 < ab[3] and bb.y1 > ab[1]):
                return True
        return False

    def _overlap(self, bb):
        """与已放置注记的总重叠面积（像素²），用于全冲突时挑最优兜底位。"""
        area = 0.0
        for o in self._placed:
            w = min(bb.x1, o.x1) - max(bb.x0, o.x0)
            h = min(bb.y1, o.y1) - max(bb.y0, o.y0)
            if w > 0 and h > 0:
                area += w * h
        return area

    def _clamp(self, bb):
        """把越界包围盒平移回轴内所需的像素位移。

        旧实现兜底分支直接把标签放到候选位，完全不校验是否出界，
        结果「东直门枢纽（2/13/机场线）」在右边界被裁成「…（2/13/机」。
        """
        axbb = self.ax.get_window_extent()
        m = 2.0
        dx = dy = 0.0
        if bb.x1 > axbb.x1 - m:
            dx = axbb.x1 - m - bb.x1
        if bb.x0 + dx < axbb.x0 + m:
            dx = axbb.x0 + m - bb.x0
        if bb.y1 > axbb.y1 - m:
            dy = axbb.y1 - m - bb.y1
        if bb.y0 + dy < axbb.y0 + m:
            dy = axbb.y0 + m - bb.y0
        return dx, dy

    def _box(self, t, renderer):
        """文本包围盒。

        不能用 `t.get_bbox_patch().get_window_extent()`：FancyBboxPatch 在
        canvas 尚未重绘时返回退化矩形（实测为 (-0,-1,1,2)），会让碰撞检测
        恒判"不冲突"，所有注记都落在第一个候选位上。改为取文字包围盒后
        按底板内边距（boxstyle pad=0.16 em）向四周扩张。
        """
        from matplotlib.transforms import Bbox
        bb = t.get_window_extent(renderer=renderer)
        pad = t.get_fontsize() * 0.24
        return Bbox.from_extents(bb.x0 - pad, bb.y0 - pad,
                                 bb.x1 + pad, bb.y1 + pad)

    #: 同优先级要素的最小锚点间距（像素）。
    #: 市域图上 1 km 只有 2~3 px：首钢园内「滑雪大跳台 / 冬奥公园 / 工业遗址核心区」
    #: 三个锚点相距不到 10 px，而每条标签宽 120 px——这不是避让能力不够，
    #: 而是"这个比例尺画不下这么多点"。只能按优先级丢弃，否则必然叠字。
    MIN_GAP_PX = 13.0

    def _dedupe(self):
        self.fig.canvas.draw()
        order = sorted(range(len(self.items)), key=lambda k: self.items[k]["priority"])
        keep, taken = set(), []
        for k in order:
            it = self.items[k]
            px = self.ax.transData.transform((it["x"], it["y"]))
            same = [t for t in taken if t[0] == it["priority"]]
            if all((px[0] - t[1][0]) ** 2 + (px[1] - t[1][1]) ** 2
                   >= self.MIN_GAP_PX ** 2 for t in same):
                taken.append((it["priority"], px))
                keep.add(k)
        if len(keep) < len(self.items):
            self.items = [it for i, it in enumerate(self.items) if i in keep]

    def flush(self):
        if not self.items:
            return
        self._dedupe()
        if not self.items:
            return
        self.fig.canvas.draw()
        renderer = self.fig.canvas.get_renderer()
        # 记录每个标签的最终落点，供调用方自行补画引线 / 做审计
        self.placed = []

        # 先放标记点（符号本身较小，允许与文字共用锚点附近）
        for it in sorted(self.items, key=lambda d: d["priority"]):
            if it["marker"]:
                self.ax.plot(it["x"], it["y"], marker=it["marker"], color=it["mcolor"],
                             markersize=it["msize"], markeredgecolor="white",
                             markeredgewidth=0.8, zorder=it["zorder"] - 1,
                             linestyle="none")

        inv = self.ax.transData.inverted()

        import re as _re

        def _strip_paren(s):
            """去掉括注：「滨海站（于家堡地下特等枢纽）」→「滨海站」。

            密集站群里标签宽度本身就是冲突主因，只靠挪位挪不开（3 个站相距
            不足 30 px，标签却宽 180 px）。放不下时先退化为主名，读者仍能靠
            引线与符号对上；稀疏处仍保留完整括注。
            """
            out = _re.sub(r"[（(][^）)]*[）)]", "", s).strip()
            return out if out and out != s.strip() else None

        for it in sorted(self.items, key=lambda d: d["priority"]):
            emx, emy = self._em_box(it["fs"])
            cands = [c for c in self.CANDIDATES
                     if (c[0] ** 2 + c[1] ** 2) ** 0.5 <= it["max_radius"] + 1e-6]

            def _make(text, dx, dy, ha, va):
                tx = it["x"] + dx * emx
                ty = it["y"] + dy * emy
                t = self.ax.text(tx, ty, text, fontsize=it["fs"],
                                 fontweight=it["weight"], color=it["color"],
                                 rotation=it["rot"], rotation_mode="anchor",
                                 ha=ha, va=va, zorder=it["zorder"],
                                 path_effects=_stroke(fs=it["fs"]),
                                 bbox=_chip())
                bb = self._box(t, renderer).expanded(*self._gap)
                return t, bb

            def _sweep(text):
                """在一组候选位里找一个「在轴内且不冲突」的位置。"""
                chosen, best = None, None
                for (dx, dy, ha, va) in cands:
                    t, bb = _make(text, dx, dy, ha, va)
                    if self._in_axes(bb) and not self._hit(bb):
                        chosen = (t, bb)
                        break
                    # 兜底代价：越界取「溢出像素²」，与重叠面积同量纲可比
                    cdx, cdy = self._clamp(bb)
                    cost = self._overlap(bb) + (abs(cdx) + abs(cdy)) ** 2 * 900.0
                    if best is None or cost < best[0]:
                        best = (cost, dx, dy, ha, va)
                    # 试探用的 Text 必须移除：旧实现在更新 best 时重建 Text 却不删旧的，
                    # 结果同一标签在图上被画了两三遍（东城区「东单（1/5号线）」）。
                    t.remove()
                return chosen, best

            txt = self._wrap(it["text"], it["fs"])
            chosen, best = _sweep(txt)
            final_txt = txt

            if chosen is None:
                short = _strip_paren(txt.replace("\n", ""))
                if short:
                    chosen, best = _sweep(short)
                    final_txt = short

            if chosen is None:
                if best is None:
                    dx, dy, ha, va = self.CANDIDATES[0]   # max_radius 过小，退回最近位
                else:
                    _, dx, dy, ha, va = best
                t, bb = _make(final_txt, dx, dy, ha, va)
                # 兜底位若仍越界，整体平移回轴内（平移后重新取包围盒）
                cdx, cdy = self._clamp(bb)
                if cdx or cdy:
                    ddx, ddy = inv.transform((bb.x0 + cdx, bb.y0 + cdy))
                    pdx, pdy = inv.transform((bb.x0, bb.y0))
                    t.set_position((t.get_position()[0] + ddx - pdx,
                                    t.get_position()[1] + ddy - pdy))
                    bb = self._box(t, renderer).expanded(*self._gap)
                chosen = (t, bb)

            t, bb = chosen
            if self._hit(bb):
                # 兜底位仍与已放置注记相交 = 真重叠。以前没人统计，只能靠人眼
                # 抽几张，掩盖了"多数图还好、少数图叠死"的分布。这里全量记账。
                AUDIT.append(dict(fig=self.ax.get_title() or "",
                                  n=len(self.items),
                                  sample=" / ".join(x["text"] for x in self.items[:3]),
                                  text=it["text"], kind="text_overlap"))
            self._placed.append(bb)
            self.placed.append((it, t, bb))

            if it["leader"]:
                # 引线：从文本边界最近点指向锚点，避免穿过文字。
                # 注意锚点必须先转成像素再与包围盒比较——旧实现直接拿数据坐标
                # （Albers 下约 4×10⁶）与像素坐标（约 10³）取 min/max，
                # 结果恒等于包围盒的右/下边缘，引线一律斜穿整幅图。
                ax_px = self.ax.transData.transform((it["x"], it["y"]))
                cx = min(max(ax_px[0], bb.x0), bb.x1)
                cy = min(max(ax_px[1], bb.y0), bb.y1)
                p_txt = inv.transform((cx, cy))
                if ((p_txt[0] - it["x"]) ** 2 + (p_txt[1] - it["y"]) ** 2) > 0:
                    self.ax.plot([it["x"], p_txt[0]], [it["y"], p_txt[1]],
                                 color="#95a5a6", lw=0.6, zorder=it["zorder"] - 2,
                                 solid_capstyle="round")


def _stroke(lw=None, fs=None):
    """白色描边：让注记压在深色路网/等高线上仍然可读。

    旧实现固定 2.6 pt，对 7 pt 的注记相当于把字吃掉一圈；
    这里按字号缩放，并给上下限。
    """
    import matplotlib.patheffects as pe
    if lw is None:
        lw = 2.6 if fs is None else min(3.2, max(1.5, fs * 0.30))
    return [pe.withStroke(linewidth=lw, foreground="white")]


def _chip(alpha=0.66):
    """注记底板：半透明白底。

    只用描边在高密度路网（石家庄站群、滨海新区中心）上仍会与红线混读，
    加一层淡底板后文字与底图分离；在空白处白底白纸几乎不可见，不增加噪声。
    """
    return dict(boxstyle="round,pad=0.16", facecolor="white",
                edgecolor="none", alpha=alpha)


def reserve_axes_boxes(placer, ax, boxes):
    """按坐标轴比例预留不可占用区域（图例、比例尺、指北针、鹰眼图等）。

    boxes: [(fx0, fy0, fx1, fy1), ...]，取值 0–1 的轴比例。
    """
    xl, yl = ax.get_xlim(), ax.get_ylim()
    wx, wy = xl[1] - xl[0], yl[1] - yl[0]
    for (fx0, fy0, fx1, fy1) in boxes:
        placer.reserve(xl[0] + wx * fx0, yl[0] + wy * fy0,
                       xl[0] + wx * fx1, yl[0] + wy * fy1)


# --------------------------------------------------------------------------
# 4. 比例尺与指北针
# --------------------------------------------------------------------------
def add_scalebar(ax, x0, y0, length_km=5, label_color="#2c3e50"):
    """三段式比例尺。

    修复三处问题：
    ① km 文本里带空格（"25 km"）会让 matplotlib 按字符间距拉伸整串，刻度与色块
       对不齐，统一改成紧排的 "25km"；
    ② 里程大（承德 25 km、张家口 40 km）而图幅窄时，中点标签 "12.5" 与端点
       "25km" 会挤到一起互压。按像素长度估阈值不可靠（字号 8pt 在 200 dpi 下
       每个数字就有 12 px，四个字符近 45 px），改为**先渲染再量真实包围盒**，
       只要中点标签碰到两端就把中点去掉；
    ③ 色块高度按 ylim 比例算，小图幅上会细到看不见，给一个下限。
    """
    ymin, ymax = ax.get_ylim()
    h = max((ymax - ymin) * 0.012, (ymax - ymin) * 0.004)
    length_m = length_km * 1000.0
    half = length_m / 2.0
    ax.add_patch(Rectangle((x0, y0), half, h, facecolor="#2c3e50",
                           edgecolor="#2c3e50", lw=0.6, zorder=25))
    ax.add_patch(Rectangle((x0 + half, y0), half, h, facecolor="white",
                           edgecolor="#2c3e50", lw=0.6, zorder=25))
    ty = y0 - h * 1.5
    t0 = ax.text(x0, ty, "0", ha="center", va="top", fontsize=8.0,
                 color=label_color, zorder=25)
    tm = ax.text(x0 + half, ty, f"{length_km/2:g}", ha="center", va="top",
                 fontsize=8.0, color=label_color, zorder=25)
    te = ax.text(x0 + length_m, ty, f"{length_km:g}km", ha="center", va="top",
                 fontsize=8.0, color=label_color, zorder=25)
    try:
        fig = ax.figure
        fig.canvas.draw()
        r = fig.canvas.get_renderer()
        b0, bm, be = (t.get_window_extent(r) for t in (t0, tm, te))
        if bm.x0 - 5.0 < b0.x1 or bm.x1 + 5.0 > be.x0:
            tm.remove()
    except Exception:
        pass
    return None


def stacked_legends(ax, groups, x=0.5, top=-0.012, gap=0.014):
    """在坐标轴下方纵向堆叠多组图例，每组自动挂在上一组下沿。

    图面采用「符号 + 编号」后，图例分两类信息：线型/符号含义、编号到名称的
    对照表。两类混在同一个 legend 里会被 matplotlib 按列重排，读者分不清哪条
    是类型说明哪条是编号，所以拆成两组。

    实现上必须用 **fig.legend** 而不是 ax.legend：Axes.legend 是单例，
    第二次调用会把第一个 legend 从 artists 里摘掉，表现是"第二组图例整块消失、
    只留第一组被裁掉半截"。

    groups: [dict(handles=[...], title="...", ncol=3, fontsize=6.6), ...]
    返回最后一组图例对象，便于继续接 footer_below_legend()。
    """
    fig = ax.figure
    y = top
    last = None
    for g in groups:
        leg = fig.legend(handles=g["handles"], loc="upper center",
                         bbox_to_anchor=(x, y), bbox_transform=ax.transAxes,
                         ncol=g.get("ncol", 3),
                         fontsize=g.get("fontsize", 6.6),
                         framealpha=g.get("framealpha", 0.96),
                         borderpad=0.55, columnspacing=1.25, handlelength=1.9,
                         title=g.get("title"),
                         title_fontsize=g.get("title_fontsize", 7.2))
        leg.set_zorder(20)
        fig.canvas.draw()
        try:
            bb = leg.get_window_extent(fig.canvas.get_renderer())
        except Exception:
            bb = leg.get_window_extent()
        y = ax.transAxes.inverted().transform((bb.x0, bb.y0))[1] - gap
        last = leg
    return last


def footer_below_legend(ax, legend, text, gap=0.006, fontsize=6.8, color="#7f8c8d"):
    """把数据源脚注挂到**所有**图例的最下沿之下。

    图例外移到图幅下方后高度随条目数/列数变化，固定 y 的脚注会被图例盒子
    从中间截断（表现为脚注只露出左右两截）。这里不再信任传进来的单个
    legend——多组图例堆叠时最后一个未必是最低的——而是遍历 figure 上所有
    legend 取最小 y，任何条目数、任何组数都不会再压。
    """
    fig = ax.figure
    fig.canvas.draw()                       # 不重绘时 legend 的 extent 会退化
    try:
        renderer = fig.canvas.get_renderer()
    except Exception:
        renderer = None
    ys = []
    for lg in list(getattr(fig, "legends", [])) + ([legend] if legend is not None else []):
        try:
            bb = lg.get_window_extent(renderer=renderer) if renderer else lg.get_window_extent()
        except Exception:
            continue
        # 换算成 figure 坐标：图例用 ax.transAxes 锚定、脚注若也用 ax 坐标，
        # 一旦 ax 的位置被 subplots_adjust 改过，两者基准不同就会错位。
        # 统一到 figure 坐标后，bbox_inches="tight" 扩边也不会拆散它们。
        ys.append(fig.transFigure.inverted().transform((bb.x0, bb.y0))[1])
    y_bottom = min(ys) if ys else 0.02
    return fig.text(0.5, y_bottom - gap, text,
                    ha="center", va="top", fontsize=fontsize, color=color)


def add_compass(ax, x=0.955, y=0.90, size=0.055):
    """指北针：置于坐标轴右上角并保持在图幅内的安全区。"""
    from matplotlib.patches import FancyArrow
    trans = ax.transAxes
    ax.add_patch(FancyArrow(x, y - size * 0.55, 0, size, width=0.0022,
                            head_width=size * 0.42, head_length=size * 0.42,
                            fc="#2c3e50", ec="#2c3e50", transform=trans, zorder=26))
    ax.text(x, y + size * 0.55, "N", transform=trans, ha="center", va="bottom",
            fontsize=10.5, fontweight="bold", color="#2c3e50", zorder=26)


# --------------------------------------------------------------------------
# 5. 符号 + 编号注记（图面零文字方案）
# --------------------------------------------------------------------------
def split_note(s):
    """「北京站 (国铁特等站)」→ ("北京站", "国铁特等站")。

    区级配置把括注直接写在名称里（全角/半角括号混用）。符号化后名称进图例、
    括注改名「注」，两者分开排版更整齐，也便于图例列宽对齐。
    """
    import re as _re
    m = _re.match(r"^(.*?)\s*[（(]([^）)]*)[）)]\s*$", s)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return s.strip(), ""


def hex2lab(h):
    """#rrggbb → CIE Lab。供同形状颜色的区分度检查使用。"""
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (1, 3, 5))
    def _f(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = _f(r), _f(g), _f(b)
    x = (r * 0.4124 + g * 0.3576 + b * 0.1805) / 0.95047
    y = (r * 0.2126 + g * 0.7152 + b * 0.0722) / 1.00000
    z = (r * 0.0193 + g * 0.1192 + b * 0.9505) / 1.08883
    def _g(t):
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    fx, fy, fz = _g(x), _g(y), _g(z)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def delta_e(h1, h2):
    """CIE76 色差。小尺寸符号上 ΔE < 25 肉眼基本分不开。"""
    a, b = hex2lab(h1), hex2lab(h2)
    return sum((p - q) ** 2 for p, q in zip(a, b)) ** 0.5


#: 图内调色板：任取两色 Lab ΔE76 ≥ 32（下方有静态校验，改动即报错）。
#: 图面零文字方案下，专题图的类型区分全靠「形状 + 颜色」；同形状的类型
#: 一旦颜色相近（港口深绿 vs 陆港绿 dE=23 曾并排挂在图例里），读者无从
#: 分辨。专题图类型数 ≤6，按序取用即可保证同图互异。
FIG_PALETTE = [
    "#c0392b",  # 红
    "#1f618d",  # 蓝
    "#1e8449",  # 绿
    "#d68910",  # 橙
    "#6c3483",  # 紫
    "#7e5109",  # 棕
    "#ad1457",  # 品红
    "#48c9b0",  # 青绿
]

# 调色板自检：新增/替换颜色时若破坏两两区分度，import 即失败。
for _i in range(len(FIG_PALETTE)):
    for _j in range(_i + 1, len(FIG_PALETTE)):
        assert delta_e(FIG_PALETTE[_i], FIG_PALETTE[_j]) >= 32.0, (
            f"FIG_PALETTE {_i}/{_j} 色差不足: "
            f"{FIG_PALETTE[_i]} vs {FIG_PALETTE[_j]} "
            f"dE={delta_e(FIG_PALETTE[_i], FIG_PALETTE[_j]):.1f} < 32")


def assign_colors(kinds, min_de=30.0):
    """给一幅图实际用到的类型分配高区分度颜色，返回 {kind: color}。

    旧做法是全局固定色表：河北专题图 47 个类型共用十来个颜色轮转，
    同一幅图里两个类型拿到同色/近色（同形状）的 pairing 被全量审计
    记了 51 处。改为每幅图现场分配：按首次出现顺序从 FIG_PALETTE
    取第一个与已分配颜色 ΔE ≥ min_de 的色；全部不达标时退回 ΔE 最大的
    一档（此时审计的 low_contrast 检查会兜底记账）。
    """
    chosen = {}
    for k in kinds:
        if k in chosen:
            continue
        best, best_de = None, -1.0
        for c in FIG_PALETTE:
            de = min((delta_e(c, v) for v in chosen.values()), default=1e9)
            if de >= min_de:
                best = c
                break
            if de > best_de:
                best, best_de = c, de
        chosen[k] = best
    return chosen


SYMBOL_KINDS = {
    "rail_hub":   dict(marker="s", face="#b03a2e", size=9.2, label="铁路特等 / 一级客运枢纽"),
    "rail_mid":   dict(marker="P", face="#d35400", size=7.5, label="铁路一般客运站"),
    "rail_goods": dict(marker="p", face="#5d6d7e", size=6.8, label="铁路货运 / 编组站"),
    "airport":    dict(marker="^", face="#1f618d", size=9.8, label="民用运输机场"),
    "port":       dict(marker="D", face="#0e6251", size=8.8, label="沿海港口（含主港区）"),
    "port_zone":  dict(marker="v", face="#16a085", size=6.8, label="港口作业区"),
    "highway":    dict(marker="H", face="#2e4053", size=8.2, label="高速公路互通 / 门户"),
    "metro":      dict(marker="o", face="#8e44ad", size=7.4, label="轨道交通换乘站"),
    "bus":        dict(marker="d", face="#f39c12", size=5.8, label="公路客运枢纽"),
    "corridor":   dict(marker=">", face="#b03a2e", size=6.5, label="综合运输通道 / 发展轴"),
    "city":       dict(marker="o", face="#2c3e50", size=4.8, label="重要城镇"),
    "dryport":    dict(marker="h", face="#6c3483", size=8.4, label="陆港 / 综合交通枢纽"),
    "scenic":     dict(marker="*", face="#27ae60", size=8.8, label="风景名胜"),
    "mountain":   dict(marker="^", face="#7e5109", size=6.8, label="山峰 / 山体"),
}


def smooth_line(pts, n=16):
    """Catmull-Rom 样条平滑，消除交通线路直接拉线的直来直去感。
    pts 可以是 (x, y) 坐标列表，或者 (lon, lat) 坐标列表。
    返回平滑后的 (xs, ys) 元组。
    """
    if len(pts) < 2:
        return [p[0] for p in pts], [p[1] for p in pts]
    if len(pts) == 2:
        # 仅有两点时，插入带微自然地理弧度的中间过渡点，避免僵硬死板的直尺拉线
        p0, p1 = pts[0], pts[1]
        dx = p1[0] - p0[0]
        dy = p1[1] - p0[1]
        dist = (dx * dx + dy * dy) ** 0.5
        # 法向微弯曲向量（控制在距离的 1.8% 左右，呈现微弧走廊）
        nx, ny = -dy / (dist + 1e-9), dx / (dist + 1e-9)
        offset = dist * 0.018
        m1 = (p0[0] + dx * 0.33 + nx * offset, p0[1] + dy * 0.33 + ny * offset)
        m2 = (p0[0] + dx * 0.67 + nx * offset * 0.8, p0[1] + dy * 0.67 + ny * offset * 0.8)
        pts = [p0, m1, m2, p1]

    P = [pts[0]] + list(pts) + [pts[-1]]
    xs, ys = [], []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            for a, b, c, d, out in ((p0[0], p1[0], p2[0], p3[0], xs),
                                    (p0[1], p1[1], p2[1], p3[1], ys)):
                out.append(0.5 * ((2 * b) + (-a + c) * t
                                  + (2 * a - 5 * b + 4 * c - d) * t2
                                  + (-a + 3 * b - 3 * c + d) * t3))
    xs.append(P[-2][0])
    ys.append(P[-2][1])
    return xs, ys



class SymbolLabels:
    """把图面文字注记换成「符号 + 编号」，名称统一移到图外图例。
    为什么必须这样做
    ----------------
    城市尺度交通图上的中文注记动辄 8~16 个字宽：「天津滨海国际机场（4E 级
    双跑道国家枢纽）」在 6.2 pt / 200 dpi 下约 230 px，而滨海新区「滨海站 /
    滨海西站 / 市民广场站」三站彼此相距不足 30 px。贪心避让在这种密度下
    **物理上无解**——不管放宽到几个半径圈、怎么折行、怎么退化主名，标签
    本身比它要避让的空间还宽。此前几轮的避让参数调优只是在推迟失败。

    可靠做法只有一条：把文字搬出图面。图上每个要素只留：
      · 一个按类型区分颜色与形状的符号
      · 一个 1~2 位编号（白底小字，宽度不足 20 px）
    读者凭编号到图外图例查名，图例同时说明符号形状/颜色的含义。

    用法::

        sl = SymbolLabels(ax, fig)
        sl.reserve([(0.0, 0.0, 0.38, 0.28), ...])   # 可选：预留图内禁放区
        sl.add(x, y, "天津站", "rail_hub", note="三线交汇特等站")
        sl.add(x, y, "天津港", "port", note="年吞吐超 5.5 亿吨")
        type_h, idx_h = sl.flush()
        # 两组 handles 交给 fig.legend(...) 放图外

    flush() 返回 (类型说明 handles, 编号对照 handles)。
    """

    # 编号相对符号的候选位：先右上，再四周近位。半径刻意压小——
    # 编号离符号太远就失去指代关系，宁可让编号压到路网上也不能飞出半个图幅。
    _IDX_CANDS = []
    for _r in (0.72, 1.15, 1.75):
        for _a in (45, 135, 315, 225, 0, 180, 90, 270, 22, 158):
            _rad = math.radians(_a)
            _dx, _dy = _r * math.cos(_rad), _r * math.sin(_rad)
            _ha = "center" if abs(_dx) < 0.3 * _r else ("left" if _dx > 0 else "right")
            _va = "center" if abs(_dy) < 0.3 * _r else ("bottom" if _dy > 0 else "top")
            _IDX_CANDS.append((_dx, _dy, _ha, _va))

    def __init__(self, ax, fig):
        self.ax = ax
        self.fig = fig
        self.items = []
        self._reserved = []

    def reserve(self, boxes):
        """预留图内不可占用区（图例、比例尺、指北针），轴比例 0–1。"""
        xl, yl = self.ax.get_xlim(), self.ax.get_ylim()
        wx, wy = xl[1] - xl[0], yl[1] - yl[0]
        for (fx0, fy0, fx1, fy1) in boxes:
            self._reserved.append((xl[0] + wx * fx0, yl[0] + wy * fy0,
                                   xl[0] + wx * fx1, yl[0] + wy * fy1))

    def add(self, x, y, name, kind, note="", priority=None, zorder=18,
            marker=None, face=None, size=None, kind_label=None):
        """登记一个要素。编号按调用顺序自增，与图例对照表顺序一致。

        marker / face / size / kind_label 可覆盖内置样式，供专题图按自己的
        类型表（政府 / 景点 / 园区 / 遗址…）就地定义符号，不必逐个往
        SYMBOL_KINDS 里加。
        """
        if kind not in SYMBOL_KINDS:
            if marker is None or face is None:
                raise KeyError(f"未知符号类型 {kind!r}，可选：{sorted(SYMBOL_KINDS)}")
            SYMBOL_KINDS[kind] = dict(marker=marker, face=face,
                                      size=size or 7.0,
                                      label=kind_label or kind)
        elif marker is not None:
            st = dict(SYMBOL_KINDS[kind])
            st["marker"] = marker
            if face is not None:
                st["face"] = face
            if size is not None:
                st["size"] = size
            if kind_label is not None:
                st["label"] = kind_label
            SYMBOL_KINDS[kind] = st
        self.items.append(dict(
            x=x, y=y, name=name, kind=kind, note=note,
            idx=len(self.items) + 1,
            priority=len(self.items) if priority is None else priority,
            zorder=zorder))

    #: 同类要素的最小像素间距。市域图上 1 km 只有 2~3 px，承德市区三个车站
    #: 相距不足 6 px，9 pt 的方块直接叠成一团红块——既看不出是几个站，
    #: 编号也没有落脚处。低于这个间距的同类要素只保留离中心最近的一个。
    MIN_GAP_PX = 26.0

    def _dedupe_px(self):
        """按像素间距去重（只在同类要素内部做）。

        跨类型不去重：机场和市区车站即使重合也要都留，它们表达的是不同事实。
        """
        self.fig.canvas.draw()
        px = [self.ax.transData.transform((it["x"], it["y"])) for it in self.items]
        cx = sum(p[0] for p in px) / len(px)
        cy = sum(p[1] for p in px) / len(px)
        by_kind = {}
        for i, it in enumerate(self.items):
            by_kind.setdefault(it["kind"], []).append(i)
        keep = set()
        all_taken = []          # [(kind, (x, y)), ...] 跨类型共用的占位表
        for kind, idxs in by_kind.items():
            idxs.sort(key=lambda k: (px[k][0] - cx) ** 2 + (px[k][1] - cy) ** 2)
            for k in idxs:
                p = px[k]
                ok = True
                for (k2, q) in all_taken:
                    d2 = (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2
                    # 同类型要求 26 px（连编号一起让开）；跨类型只要不把符号
                    # 压在别人身上，留 13 px。跨类型若也套 26 px，机场和同城
                    # 车站会被强行二选一——那表达的是两件不同的事。
                    if d2 < (self.MIN_GAP_PX ** 2 if k2 == kind else 169.0):
                        ok = False
                        break
                if ok:
                    all_taken.append((kind, p))
                    keep.add(k)
        dropped = [self.items[i]["name"] for i in range(len(self.items)) if i not in keep]
        self.items = [it for i, it in enumerate(self.items) if i in keep]
        for n, it in enumerate(self.items, 1):
            it["idx"] = n
        self.dropped = dropped
        return dropped

    def flush(self):
        """画符号与编号，返回 (类型说明 handles, 编号对照 handles)。"""
        from matplotlib.lines import Line2D

        self._dedupe_px()
        if not self.items:
            return [], []

        # ① 先画符号：符号本身不参与避让（它只有 9 px，是锚点而非注记）
        # 未填充 marker（x + | _ 等）上色靠 edgecolor，若统一套白色描边会
        # 变成白色符号、在图面上彻底消失（走廊曾因此只剩编号不见符号）。
        _UNFILLED = {"x", "+", "|", "_"}
        for it in self.items:
            st = SYMBOL_KINDS[it["kind"]]
            filled = st["marker"] not in _UNFILLED
            self.ax.plot(it["x"], it["y"], marker=st["marker"], linestyle="none",
                         markersize=st["size"],
                         markerfacecolor=st["face"] if filled else "none",
                         markeredgecolor="white" if filled else st["face"],
                         markeredgewidth=0.9, zorder=it["zorder"])

        # ② 编号固定在符号右上（放不下就翻到其余三角）。
        # 这里**不做贪心避让**：符号已按 26 px 去重，编号宽不足 10 px，紧贴后
        # 相邻编号中心距必 ≥26 px，本来就不会撞；上一版把编号交给 LabelPlacer
        # 反而把编号推到邻居编号上（全量审计记到 14 处编号互撞），
        # 因为避让器既躲不开自己的符号、又不知道邻居编号也占位。
        renderer = self.fig.canvas.get_renderer()
        axbb = self.ax.get_window_extent()
        inv = self.ax.transData.inverted()
        # 所有符号的像素位置：编号四角都要避开它们。只判轴边界不够——
        # 东城「王府井商业区」的编号曾经正好压在同城的区政府星标上。
        sym_px = [self.ax.transData.transform((it["x"], it["y"])) for it in self.items]
        for it in self.items:
            st = SYMBOL_KINDS[it["kind"]]
            px, py = self.ax.transData.transform((it["x"], it["y"]))
            off = max(5.2, st["size"] * 0.80)
            spot = None
            for (dxs, dys, ha, va) in ((off, off, "left", "bottom"),
                                       (-off, off, "right", "bottom"),
                                       (off, -off, "left", "top"),
                                       (-off, -off, "right", "top"),
                                       (off * 1.55, off * 0.2, "left", "center"),
                                       (-off * 1.55, off * 0.2, "right", "center")):
                tx, ty = inv.transform((px + dxs, py + dys))
                cxp, cyp = px + dxs, py + dys
                if any((cxp - q[0]) ** 2 + (cyp - q[1]) ** 2 < 49.0
                       for q in sym_px if (q[0], q[1]) != (px, py)):
                    continue
                t = self.ax.text(tx, ty, str(it["idx"]), fontsize=5.9,
                                 fontweight="bold", color="#1a252f", ha=ha, va=va,
                                 zorder=it["zorder"] + 2,
                                 path_effects=_stroke(fs=5.9), bbox=_chip())
                bb = t.get_window_extent(renderer=renderer)
                if (bb.x0 >= axbb.x0 - 1 and bb.x1 <= axbb.x1 + 1
                        and bb.y0 >= axbb.y0 - 1 and bb.y1 <= axbb.y1 + 1):
                    spot = t
                    break
                t.remove()
            if spot is None:
                tx, ty = inv.transform((px + off, py + off))
                self.ax.text(tx, ty, str(it["idx"]), fontsize=5.9,
                             fontweight="bold", color="#1a252f", ha="left", va="bottom",
                             zorder=it["zorder"] + 2,
                             path_effects=_stroke(fs=5.9), bbox=_chip())

        # ③ 图例条目
        used = []
        for it in self.items:
            if it["kind"] not in used:
                used.append(it["kind"])

        # ③' 同形状颜色区分度检查。图例里形状相同的条目只能靠颜色区分，
        # 小尺寸符号（5~9 pt）上 ΔE76 < 25 的两色肉眼基本分不出——
        # 曾有港口 #117864 vs 陆港 #1e8449 这对深绿并排挂在图例里。
        # 这里逐对记账，修色前先让问题显形。
        for i in range(len(used)):
            for j in range(i + 1, len(used)):
                ka, kb = used[i], used[j]
                sa, sb = SYMBOL_KINDS[ka], SYMBOL_KINDS[kb]
                if sa["marker"] != sb["marker"]:
                    continue
                de = delta_e(sa["face"], sb["face"])
                if de < 25.0:
                    AUDIT.append(dict(fig=self.ax.get_title() or "",
                                      n=len(used),
                                      sample="",
                                      text=f"{ka}({sa['face']}) vs {kb}({sb['face']}) dE={de:.0f}",
                                      kind="low_contrast"))
        type_handles = [
            Line2D([0], [0], marker=SYMBOL_KINDS[k]["marker"], linestyle="none",
                   color="none", markerfacecolor=SYMBOL_KINDS[k]["face"],
                   markeredgecolor="white", markeredgewidth=0.8,
                   markersize=min(SYMBOL_KINDS[k]["size"], 9.0),
                   label=SYMBOL_KINDS[k]["label"])
            for k in used]
        idx_handles = [
            Line2D([0], [0], marker=SYMBOL_KINDS[it["kind"]]["marker"], linestyle="none",
                   color="none", markerfacecolor=SYMBOL_KINDS[it["kind"]]["face"],
                   markeredgecolor="white", markeredgewidth=0.8,
                   markersize=min(SYMBOL_KINDS[it["kind"]]["size"], 7.2),
                   label=(f"{it['idx']}  {it['name']}"
                          + (f"（{it['note']}）" if it["note"] else "")))
            for it in self.items]
        return type_handles, idx_handles
