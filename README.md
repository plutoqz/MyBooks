# 《中国地理知识手册》项目仓库

一本以公开、可信数据为基础的中国地理参考手册：13 章 51 节 + 13.5 分省 34 节 + 附录，共 **85 个正文小节、165 幅图**。

仓库只收录**文稿、绘图脚本与成品图**；原始地理数据（约 1.5 GB，含 DEM 瓦片、边界矢量、统计底稿）不入库，获取方式见文末。

## 目录结构

```
中国地理知识手册/
├── 00_提纲与编写说明.md      编写提纲、章节规划、数据来源清单
├── sections/                 正文（Markdown），85 个正文小节 + 1 个分省推进台账
├── figures/                  成品图（PNG，200 dpi），文件名 fig{章}-{序}_名称.png
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
python scripts/md2html.py 13-05-23   # 只转文件名含该关键字的节

# 3) 导出 PDF（不安装额外依赖，调用本机 Microsoft Edge / Chrome 无头模式）
python scripts/build_pdf.py
```

`build_book.py` 生成的 HTML 通过相对路径引用 `figures/`，请保持 `output/` 与 `figures/` 在同级目录；用浏览器打开后可直接"打印 → 另存为 PDF"，`@media print` 已按章设置分页。

## 写作与制图约定

- **正文**：每节一个 `sections/NN-MM_名称.md`，首行为 `# 节号 标题`；图用相对路径 `../figures/…`；图下一行写 `**图 X-Y 说明**`。
- **地图**：统一 Albers 等积圆锥投影（中央经线 105°E，标准纬线 25°N/47°N），配色与字号集中在 `scripts/style.py`；中国全图须含南海诸岛与断续线，示意地图注明"不作为权属划界依据"。
- **图号**：`fig{章号}-{序号}`，全书按出现顺序编号；13.5 分省图号分块预留（北方 7–99、南方 101–199、西北/青藏 201–249），台账见 `sections/13-05_推进登记.md`。
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
