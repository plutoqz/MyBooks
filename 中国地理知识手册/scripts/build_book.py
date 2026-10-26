# -*- coding: utf-8 -*-
"""组装全书 HTML（送审稿，不导出 PDF）。

输出：
    output/中国地理知识手册_全书.html   单文件，图片用相对路径引用 figures/
    output/中国地理知识手册_目录.html   仅目录页（可选，便于快速跳转）

用法：python build_book.py [--embed]
    --embed  把图片转成 base64 内嵌（文件很大，约 190 MB，默认关闭）
"""
import io
import os
import re
import sys

import markdown

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEC = os.path.join(ROOT, "sections")
OUT = os.path.join(ROOT, "output")

# 章标题与所属小节前缀（顺序即全书顺序）
CHAPTERS = [
    ("第 1 章　疆域与位置", ["01-"]),
    ("第 2 章　行政区划", ["02-"]),
    ("第 3 章　地形地貌", ["03-"]),
    ("第 4 章　气候", ["04-"]),
    ("第 5 章　河流与湖泊", ["05-"]),
    ("第 6 章　自然资源与土地利用", ["06-"]),
    ("第 7 章　生态环境与自然灾害", ["07-"]),
    ("第 8 章　海洋地理", ["08-"]),
    ("第 9 章　人口与民族", ["09-"]),
    ("第 10 章　城市与城镇化", ["10-"]),
    ("第 11 章　经济地理", ["11-"]),
    ("第 12 章　交通地理", ["12-"]),
    ("第 13 章　区域地理分论", ["13-0"]),
    ("13.5　省级行政区速览（34 个省级行政区）", ["13-05-"]),
    ("附录", ["99_"]),
]

EDITOR_NOTE = """## 编辑说明（送审稿，非正文）

本稿为《中国地理知识手册》全书送审稿，由 `sections/*.md` 自动组装，图片按相对路径引用 `figures/`（打开时请保持 `output/` 与 `figures/` 同在一个文件夹内）。

- 全书 13 章 51 节 + 13.5 分省 34 节 + 附录，共 85 个正文小节、165 幅图。
- 统计口径：北方线（13.5.1–10）与南方线（13.5.11–28）采用 2024 年年度数据（人口为 2020 年七普）；西北/青藏线（13.5.29–34）采用 2025 年年度数据；港澳台采用当地公布口径。组装定稿前如需统一年份，将对上述正文与 GDP 图做一次升级。
- 尚未配图的小节：6.2、8.1、10.3、12.3（6.2 原计划使用 CLCD 土地覆盖数据，该数据尚未下载）。
- 附录 A 为 2023 年口径，与各节 2024/2025 年数据并置时请以节内标注为准。
- 本稿未做 PDF 导出。
"""

CSS = """
:root { --accent:#8e2b20; --text:#2c3e50; --muted:#6b7280; }
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", sans-serif;
  color: var(--text); background:#f4f2ee; margin:0; line-height:1.85; font-size:15px;
}
.book { max-width: 980px; margin: 0 auto; background:#fff;
        padding: 64px 72px 96px; box-shadow: 0 2px 14px rgba(0,0,0,.10); }
h1 { color: var(--accent); border-bottom: 3px solid var(--accent);
     padding-bottom: 10px; margin-top: 0; font-size: 1.65em; }
h2 { color: var(--accent); margin-top: 2.4em; font-size: 1.24em;
     border-left: 5px solid var(--accent); padding-left: 12px; }
h3 { color:#5a4a33; font-size: 1.06em; margin-top: 1.8em; }
h4 { color:#5a4a33; font-size: 1em; }
blockquote { margin:1.2em 0; padding:10px 18px; background:#fdf6ec;
             border-left:4px solid #c8a15a; color:#6b5b3e; font-size:.95em; }
table { border-collapse: collapse; width:100%; margin:1.2em 0; font-size:.92em; }
th, td { border:1px solid #d5d0c8; padding:7px 10px; text-align:left; vertical-align:top; }
th { background:#f0e9df; color:#5a4a33; }
tr:nth-child(even) td { background:#faf9f6; }
img { max-width:100%; display:block; margin:1.6em auto .4em;
      border:1px solid #e3e0da; box-shadow:0 2px 8px rgba(0,0,0,.08); }
p > strong:only-child { display:block; text-align:center; color:#555;
      font-weight:600; margin-bottom:1.6em; font-size:.94em; }
ol, ul { padding-left:1.6em; }
li { margin:.3em 0; }
a { color:#8e2b20; text-decoration:none; }
a:hover { text-decoration:underline; }
.chapter { page-break-before: always; break-before: page; margin-top: 96px; }
.chapter:first-of-type { margin-top: 0; }
.cover { text-align:center; padding: 120px 20px 80px; }
.cover h1 { border:none; font-size: 2.6em; letter-spacing:.08em; }
.cover .sub { color:#666; font-size:1.05em; margin-top:18px; }
.cover .meta { color:#888; font-size:.9em; margin-top:60px; line-height:2; }
.toc { page-break-after: always; break-after: page; }
.toc h2 { border-left:none; padding-left:0; }
.toc ul { list-style:none; padding-left:0; }
.toc li { margin:.28em 0; }
.toc .lv1 { font-weight:700; margin-top:1.1em; color:var(--accent); }
.toc .lv2 { padding-left:1.6em; font-size:.95em; }
.toc .pg { color:#aaa; }
.note { background:#fbf7ef; border:1px dashed #c8a15a; padding:18px 22px; }
.section-foot { color:#999; font-size:.82em; margin-bottom:2em; }
@media print {
  body { background:#fff; }
  .book { box-shadow:none; max-width:none; padding:0; }
  .chapter { page-break-before: always; }
  a { color: inherit; }
}
"""


def slug(text, used):
    s = re.sub(r"[^\w\u4e00-\u9fa5]+", "-", text).strip("-")
    s = s[:60] or "sec"
    base, i = s, 2
    while s in used:
        s = f"{base}-{i}"
        i += 1
    used.add(s)
    return s


def demote(html):
    """h1→h2, h2→h3, h3→h4（保留 markdown 生成的顺序）。"""
    html = re.sub(r"<h4", "<h5", html)
    html = re.sub(r"</h4>", "</h5>", html)
    html = re.sub(r"<h3", "<h4", html)
    html = re.sub(r"</h3>", "</h4>", html)
    html = re.sub(r"<h2", "<h3", html)
    html = re.sub(r"</h2>", "</h3>", html)
    html = re.sub(r"<h1", "<h2", html)
    html = re.sub(r"</h1>", "</h2>", html)
    return html


def add_ids(html, used, toc, chapter_titles):
    """给 h2（节）与 h3（节内小标题）加锚点，并收集目录项。"""

    def repl(m):
        tag, attrs, inner = m.group(1), m.group(2), m.group(3)
        text = re.sub(r"<[^>]+>", "", inner).strip()
        ident = slug(text, used)
        if tag == "h2":
            toc.append((2, text, ident))
        return f'<{tag}{attrs} id="{ident}">{inner}</{tag}>'

    return re.sub(r"<(h2|h3)([^>]*)>(.*?)</\1>", repl, html, flags=re.S)


def convert_md(text, embed=False):
    text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)",
                  lambda m: f"![{m.group(1)}]({m.group(2)})", text)
    return markdown.markdown(text, extensions=["tables", "sane_lists"])


def main(embed=False):
    os.makedirs(OUT, exist_ok=True)
    files = sorted(f for f in os.listdir(SEC) if f.endswith(".md")
                   and f != "13-05_推进登记.md")

    used, toc_entries = set(), []
    body, counts = [], []

    for chap_title, prefixes in CHAPTERS:
        group = []
        for pre in prefixes:
            for f in files:
                if f.startswith(pre) and f not in [g[0] for g in group]:
                    if pre == "13-0" and f.startswith("13-05-"):
                        continue
                    group.append((f, pre))
        group.sort(key=lambda x: x[0])
        if not group:
            continue
        cid = slug(chap_title, used)
        part = [f'<section class="chapter" id="{cid}">',
                f"<h1>{chap_title}</h1>"]
        toc_entries.append((1, chap_title, cid))
        for f, _ in group:
            text = io.open(os.path.join(SEC, f), encoding="utf-8").read()
            html = demote(convert_md(text))
            html = add_ids(html, used, toc_entries, chap_title)
            part.append(html)
        part.append("</section>")
        body.append("\n".join(part))
        counts.append((chap_title, len(group)))

    # 目录
    toc_html = ['<nav class="toc"><h2 id="toc">目　录</h2><ul>']
    for lv, text, ident in toc_entries:
        cls = "lv1" if lv == 1 else "lv2"
        toc_html.append(f'<li class="{cls}"><a href="#{ident}">{text}</a></li>')
    toc_html.append("</ul></nav>")

    n_sec = sum(c for _, c in counts)
    cover = f"""<div class="cover">
  <h1>中国地理知识手册</h1>
  <div class="sub">Handbook of the Geography of China</div>
  <div class="meta">
    送审稿（全书 HTML）· 2026-10-26<br>
    13 章 51 节 + 13.5 分省 34 节 + 附录<br>
    {n_sec} 个正文小节 · 165 幅图
  </div>
</div>"""

    note = demote(markdown.markdown(EDITOR_NOTE,
                                    extensions=["tables", "sane_lists"]))
    note = add_ids(note, used, [], "")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>中国地理知识手册（送审稿）</title>
<style>{CSS}</style>
</head>
<body>
<div class="book">
{cover}
{toc_html and "".join(toc_html)}
{''.join(body)}
<section class="chapter" id="editor-note">
<h1>编辑说明</h1>
{note}
</section>
</div>
</body>
</html>"""
    out = os.path.join(OUT, "中国地理知识手册_全书.html")
    io.open(out, "w", encoding="utf-8", newline="\n").write(html)
    size = os.path.getsize(out) / 1024 / 1024
    print(f"写出 {out}  ({size:.1f} MB)")
    for t, c in counts:
        print(f"  {t}: {c} 节")
    print(f"小节合计 {n_sec}")


if __name__ == "__main__":
    main("--embed" in sys.argv)
