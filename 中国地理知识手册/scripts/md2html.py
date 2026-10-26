# -*- coding: utf-8 -*-
"""把 sections/*.md 转为自包含的审阅用 HTML（图片内嵌 base64）。

用法：
    python md2html.py                 # 转换 sections/ 下所有 md
    python md2html.py 01-01           # 只转换文件名含指定关键字的 md
"""
import base64
import os
import re
import sys

import markdown

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECTIONS = os.path.join(ROOT, "sections")
HTML = os.path.join(ROOT, "html")

CSS = """
:root { --accent: #8e2b20; --text: #2c3e50; }
* { box-sizing: border-box; }
body {
  font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", sans-serif;
  color: var(--text); background: #f5f4f0; margin: 0; line-height: 1.85;
}
article {
  max-width: 960px; margin: 24px auto; background: #fff;
  padding: 48px 56px 56px; box-shadow: 0 1px 6px rgba(0,0,0,.12);
}
h1 {
  font-size: 1.7em; color: var(--accent);
  border-bottom: 3px solid var(--accent); padding-bottom: 10px;
}
h2 { font-size: 1.25em; color: var(--accent); margin-top: 2em;
     border-left: 5px solid var(--accent); padding-left: 10px; }
blockquote {
  margin: 1.2em 0; padding: 10px 18px; background: #fdf6ec;
  border-left: 4px solid #c8a15a; color: #6b5b3e; font-size: .95em;
}
table { border-collapse: collapse; width: 100%; margin: 1.2em 0; font-size: .93em; }
th, td { border: 1px solid #d5d0c8; padding: 7px 10px; text-align: left; }
th { background: #f0e9df; color: #5a4a33; }
tr:nth-child(even) td { background: #faf9f6; }
img { max-width: 100%; display: block; margin: 1.6em auto .4em;
      border: 1px solid #e3e0da; box-shadow: 0 2px 8px rgba(0,0,0,.08); }
p > strong:only-child { display: block; text-align: center; color: #555;
      font-weight: 600; margin-bottom: 1.6em; }
ol, ul { padding-left: 1.6em; }
li { margin: .3em 0; }
hr { border: none; border-top: 1px dashed #ccc; margin: 2.2em 0; }
code { background: #f0ede8; padding: 1px 5px; border-radius: 3px; }
@media print { body { background:#fff; } article { box-shadow:none; margin:0; max-width:none; } }
"""


def img_to_data_uri(match):
    alt, path = match.group(1), match.group(2)
    full = os.path.normpath(os.path.join(SECTIONS, path))
    if not os.path.exists(full):
        return match.group(0)
    with open(full, "rb") as f:
        uri = "data:image/png;base64," + base64.b64encode(f.read()).decode()
    return f"![{alt}](<{uri}>)" if False else f'<img src="{uri}" alt="{alt}" />'


def convert(md_path):
    with open(md_path, encoding="utf-8") as f:
        text = f.read()
    # 图片先替换为内嵌 <img>
    text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", img_to_data_uri, text)
    body = markdown.markdown(text, extensions=["tables", "sane_lists"])
    title = os.path.basename(md_path).rsplit(".", 1)[0]
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{CSS}</style>
</head>
<body>
<article>
{body}
</article>
</body>
</html>"""
    out = os.path.join(HTML, os.path.basename(md_path).rsplit(".", 1)[0] + ".html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    return out


if __name__ == "__main__":
    key = sys.argv[1] if len(sys.argv) > 1 else ""
    os.makedirs(HTML, exist_ok=True)
    mds = sorted(f for f in os.listdir(SECTIONS) if f.endswith(".md") and key in f)
    for f in mds:
        print("->", convert(os.path.join(SECTIONS, f)))
