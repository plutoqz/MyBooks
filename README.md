# 《中国地理知识手册》项目仓库

中国地理参考手册。上册包括全国自然与人文地理、区域分论和 34 个省级行政区速览，共 **90 节、204 幅图**；下册包括 **34 章、514 节、2400 幅图**。

仓库只收录**文稿、绘图脚本与成品图**；原始地理数据（约 1.5 GB，含 DEM 瓦片、边界矢量、统计底稿）不入库，获取方式见文末。

## 目录结构

```
中国地理知识手册/
├── 00_提纲与编写说明.md      编写提纲、章节规划、数据来源清单
├── sections/                 上册正文（Markdown），90 节及推进台账
├── sections_vol2/            下册正文（Markdown）
├── figures/                  成品图（上册 300 dpi PNG），文件名 fig{章}-{序}_名称.png
├── scripts/                  绘图脚本与构建脚本
│   ├── style.py              全书统一配色、字体、Albers 投影参数
│   ├── ch01_*.py … ch13_*.py 分章绘图脚本（需要 data/ 才能重跑）
│   ├── md2html.py            单节 Markdown → 自包含审阅 HTML
│   ├── build_book.py         全书 Markdown → 单文件 HTML（含目录）
│   ├── build_pdf.py          全书 HTML → PDF（调用本机 Edge/Chrome）
│   └── qa_structure.py       结构一致性检查（缺图、图号、表格、引用）
├── output/                   组装成果：中国地理知识手册_全书.html
└── data/                     （未入库）原始数据，见下方说明
```

## 快速开始

需要 Python 3.10+。

```bash
pip install -r 中国地理知识手册/requirements.txt
cd 中国地理知识手册

# 1) 生成全书 HTML → output/中国地理知识手册_全书.html
python scripts/build_book.py

# 2) 逐节生成审阅用 HTML → html/*.html（图片内嵌，单文件可直接发给他人）
python scripts/md2html.py            # 全部
python scripts/md2html.py 14-23      # 只转文件名含该关键字的节

# 3) 导出 PDF（不安装额外依赖，调用本机 Microsoft Edge / Chrome 无头模式）
python scripts/build_pdf.py
```

上册修订版入口为 `output/上册修订/`，包括 PDF、HTML、204 幅 PNG 及对应 PDF/SVG。排版与数据处理说明见该目录的 `README.md`。上册的独立构建命令：

```bash
python scripts/rebuild_volume1.py
python scripts/qa_volume1_exports.py
python scripts/build_volume1.py
```

PDF 正文采用 A4 竖向，宽图采用横向页面。HTML 与同目录下的 `figures/` 文件夹配套使用。

下册修订版入口为 `output/下册修订/`，包括 4642 页合订本、13 页典型样页、HTML、300 dpi PNG 及对应 PDF/SVG。正文单位与坐标采用 Unicode 排版，线框示意图采用表格或列表，宽表分组并重复行政单元列。下册的独立构建命令：

```bash
python scripts/audit_volume2.py
python scripts/volume2_text.py
python scripts/rebuild_volume2.py
python scripts/sync_volume2_captions.py
python scripts/qa_volume2_exports.py
python scripts/build_volume2.py
python scripts/review_volume2.py --book
python scripts/review_volume2.py --sample-book
python scripts/publish_volume2.py
```

`audit_volume2.py` 保存初始清单及备份；`volume2_text.py` 规范当前正文的排版。局部图件可用 `rebuild_volume2.py 脚本名 --code 行政代码 --pattern 文件名模式` 重建。统计图保留的观测记录位于修订目录 `qa/*.data.json`，可用 `refresh_volume2_charts.py` 单独排版。`publish_volume2.py` 将下册修订 PNG 同步至正文引用目录。数据口径及待核实事项见修订目录的 `README.md`。

`build_book.py` 生成的 HTML 通过相对路径引用 `figures/`，请保持 `output/` 与 `figures/` 在同级目录；用浏览器打开后可直接"打印 → 另存为 PDF"，`@media print` 已按章设置分页。

## 写作与制图约定

- **正文**：每节一个 `sections/NN-MM_名称.md`，首行为 `# 节号 标题`；图用相对路径 `../figures/…`；图下一行写 `**图 X-Y 说明**`。
- **地图**：统一 Albers 等积圆锥投影（中央经线 105°E，标准纬线 25°N/47°N），配色与字号集中在 `scripts/style.py`；中国全图须含南海诸岛与断续线，示意地图注明"不作为权属划界依据"。
- **图号**：`fig{章号}-{序号}`；省级行政区速览采用第 14 章图号，保留既有分块序号（北方 7–99、南方 101–199、西北/青藏 201–249），台账见 `sections/14-00_推进登记.md`。
- **数据年份**：13.5 北方线与南方线为 2024 年口径，西北/青藏线为 2025 年口径，港澳台为当地公布口径；组装定稿前如需统一年份，需同步修改正文与 GDP 图。
- **质检**：`python scripts/qa_structure.py` 可检查缺图、过期 HTML、图号与图注不符、表格列数、跨节引用等问题。

## 数据说明（未入库）

绘图脚本依赖 `data/` 下的原始数据，重跑前需按 `00_提纲与编写说明.md`「四、数据来源清单」自行下载，目录约定如下：

| 目录 | 内容 | 来源 |
|------|------|------|
| `data/boundaries/datav/` | 省、市级 GeoJSON（`{adcode}_full.json`） | 阿里云 DataV.GeoAtlas（2021.5） |
| `data/boundaries/natural_earth/` | 全球国界、河湖矢量 | Natural Earth（公共领域） |
| `data/dem/` | 高程瓦片与重投影缓存 | AWS Terrain Tiles（terrarium） |
| `data/stats/` | 分省统计表 | 国家统计局及各省统计公报 |

> 台湾仅有省级轮廓 `710000.json`（DataV 未提供下级界线），相应图幅改用地势图与经济对比图。

## 声明

本手册为学习与参考用途的知识汇编。所有示意地图不作为权属划界依据；统计数字以各来源最新官方发布为准。各节末"参考与数据来源"列出来源与口径。
