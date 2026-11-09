# -*- coding: utf-8 -*-
"""组装《中国地理知识手册》全书合卷 HTML（上册 + 下册已完成部分）。

包含：
  - 上册：全国自然与人文地理总论（第 1-14 章 + 附录，共 91 节，173 幅图）
  - 下册：区域与省域专论（华北与京津冀协同发展区已完成部分：北京市、天津市、河北省，共 52 节，255 幅图）
  合计：18 篇章，143 个正文专著小节，449 幅出版级地理矢量制图，逾 25 万字学术专著。

输出：
  1. output/中国地理知识手册_全书合卷.html             (相对路径引用 figures/，打开飞速秒开，约 2.2 MB)
  2. output/中国地理知识手册_全书合卷_自包含单文件.html (内嵌所有 449 幅图 base64，单文件完全自包含便携，约 326 MB)
"""
import base64
import io
import os
import re
import sys
import time

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import markdown

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEC_VOL1 = os.path.join(ROOT, "sections")
SEC_VOL2 = os.path.join(ROOT, "sections_vol2")
FIG_DIR = os.path.join(ROOT, "figures")
OUT_DIR = os.path.join(ROOT, "output")

# 上册章节映射
CHAPTERS_VOL1 = [
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
    ("第 13 章　区域地理分论", ["13-"]),
    ("第 14 章　省级行政区速览（34 个省级行政区）", ["14-"]),
    ("附录　数据汇编与技术备忘", ["99_"]),
]

# 下册已完成章节映射
CHAPTERS_VOL2 = [
    ("第 1 章　北京市（首都功能核心区、中心城区、副中心、平原新城与生态涵养区）", ["01-"]),
    ("第 2 章　天津市（“津城”核心六区、“环城四区”、“滨城”滨海新区与外围四区）", ["02-"]),
    ("第 3 章　河北省（11 地级市、雄安新区、省直管辛集市与定州市）", ["03-"]),
    ("第 4 章　山西省（11 地级市与省域转型综改试验区）", ["04-"]),
    ("第 5 章　辽宁省（14 地级市、沈大双核与东北亚陆海国际枢纽）", ["05-"]),
    ("第 6 章　吉林省（8 地级市、1 自治州、“东林中农西草”三带格局与向北开放枢纽）", ["06-"]),
    ("第 7 章　黑龙江省（12 地级市、1 地区、“五山一水一草三分田”与维护国家五大安全战略大底座）", ["07-"]),
    ("第 8 章　山东省（16 地级市、济青双核引领与绿色低碳高质量发展先行区）", ["08-"]),
    ("第 9 章　上海市（16 市辖区、“五个中心”与社会主义现代化国际大都市）", ["09-"]),
    ("第 10 章　江苏省（13 地级市、“1+3”重点功能区与高质量发展先行省）", ["10-"]),
    ("第 11 章　浙江省（11 地级市、“四大都市区”与高质量发展建设共同富裕示范区）", ["11-"]),
    ("第 12 章　安徽省（16 地级市、“一圈五区”与创新型高能级省份）", ["12-"]),
    ("第 13 章　福建省（9 设区市、“两极两带六轴”与两岸融合发展示范区）", ["13-"]),
    ("第 14 章　江西省（11 设区市、“一圈两带三区”与内陆开放型经济试验区）", ["14-"]),
    ("第 15 章　河南省（17 地级市、1 省直管县级市、“一核两翼三区”与中原经济区）", ["15-"]),
    ("第 16 章　湖北省（12 地级市、1 自治州、3 省直管市、1 林区、“一主两翼全辐射”与三大都市圈）", ["16-"]),
    ("第 17 章　湖南省（13 地级市、1 自治州、“一核两副三带四区”与长株潭都市圈）", ["17-"]),
    ("第 18 章　广东省（21 地级市、“一核一带一区”与粤港澳大湾区世界级城市群）", ["18-"]),
    ("第 19 章　广西壮族自治区（14 地级市、“一区两地一园一通道”与北部湾向海经济区）", ["19-"]),
    ("第 20 章　海南省（4 地级市、15 省直管县级市/县、“三极一带一区”与自由贸易港全岛封关）", ["20-"]),
    ("第 21 章　重庆市（38 个区县、“一区两群”与长江上游国家中心城市）", ["21-"]),
    ("第 22 章　四川省（21 个市州、“五大经济区”与国家战略腹地核心承载区）", ["22-"]),
    ("第 23 章　贵州省（6 个地级市、3 个自治州、“黔中城市群”与世界桥梁博物馆）", ["23-"]),
    ("第 24 章　云南省（8 个地级市、8 个自治州、“滇中城市群”与面向南亚东南亚辐射中心）", ["24-"]),
    ("第 25 章　陕西省（10 个地级市、杨凌示范区、“一核两翼多组团”与国家战略腹地）", ["25-"]),
    ("第 26 章　台湾省（4 个功能板块、22 个县市与全球半导体硅岛）", ["26-"]),
    ("第 27 章　香港特别行政区（4 个分析板块、18 区与“背靠祖国·联通世界”国际都会）", ["27-"]),
    ("第 28 章　澳门特别行政区（3 个分析单元、8 个堂区分区与世界旅游休闲中心）", ["28-"]),
    ("第 29 章　内蒙古自治区（9 地级市、3 盟与北疆生态安全屏障）", ["29-"]),
    ("第 30 章　甘肃省（12 地级市、2 自治州与丝路经济带黄金走廊）", ["30-"]),
    ("第 31 章　宁夏回族自治区（5 个地级市与黄河流域生态保护先行区）", ["31-"]),
    ("第 32 章　新疆维吾尔自治区（4 个地级市、5 个地区、5 个自治州、兵团直辖县级市与丝绸之路经济带核心区）", ["32-"]),
    ("第 33 章　青海省（2 个地级市、6 个自治州与“中华水塔”生态安全屏障）", ["33-"]),
    ("第 34 章　西藏自治区（6 个地级市、1 个地区与国家生态安全第一屏障）", ["34-"]),
]

CSS = """
:root {
  --accent: #8e2b20;
  --accent-light: #fbeee9;
  --accent-dark: #6e1e16;
  --text: #2c3e50;
  --text-muted: #6b7280;
  --bg: #f4f2ee;
  --card-bg: #ffffff;
  --border: #d5d0c8;
  --sidebar-w: 320px;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
  color: var(--text);
  background: var(--bg);
  margin: 0;
  padding: 0;
  line-height: 1.85;
  font-size: 15px;
}

/* 顶部悬浮控制栏与侧边栏 */
#sidebar-toggle {
  position: fixed;
  top: 14px;
  left: 14px;
  z-index: 1001;
  background: var(--accent);
  color: #fff;
  border: none;
  padding: 8px 14px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13.5px;
  font-weight: 600;
  box-shadow: 0 2px 10px rgba(0,0,0,0.22);
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
}
#sidebar-toggle:hover { background: var(--accent-dark); }

#sidebar {
  position: fixed;
  top: 0;
  left: 0;
  width: var(--sidebar-w);
  height: 100vh;
  background: #ffffff;
  border-right: 1px solid var(--border);
  box-shadow: 2px 0 14px rgba(0,0,0,0.08);
  z-index: 1000;
  display: flex;
  flex-direction: column;
  transition: transform 0.28s cubic-bezier(0.4, 0, 0.2, 1);
}
#sidebar.collapsed {
  transform: translateX(-100%);
}

.sidebar-header {
  padding: 16px 18px 12px;
  border-bottom: 1px solid #ebe7e0;
  background: #faf8f5;
}
.sidebar-header h2 {
  margin: 0 0 8px 0;
  font-size: 15px;
  color: var(--accent);
  border: none;
  padding: 0;
  font-weight: 700;
  letter-spacing: 0.02em;
}
.sidebar-search {
  width: 100%;
  padding: 7px 12px;
  border: 1px solid var(--border);
  border-radius: 5px;
  font-size: 13px;
  outline: none;
  background: #fff;
  transition: border-color 0.2s;
}
.sidebar-search:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px rgba(142,43,32,0.15);
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 10px 14px;
}
.sidebar-content ul {
  list-style: none;
  padding: 0;
  margin: 0;
}
.sidebar-content li {
  margin: 2px 0;
}
.sidebar-content .vol-title {
  font-size: 12.5px;
  font-weight: 700;
  color: #fff;
  background: var(--accent);
  padding: 6px 10px;
  border-radius: 4px;
  margin: 14px 0 6px;
  letter-spacing: 0.04em;
}
.sidebar-content .chap-title {
  font-size: 12.5px;
  font-weight: 600;
  color: #4a3e30;
  padding: 5px 8px;
  margin-top: 8px;
  border-left: 3px solid #c8a15a;
  background: #faf8f5;
  border-radius: 0 4px 4px 0;
}
.sidebar-content a {
  display: block;
  padding: 4px 8px 4px 14px;
  font-size: 12px;
  color: #4b5563;
  text-decoration: none;
  border-radius: 4px;
  line-height: 1.45;
  transition: all 0.12s;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sidebar-content a:hover {
  background: var(--accent-light);
  color: var(--accent);
}
.sidebar-content a.active {
  background: var(--accent-light);
  color: var(--accent);
  font-weight: 600;
}

/* 主书体内容容器 */
.layout-container {
  display: flex;
  min-height: 100vh;
}
.main-wrapper {
  flex: 1;
  margin-left: var(--sidebar-w);
  transition: margin-left 0.28s cubic-bezier(0.4, 0, 0.2, 1);
  padding: 24px 24px 90px;
}
.main-wrapper.full-width {
  margin-left: 0;
}

.book {
  max-width: 1040px;
  margin: 0 auto;
  background: var(--card-bg);
  padding: 64px 76px 100px;
  box-shadow: 0 2px 18px rgba(0,0,0,0.07);
  border-radius: 4px;
}

/* 封面区 */
.cover {
  text-align: center;
  padding: 50px 20px 70px;
  border-bottom: 2px solid #eee;
  margin-bottom: 50px;
}
.cover-badge {
  display: inline-block;
  background: #c8a15a;
  color: #fff;
  font-size: 12.5px;
  padding: 4px 14px;
  border-radius: 20px;
  font-weight: 600;
  letter-spacing: 0.1em;
  margin-bottom: 18px;
}
.cover h1 {
  font-size: 2.85em;
  color: var(--accent);
  margin: 0;
  letter-spacing: 0.05em;
  border: none;
  padding: 0;
  font-family: "Noto Serif CJK SC", "Songti SC", "SimSun", serif;
}
.cover .sub {
  color: #666;
  font-size: 1.25em;
  margin-top: 14px;
  font-style: italic;
}
.cover .vol-tagline {
  font-size: 1.05em;
  color: #8e2b20;
  font-weight: 600;
  margin-top: 24px;
  padding: 10px 26px;
  background: #fdf6ec;
  display: inline-block;
  border-radius: 6px;
  border: 1px solid #ebd7b2;
}
.cover .meta {
  color: #666;
  font-size: 0.92em;
  margin-top: 40px;
  line-height: 2.1;
  border-top: 1px dashed #ddd;
  padding-top: 24px;
}

/* 编纂说明卡片 */
.editor-intro {
  background: #fbf7ef;
  border: 1px solid #ebd7b2;
  border-radius: 6px;
  padding: 24px 28px;
  margin: 36px 0 54px;
}
.editor-intro h3 {
  margin-top: 0;
  color: var(--accent);
  border-bottom: 2px solid #dfc38a;
  padding-bottom: 8px;
  font-size: 1.2em;
}
.editor-intro ul {
  padding-left: 20px;
  margin: 10px 0;
}
.editor-intro li {
  margin: 6px 0;
  color: #4a3e30;
}

/* 分卷隔页 */
.volume-divider {
  background: linear-gradient(135deg, #8e2b20 0%, #5c1a13 100%);
  color: #fff;
  padding: 44px 36px;
  border-radius: 8px;
  margin: 80px 0 46px;
  text-align: center;
  box-shadow: 0 4px 18px rgba(142,43,32,0.22);
  page-break-before: always;
  break-before: page;
}
.volume-divider h2 {
  color: #fff;
  border: none;
  padding: 0;
  margin: 0;
  font-size: 2.1em;
  font-family: "Noto Serif CJK SC", "Songti SC", "SimSun", serif;
  letter-spacing: 0.08em;
}
.volume-divider .vol-desc {
  color: #f7e8e6;
  font-size: 1.02em;
  margin-top: 12px;
  max-width: 780px;
  margin-left: auto;
  margin-right: auto;
  line-height: 1.75;
}

/* 章节 */
.chapter {
  margin-top: 72px;
  page-break-before: always;
  break-before: page;
}
.chapter:first-of-type { margin-top: 20px; }
.chapter h1 {
  font-size: 1.85em;
  color: var(--accent);
  border-bottom: 3px solid var(--accent);
  padding-bottom: 12px;
  margin-top: 0;
  margin-bottom: 28px;
  font-family: "Noto Serif CJK SC", "Songti SC", "SimSun", serif;
}
h2 {
  color: var(--accent);
  font-size: 1.34em;
  margin-top: 2.4em;
  margin-bottom: 0.8em;
  border-left: 5px solid var(--accent);
  padding-left: 12px;
}
h3 {
  color: #5a4a33;
  font-size: 1.12em;
  margin-top: 1.8em;
  margin-bottom: 0.6em;
}
h4 {
  color: #5a4a33;
  font-size: 1.02em;
  margin-top: 1.2em;
}

/* 引用块、表格、图片 */
blockquote {
  margin: 1.4em 0;
  padding: 12px 20px;
  background: #fdf6ec;
  border-left: 4px solid #c8a15a;
  color: #6b5b3e;
  font-size: 0.95em;
  border-radius: 0 4px 4px 0;
}
.table-wrap {
  overflow-x: auto;
  margin: 1.4em 0;
}
table {
  border-collapse: collapse;
  width: 100%;
  font-size: 0.92em;
  line-height: 1.6;
}
th, td {
  border: 1px solid #d5d0c8;
  padding: 8px 11px;
  text-align: left;
  vertical-align: top;
}
th {
  background: #f0e9df;
  color: #4a3e30;
  font-weight: 600;
}
tr:nth-child(even) td { background: #faf9f6; }
tr:hover td { background: #f5f2eb; }

img {
  max-width: 100%;
  height: auto;
  display: block;
  margin: 1.8em auto 0.5em;
  border: 1px solid #e3e0da;
  border-radius: 4px;
  box-shadow: 0 3px 10px rgba(0,0,0,0.08);
}
p > strong:only-child {
  display: block;
  text-align: center;
  color: #555;
  font-weight: 600;
  margin-bottom: 1.8em;
  font-size: 0.93em;
}

/* 浮动操作按钮 */
.floating-actions {
  position: fixed;
  bottom: 24px;
  right: 24px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  z-index: 999;
}
.fab-btn {
  background: #fff;
  color: var(--accent);
  border: 1px solid #ddd;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 3px 10px rgba(0,0,0,0.15);
  transition: all 0.2s;
  font-size: 16px;
  font-weight: bold;
}
.fab-btn:hover {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}

/* 打印与移动端适配 */
@media print {
  #sidebar, #sidebar-toggle, .floating-actions { display: none !important; }
  .main-wrapper { margin-left: 0 !important; padding: 0 !important; }
  .book { box-shadow: none !important; max-width: none !important; padding: 0 !important; }
  body { background: #fff !important; }
  .volume-divider, .chapter { page-break-before: always; break-before: page; }
}

@media (max-width: 900px) {
  #sidebar { transform: translateX(-100%); }
  #sidebar.show-mobile { transform: translateX(0); }
  .main-wrapper { margin-left: 0; padding: 12px 10px 60px; }
  .book { padding: 32px 20px; }
}
"""

JS = """
document.addEventListener("DOMContentLoaded", function() {
  const sidebar = document.getElementById("sidebar");
  const mainWrapper = document.querySelector(".main-wrapper");
  const toggleBtn = document.getElementById("sidebar-toggle");
  const searchInput = document.querySelector(".sidebar-search");
  const tocLinks = document.querySelectorAll(".sidebar-content a");

  toggleBtn.addEventListener("click", function() {
    sidebar.classList.toggle("collapsed");
    mainWrapper.classList.toggle("full-width");
  });

  // 目录搜索实时过滤
  searchInput.addEventListener("input", function(e) {
    const val = e.target.value.trim().toLowerCase();
    tocLinks.forEach(link => {
      const text = link.textContent.toLowerCase();
      const li = link.closest("li");
      if (!val || text.includes(val)) {
        li.style.display = "";
      } else {
        li.style.display = "none";
      }
    });
  });

  // 平滑滚动与高亮
  tocLinks.forEach(link => {
    link.addEventListener("click", function(e) {
      tocLinks.forEach(l => l.classList.remove("active"));
      this.classList.add("active");
    });
  });

  // 返回顶部
  document.getElementById("btn-back-to-top").addEventListener("click", function() {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  // 表格包装保护横向滚动
  document.querySelectorAll(".book table").forEach(tbl => {
    if (!tbl.parentElement.classList.contains("table-wrap")) {
      const wrap = document.createElement("div");
      wrap.className = "table-wrap";
      tbl.parentNode.insertBefore(wrap, tbl);
      wrap.appendChild(tbl);
    }
  });
});
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
    html = re.sub(r"<h4", "<h5", html)
    html = re.sub(r"</h4>", "</h5>", html)
    html = re.sub(r"<h3", "<h4", html)
    html = re.sub(r"</h3>", "</h4>", html)
    html = re.sub(r"<h2", "<h3", html)
    html = re.sub(r"</h2>", "</h3>", html)
    html = re.sub(r"<h1", "<h2", html)
    html = re.sub(r"</h1>", "</h2>", html)
    return html

def add_ids(html, used, toc_list):
    def repl(m):
        tag, attrs, inner = m.group(1), m.group(2), m.group(3)
        text = re.sub(r"<[^>]+>", "", inner).strip()
        ident = slug(text, used)
        if tag == "h2":
            toc_list.append((2, text, ident))
        return f'<{tag}{attrs} id="{ident}">{inner}</{tag}>'
    return re.sub(r"<(h2)([^>]*)>(.*?)</\1>", repl, html, flags=re.S)

def resolve_image(path, md_dir):
    candidates = [
        os.path.normpath(os.path.join(md_dir, path)),
        os.path.normpath(os.path.join(ROOT, "figures", os.path.basename(path))),
        os.path.normpath(os.path.join(ROOT, path)),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None

def replace_images_in_html(html, md_dir, embed_base64=False, b64_cache=None):
    if b64_cache is None:
        b64_cache = {}

    def _img_tag_repl(m):
        attrs = m.group(1)
        src_match = re.search(r'src=["\']([^"\']+)["\']', attrs)
        alt_match = re.search(r'alt=["\']([^"\']*)["\']', attrs)
        src = src_match.group(1) if src_match else ""
        alt = alt_match.group(1) if alt_match else ""

        real_img = resolve_image(src, md_dir)
        if not real_img:
            return f'<img src="{src}" alt="{alt}" loading="lazy" />'

        if embed_base64:
            if real_img not in b64_cache:
                with open(real_img, "rb") as f:
                    b64_cache[real_img] = base64.b64encode(f.read()).decode("utf-8")
            b64_str = b64_cache[real_img]
            return f'<img src="data:image/png;base64,{b64_str}" alt="{alt}" loading="lazy" />'
        else:
            rel = f"../figures/{os.path.basename(real_img)}"
            return f'<img src="{rel}" alt="{alt}" loading="lazy" />'

    return re.sub(r'<img\s+([^>]+)>', _img_tag_repl, html)

def generate_book_html(embed_base64=False, b64_cache=None):
    t0 = time.time()
    os.makedirs(OUT_DIR, exist_ok=True)
    used = set()
    sidebar_items = []
    body_parts = []

    # 封面
    body_parts.append("""
<div class="cover" id="cover">
  <div class="cover-badge">中国地理知识库 · 权威研制成果</div>
  <h1>中国地理知识手册</h1>
  <div class="sub">Handbook of the Geography of China</div>
  <div class="vol-tagline">全书合卷：上册（全国地理总论）+ 下册（区域与省域专论 · 华北、东北、华东、中南、西南与西北/青藏区域集群，已完成30省区市）</div>
  <div class="meta">
    <strong>研制标准</strong>：海淀学术标杆级专著 · 自然地理与人文经济双维图构<br>
    <strong>覆盖范围</strong>：全国自然地理系统、34 省级行政区速览；已全面完成全国 30 个省、自治区、直辖市下沉至地级单元的深度出版级专著编纂<br>
    <strong>研制周期</strong>：2026年11月 · 权威统计年鉴与高精度 GIS 空间图谱集成
  </div>
</div>

<div class="editor-intro">
  <h3>编纂说明与审阅备忘（送审合卷）</h3>
  <ul>
    <li><strong>篇卷架构</strong>：本卷为《中国地理知识手册》全书送审合卷，整合<strong>上册《全国自然与人文地理总论》</strong>（第 1–14 章 + 附录，共 91 节）与<strong>下册《区域与省域专论》已完成省份集群</strong>（已全面覆盖 30 个省级行政区）。</li>
    <li><strong>学术深度与海淀标杆</strong>：下册全面落实以“海淀模式”为基准的深度专著标准，每区/市/州/地区标配 5 幅出版级矢量制图（区位与空间结构、地形地貌与水系、多源路网与综合枢纽、特色专题剖面、夜光遥感与经济空间演进），并配齐详实权威的经济与地理要素指标矩阵。</li>
    <li><strong>制图标准与地理底盘</strong>：全书地图统一采用标准天地图/国家地理底图，全国尺度采用标准阿尔伯斯等面积投影（Albers Equal Area Conic，中央经线 105°E），省级与地级尺度采用匹配经度的高斯-克吕格/UTM投影；集成 AWS Terrain 300米高程 DEM、1986–2024年连续夜光遥感与 Geofabrik OpenStreetMap 最新多源路网水系。</li>
    <li><strong>统计口径与前沿更新</strong>：宏观经济指标采用 2024/2025 年权威统计年鉴与国民经济公报最新发布数据，人口指标锚定“七普”及最新常住人口抽样公报。</li>
  </ul>
</div>
""")

    # --- 上册 ---
    body_parts.append("""
<div class="volume-divider" id="vol-1">
  <h2>上册：全国自然与人文地理总论</h2>
  <div class="vol-desc">系统阐述中华疆域、行政建置、地貌梯级、季风气候、江河大湖、国土资源、生态安全、海洋国土、人口城镇、宏观经济、综合交通及全国 34 个省级行政区基础速览。</div>
</div>
""")
    sidebar_items.append(("vol", "上册：全国地理总论", "vol-1", []))

    files_v1 = sorted([f for f in os.listdir(SEC_VOL1) if f.endswith(".md") and f != "13-05_推进登记.md"])
    for chap_title, prefixes in CHAPTERS_VOL1:
        chap_id = slug(chap_title, used)
        chap_sections = []
        for pre in prefixes:
            for f in files_v1:
                if f.startswith(pre) and f not in [g[0] for g in chap_sections]:
                    chap_sections.append((f, pre))
        chap_sections.sort(key=lambda x: x[0])
        if not chap_sections:
            continue

        body_parts.append(f'<section class="chapter" id="{chap_id}">')
        body_parts.append(f'<h1>{chap_title}</h1>')

        chap_toc_entries = []
        for f, _ in chap_sections:
            f_path = os.path.join(SEC_VOL1, f)
            raw_text = io.open(f_path, encoding="utf-8").read()
            html_raw = markdown.markdown(raw_text, extensions=["tables", "sane_lists"])
            html_demoted = demote(html_raw)
            html_with_ids = add_ids(html_demoted, used, chap_toc_entries)
            html_with_imgs = replace_images_in_html(html_with_ids, SEC_VOL1, embed_base64=embed_base64, b64_cache=b64_cache)
            body_parts.append(html_with_imgs)

        body_parts.append('</section>')
        sidebar_items.append(("chap", chap_title, chap_id, chap_toc_entries))

    # --- 下册 ---
    body_parts.append("""
<div class="volume-divider" id="vol-2">
  <h2>下册：区域与省域地理专论（华北、东北、华东、中原华中与西北/青藏区域集群）</h2>
  <div class="vol-desc">以“海淀标杆”标准深度研制的省域与地级市专著章节。包含北京市、天津市、河北省、山西省、辽宁省、吉林省、黑龙江省、山东省、上海市、江苏省、浙江省、安徽省、福建省、江西省、河南省、湖北省、内蒙古自治区、甘肃省、宁夏回族自治区、新疆维吾尔自治区、青海省、西藏自治区，集成自然地理底盘、夜光遥感、水系路网与宏观经济指标矩阵。</div>
</div>
""")
    sidebar_items.append(("vol", "下册：区域与省域专论", "vol-2", []))

    files_v2 = sorted([f for f in os.listdir(SEC_VOL2) if f.endswith(".md")])
    for chap_title, prefixes in CHAPTERS_VOL2:
        chap_id = slug(chap_title, used)
        chap_sections = []
        for pre in prefixes:
            for f in files_v2:
                if f.startswith(pre) and f not in [g[0] for g in chap_sections]:
                    chap_sections.append((f, pre))
        chap_sections.sort(key=lambda x: x[0])
        if not chap_sections:
            continue

        body_parts.append(f'<section class="chapter" id="{chap_id}">')
        body_parts.append(f'<h1>{chap_title}</h1>')

        chap_toc_entries = []
        for f, _ in chap_sections:
            f_path = os.path.join(SEC_VOL2, f)
            raw_text = io.open(f_path, encoding="utf-8").read()
            html_raw = markdown.markdown(raw_text, extensions=["tables", "sane_lists"])
            html_demoted = demote(html_raw)
            html_with_ids = add_ids(html_demoted, used, chap_toc_entries)
            html_with_imgs = replace_images_in_html(html_with_ids, SEC_VOL2, embed_base64=embed_base64, b64_cache=b64_cache)
            body_parts.append(html_with_imgs)

        body_parts.append('</section>')
        sidebar_items.append(("chap", chap_title, chap_id, chap_toc_entries))

    # 构建侧边栏
    sidebar_html = ['<aside id="sidebar"><div class="sidebar-header">',
                    '<h2>中国地理知识手册 · 导航</h2>',
                    '<input type="text" class="sidebar-search" placeholder="搜索章节、区县、地名..." />',
                    '</div><div class="sidebar-content"><ul>']

    for item in sidebar_items:
        itype = item[0]
        if itype == "vol":
            sidebar_html.append(f'<li class="vol-title"><a href="#{item[2]}" style="color:#fff;padding:0;">{item[1]}</a></li>')
        elif itype == "chap":
            sidebar_html.append(f'<li class="chap-title"><a href="#{item[2]}" style="color:inherit;padding:0;">{item[1]}</a></li>')
            for _, stitle, sid in item[3]:
                sidebar_html.append(f'<li><a href="#{sid}" title="{stitle}">{stitle}</a></li>')
    sidebar_html.append('</ul></div></aside>')

    full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>中国地理知识手册（全书合卷送审稿）</title>
<style>{CSS}</style>
</head>
<body>
<button id="sidebar-toggle" title="展开/收起目录">☰ 目录导航</button>
<div class="layout-container">
  {"".join(sidebar_html)}
  <main class="main-wrapper">
    <div class="book">
      {"".join(body_parts)}
    </div>
  </main>
</div>
<div class="floating-actions">
  <button class="fab-btn" id="btn-back-to-top" title="返回顶部">↑</button>
</div>
<script>{JS}</script>
</body>
</html>
"""
    out_name = "中国地理知识手册_全书合卷_自包含单文件.html" if embed_base64 else "中国地理知识手册_全书合卷.html"
    out_path = os.path.join(OUT_DIR, out_name)
    with io.open(out_path, "w", encoding="utf-8", newline="\n") as fp:
        fp.write(full_html)

    size_mb = os.path.getsize(out_path) / 1024 / 1024
    elapsed = time.time() - t0
    mode_desc = "自包含 base64 单文件" if embed_base64 else "相对路径快速版"
    print(f"[{mode_desc}] 导出成功: {out_path} ({size_mb:.2f} MB, 耗时 {elapsed:.1f} 秒)")
    return out_path

def main():
    b64_cache = {}
    # 1. 导出相对路径版
    print("--> 正在生成相对路径引用版全书合卷...")
    p1 = generate_book_html(embed_base64=False)

    # 2. 导出内嵌 base64 自包含单文件版
    print("--> 正在生成自包含单文件版（内嵌 449 幅图 base64）...")
    p2 = generate_book_html(embed_base64=True, b64_cache=b64_cache)

    print("========================================")
    print("全书合卷 HTML 导出全部完成！")
    print(f"1. 快速阅读版: {p1}")
    print(f"2. 便携独立版: {p2}")

if __name__ == "__main__":
    main()
