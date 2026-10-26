# -*- coding: utf-8 -*-
"""全书结构与机械一致性检查（只读，不改文件）。

用法：python qa_structure.py
输出：逐条问题清单 + 统计摘要。
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEC = os.path.join(ROOT, "sections")
FIG = os.path.join(ROOT, "figures")
HTML = os.path.join(ROOT, "html")

EXPECT = ([f"01-0{i}" for i in range(1, 4)] + [f"02-0{i}" for i in range(1, 5)]
          + [f"03-0{i}" for i in range(1, 6)] + [f"04-0{i}" for i in range(1, 6)]
          + [f"05-0{i}" for i in range(1, 6)] + [f"06-0{i}" for i in range(1, 5)]
          + [f"07-0{i}" for i in range(1, 4)] + [f"08-0{i}" for i in range(1, 4)]
          + [f"09-0{i}" for i in range(1, 5)] + [f"10-0{i}" for i in range(1, 4)]
          + [f"11-0{i}" for i in range(1, 5)] + [f"12-0{i}" for i in range(1, 4)]
          + [f"13-0{i}" for i in range(1, 5)]
          + [f"13-05-{i:02d}" for i in range(1, 35)] + ["99"])

PROV_H2 = [("省情速览",), ("自然地理",), ("建置沿革",),
           ("经济",), ("分区地理",), ("之最",)]

issues = []


def add(kind, fname, line, msg):
    issues.append((kind, fname, line, msg))


mds = sorted(f for f in os.listdir(SEC) if f.endswith(".md"))
stems = {f[:-3] for f in mds}

# ---------- 0. 完整性
for e in EXPECT:
    if not any(s == e or s.startswith(e + "_") for s in stems):
        add("缺节", "-", 0, f"提纲中的小节 {e} 没有对应文件")
extra = [s for s in stems if not s.startswith("13-05_")
         and not any(s == e or s.startswith(e + "_") for e in EXPECT)]
for s in extra:
    add("多节", s, 0, "不在提纲编号内的文件")

figs = set(os.listdir(FIG))
htmls = {f[:-5] for f in os.listdir(HTML) if f.endswith(".html")}
used_fig = {}

for f in mds:
    raw = open(os.path.join(SEC, f), "rb").read()
    if raw.startswith(b"\xef\xbb\xbf"):
        add("BOM", f, 1, "文件带 UTF-8 BOM（PowerShell 写入残留），首字符会渲染成乱码")
        raw = raw[3:]
    t = raw.decode("utf-8")
    lines = [x.replace("\r", "") for x in t.split("\n")]

    # ---------- 1. 标题编号与文件名
    m = re.match(r"^#\s*(\d+(?:\.\d+)*)\s", lines[0] if lines else "")
    if not m:
        add("标题", f, 1, f"首行不是 '# X.Y 标题' 形式：{lines[0][:40]!r}")
    else:
        num = m.group(1)
        if f.startswith("13-05-"):
            want = "13.5." + str(int(f[6:8]))
        elif f.startswith("99"):
            want = None
        else:
            want = f[:2].lstrip("0") + "." + f[4]
        if want and num != want:
            add("标题编号", f, 1, f"标题编号 {num} 与文件名应为的 {want} 不符")

    # ---------- 2. 分省六段式
    if f.startswith("13-05-") and f != "13-05_推进登记.md":
        h2 = [x for x in lines if x.startswith("## ")]
        for keys in PROV_H2:
            if not any(any(k in h for k in keys) for h in h2):
                add("分省结构", f, 0, f"缺少二级标题“{keys[0]}”")
        if not any("参考与数据来源" in x for x in h2):
            add("分省结构", f, 0, "缺少“参考与数据来源”")
        ch = len(re.sub(r"\s", "", t))
        if ch < 2500:
            add("篇幅", f, 0, f"正文字符仅 {ch}")

    # ---------- 3. 图片引用 / 图号 / 图注
    for i, ln in enumerate(lines):
        for alt, path in re.findall(r"!\[([^\]]*)\]\(([^)]+)\)", ln):
            base = os.path.basename(path)
            if base not in figs:
                add("图缺失", f, i + 1, f"引用的图不存在: {base}")
            used_fig.setdefault(base, []).append(f)
            a = re.search(r"图\s*(\d+)-(\d+)", alt)
            b = re.search(r"fig(\d+)-(\d+)_", base)
            if a and b and (a.group(1), a.group(2)) != (b.group(1), b.group(2)):
                add("图号不符", f, i + 1,
                    f"alt“{alt}”与文件名“{base}”的图号不一致")
            if not a:
                add("图题", f, i + 1, f"图片 alt 未写“图 X-Y”：{alt}")
            # 图注：向下越过空行找第一行非空
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            cm = re.match(r"^\*\*图\s*(\d+)-(\d+)", lines[j].strip()) if j < len(lines) else None
            if not cm:
                add("图注", f, i + 1, "图片后没有紧跟“**图 X-Y …**”图注")
            elif cm.group(1) != (b.group(1) if b else "") or \
                    cm.group(2) != (b.group(2) if b else ""):
                add("图注号", f, j + 1, "图注图号与图片文件名不一致")

        # 正文引用的图号是否存在于 figures
        for g in re.findall(r"图\s*(\d+)-(\d+)", ln):
            num = f"fig{g[0]}-{g[1]}_"
            if not any(n.startswith(num) for n in figs):
                add("图号引用", f, i + 1, f"提到图 {g[0]}-{g[1]}，但无此图")

    # ---------- 4. 跨节引用
    for ref in re.findall(r"见\s*(\d+)\.(\d+)\s*节", t):
        key = f"{int(ref[0]):02d}-{int(ref[1]):02d}"
        if not any(s.startswith(key) for s in stems):
            add("跨节引用", f, 0, f"引用 {ref[0]}.{ref[1]} 节，但该节不存在")

    # ---------- 5. 表格列数
    in_tbl, header_cols = False, 0
    for i, ln in enumerate(lines):
        if ln.strip().startswith("|"):
            cols = ln.count("|")
            if not in_tbl:
                in_tbl, header_cols = True, cols
            elif cols != header_cols and not re.match(r"^\|[\s:\-|]+\|?$", ln.strip()):
                add("表格", f, i + 1, f"该行列数 {cols - 1} 与表头 {header_cols - 1} 不等")
        else:
            in_tbl = False

    # ---------- 6. 文字瑕疵
    for i, ln in enumerate(lines):
        if re.search(r"[，。；：]{2,}", ln):
            add("标点", f, i + 1, "连续标点：" + ln.strip()[:40])
        if re.search(r"（\s*）|\(\s*\)", ln):
            add("标点", f, i + 1, "空括号")
        if ln.count("**") % 2:
            add("标记", f, i + 1, "** 未配对：" + ln.strip()[:50])

    # ---------- 7. HTML 存在与新鲜度
    if f != "13-05_推进登记.md":
        if f[:-3] not in htmls:
            add("HTML", f, 0, "缺少审阅用 html")
        elif os.path.getmtime(os.path.join(SEC, f)) > \
                os.path.getmtime(os.path.join(HTML, f[:-3] + ".html")) + 1:
            add("HTML", f, 0, "html 比 md 旧")

# ---------- 8. 图片重复使用
for base, owners in used_fig.items():
    if len(owners) > 1:
        add("图复用", ",".join(sorted(set(owners))), 0, f"{base} 被多节引用")

unused = sorted(figs - set(used_fig))
print(f"md={len(mds)}  html={len(htmls)}  figures={len(figs)}  "
      f"未引用图={len(unused)}")
if unused:
    print("未引用图：", ", ".join(unused))

print(f"\n问题 {len(issues)} 条")
for kind, f, line, msg in issues:
    print(f"[{kind}] {f}:{line}  {msg}")
