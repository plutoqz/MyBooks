# -*- coding: utf-8 -*-
"""执行目录组织重构：
1. 将 13.5 独立为 第 14 章（14-01 到 14-34）；
2. 分省图片重命名为 fig14- 并同步更新 md 引用；
3. 将第 13 章拆分为 13.1-13.5（13.4 西北地区，13.5 青藏地区）；
4. 更新 qa_structure.py 和 build_book.py。
"""
import os
import re
import glob
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEC = os.path.join(ROOT, "sections")
FIG = os.path.join(ROOT, "figures")
HTML = os.path.join(ROOT, "html")


def step1_split_ch13_04_05():
    """拆分原 13-04_西北地区与青藏地区.md 为 13-04_西北地区.md 与 13-05_青藏地区.md。"""
    old_p = os.path.join(SEC, "13-04_西北地区与青藏地区.md")
    if not os.path.exists(old_p):
        print("13-04 已拆分或不存在")
        return

    content = open(old_p, encoding="utf-8").read()
    
    # 找到青藏地区的分界点：'## 三、青藏：高度的礼赞'
    parts = content.split("## 三、青藏：高度的礼赞")
    if len(parts) != 2:
        print("未找到青藏分界点")
        return
        
    part_nw = parts[0]
    part_tp = parts[1]

    # 西北篇
    nw_md = """# 13.4 西北地区

西北地区深居欧亚大陆腹地，涵盖内蒙古自治区、甘肃省、宁夏回族自治区与新疆维吾尔自治区。在这片占全国近三分之一面积的广袤干旱与半干旱土地上，山盆相间、绿洲点缀、大漠孤烟与丰饶矿藏交织，构成了中国最辽阔的陆疆屏障与向西开放前沿。

## 一、区域范围与行政单元

| 省级行政区 | 面积（km²） | 常住人口（万，2023） | 地区生产总值（万亿元） | 行政中心 |
|:---|:---:|:---:|:---:|:---|
| **内蒙古自治区** | 1,183,000 | 2,396 | ~2.46 | 呼和浩特 |
| **甘肃省** | 425,800 | 2,465 | ~1.18 | 兰州 |
| **宁夏回族自治区** | 66,400 | 729 | ~0.53 | 银川 |
| **新疆维吾尔自治区** | 1,664,900 | 2,598 | ~1.91 | 乌鲁木齐 |

## 二、自然地理与生态环境

西北的干旱源于三大核心地理成因：深居欧亚大陆腹地、四周高山阻隔大洋暖湿水汽、以及青藏高原隆升对西风带与季风环流的强烈阻断。年降水量自东向西呈梯度递减：从呼伦贝尔草原的 400 mm 以上，逐渐递减至贺兰山以西的 200 mm 以下，再至塔里木盆地腹地不足 50 mm，而潜在蒸发量高达 2000—3000 mm。

![图13-5 西北地区专题图](../figures/fig13-5_西北地区专题图.png)

**图 13-5 西北地区专题图**：三大地形单元、沙漠与绿洲、主要矿产与陆路口岸分布。

地貌格局呈现鲜明的两大地形大系：
1. **内蒙古高原**：地势坦荡，呼伦贝尔、锡林郭勒、科尔沁与鄂尔多斯草原连绵千里，是中国温带草原生态系统的重要基底；
2. **新疆“三山夹两盆”**：北有阿尔泰山，中有天山横亘，南有昆仑山阿尔金山环抱，其间环抱准噶尔盆地与塔里木盆地。塔克拉玛干沙漠（约 33 万 km²）为世界第二大流动沙漠，古尔班通古特沙漠为中国最大固定半固定沙漠；
3. **河西走廊**：祁连山北麓长达千里的冲积扇狭长平原，冰川雪水融流滋养了武威、张掖、酒泉、敦煌四大绿洲，自古是联通中原与西域的陆路咽喉。

## 三、绿洲农业与资源型产业

西北是典型的“水主宰一切”的人地系统。水资源主要依托天山、祁连山、昆仑山高山冰川积雪融水，形成了独特的内流河水系，其中**塔里木河**（全长约 2179 km）是中国最长的内流河：
- **绿洲灌溉农业**：黄河干流自流引水造就了“塞上江南”河套平原与宁夏平原；新疆绿洲以古代坎儿井与现代节水滴灌技术，发展出高品质棉花（全国 90% 以上优质长绒棉）、番茄加工与吐鲁番葡萄、哈密瓜等特色特色果品；
- **能源矿产宝库**：鄂尔多斯盆地与准噶尔、塔里木盆地富集煤炭、石油与天然气（西气东输工程主力气源地）；白云鄂博是世界最大稀土伴生矿床，金昌拥有全国最大镍矿基地；
- **陆路向西开放前沿**：依托中欧班列西通道（阿拉山口、霍尔果斯口岸）与兰新高铁，新疆从内陆腹地一跃成为新丝绸之路经济带核心区。

## 参考与数据来源

1. 自然地理与气候数据：中国科学院西北生态环境资源研究院《中国西北干旱区水资源与生态环境评价》。
2. 经济与人口指标：内蒙古、甘肃、宁夏、新疆四省区统计局国民经济和社会发展统计公报（2023—2024）。
"""

    # 青藏篇
    tp_md = """# 13.5 青藏地区

青藏地区涵盖青海省与西藏自治区（以及四川西部、川西滇西北等高原边缘地带），平均海拔在 4000 米以上，雄踞世界屋脊，是名副其实的“地球第三极”与“亚洲水塔”。

## 一、区域范围与行政单元

| 省级行政区 | 面积（km²） | 常住人口（万，2023） | 地区生产总值（万亿元） | 行政中心 |
|:---|:---:|:---:|:---:|:---|
| **青海省** | 722,300 | 594 | ~0.38 | 西宁 |
| **西藏自治区** | 1,228,400 | 365 | ~0.24 | 拉萨 |

## 二、自然地理与高寒环境

青藏高原是新生代欧亚板块与印度洋板块剧烈碰撞隆升的地质奇迹。高海拔造就了极端的高寒低氧、气压低下、强紫外线辐射与漫长严寒环境：

![图13-6 青藏地区专题图](../figures/fig13-6_青藏地区专题图.png)

**图 13-6 青藏地区专题图**：高原雪山冰川分布、大江大河源头、“一江两河”农牧区与主要交通线。

1. **亚洲水塔与冰冻圈**：高原发育了极度壮丽的现代冰川与多年冻土，总面积近 5 万平方公里。青藏高原是长江、黄河、澜沧江（湄公河）、雅鲁藏布江（布拉马普特拉河）、印度河、怒江（萨尔温江）等大江大河的共同源头，孕育了三江源国家公园；
2. **构造盆地与内陆大湖**：柴达木盆地（“聚宝盆”）盐湖密布，察尔汗盐湖拥有全国最大的钾盐与锂矿资源；青海湖是中国最大的内陆咸水湖，纳木错、色林错等高原大湖星罗棋布。

## 三、高寒农牧业与绿色发展

在脆弱严酷的高原生境下，人地系统展现出极强的适应智慧：
- **河谷农业**：种植区严格限制在海拔相对较低、水热条件稍好的河谷地带，即雅鲁藏布江中游及其支流拉萨河、年楚河构成的“一江两河”谷地，以及青海湟水谷地，主要作物为耐寒早熟的青稞、冬春小麦与豌豆；
- **高原游牧畜牧业**：广袤的高寒草原与高寒草甸上，世代繁育耐低氧抗严寒的牦牛、藏羊；
- **国家生态安全屏障**：高原承担着调节全球季风环流与亚洲水源补给的神圣生态功能。全域划定高标准生态红线，大力发展高原生态旅游、地热能与光伏清洁能源，青藏铁路与在建川藏铁路将雪域高原与祖国内地紧密交融。

## 参考与数据来源

1. 高原科学考察：中国科学院“第二次青藏高原综合科学考察研究”系列成果公报。
2. 经济与生态监测：青海省、西藏自治区统计局公报与三江源国家公园生态监测报告。
"""

    with open(os.path.join(SEC, "13-04_西北地区.md"), "w", encoding="utf-8") as f:
        f.write(nw_md)
    with open(os.path.join(SEC, "13-05_青藏地区.md"), "w", encoding="utf-8") as f:
        f.write(tp_md)

    os.remove(old_p)
    print("拆分完成：生成 13-04_西北地区.md 与 13-05_青藏地区.md，已移除原 13-04 文件。")


def step2_rename_provinces():
    """将 13-05-01 到 13-05-34 重命名为 14-01 到 14-34，并更新标题与图片。"""
    prov_files = sorted(glob.glob(os.path.join(SEC, "13-05-*.md")))
    print(f"找到 {len(prov_files)} 个分省文件")

    # 收集分省引用的图片做映射
    # 比如 fig13-7 -> fig14-7
    for pf in prov_files:
        base = os.path.basename(pf)
        # 例如 13-05-01_北京市.md -> 14-01_北京市.md
        m = re.match(r"^13-05-(\d\d)_(.*)\.md$", base)
        if not m:
            continue
        p_idx = int(m.group(1))
        p_name = m.group(2)
        new_base = f"14-{p_idx:02d}_{p_name}.md"
        new_path = os.path.join(SEC, new_base)

        content = open(pf, encoding="utf-8").read()

        # 1. 替换首行标题: # 13.5.X 省名 -> # 14.X 省名
        content = re.sub(r"^#\s*13\.5\.\d+\s+", f"# 14.{p_idx} ", content)

        # 2. 查找并重命名该文件中引用的图片: fig13-X_ -> fig14-X_
        # 图片链接: ![图 13-X ...](../figures/fig13-X_...png)
        # 图注: **图 13-X ...**
        def repl_img(match):
            alt = match.group(1)
            rel_path = match.group(2)
            fname = os.path.basename(rel_path)
            
            # 若是 fig13-X_...
            m_fig = re.match(r"^fig13-(\d+)_(.*)$", fname)
            if m_fig:
                f_num = m_fig.group(1)
                f_rest = m_fig.group(2)
                new_fname = f"fig14-{f_num}_{f_rest}"
                old_fig_p = os.path.join(FIG, fname)
                new_fig_p = os.path.join(FIG, new_fname)
                if os.path.exists(old_fig_p):
                    shutil.move(old_fig_p, new_fig_p)
                new_rel = rel_path.replace(fname, new_fname)
                new_alt = re.sub(r"图\s*13-", "图 14-", alt)
                return f"![{new_alt}]({new_rel})"
            return match.group(0)

        content = re.sub(r"!\[(.*?)\]\((.*?)\)", repl_img, content)

        # 替换图注: **图 13-X
        content = re.sub(r"\*\*图\s*13-(\d+)", r"**图 14-\1", content)

        # 替换正文中的可能图号引用: 图 13-X
        content = re.sub(r"图\s*13-(\d+)", r"图 14-\1", content)

        # 写入新文件
        with open(new_path, "w", encoding="utf-8") as f:
            f.write(content)

        # 删除旧文件
        os.remove(pf)
        print(f"Renamed: {base} -> {new_base} (首行: # 14.{p_idx} {p_name})")

    # 处理 13-05_推进登记.md -> 14-00_推进登记.md
    reg_p = os.path.join(SEC, "13-05_推进登记.md")
    if os.path.exists(reg_p):
        reg_txt = open(reg_p, encoding="utf-8").read()
        reg_txt = reg_txt.replace("13.5", "14").replace("13-05-", "14-").replace("fig13-", "fig14-")
        new_reg_p = os.path.join(SEC, "14-00_推进登记.md")
        with open(new_reg_p, "w", encoding="utf-8") as f:
            f.write(reg_txt)
        os.remove(reg_p)
        print("Updated 13-05_推进登记.md -> 14-00_推进登记.md")


def step3_clean_html_cache():
    """清理旧的 html/13-05-*.html 缓存。"""
    for h in glob.glob(os.path.join(HTML, "13-05-*.html")):
        os.remove(h)
    for h in glob.glob(os.path.join(HTML, "13-04_*.html")):
        os.remove(h)
    for h in glob.glob(os.path.join(HTML, "13-05_*.html")):
        os.remove(h)
    print("清理旧 HTML 缓存完成")


def step4_update_qa_script():
    """更新 qa_structure.py 中的匹配规则。"""
    qa_p = os.path.join(ROOT, "scripts", "qa_structure.py")
    txt = open(qa_p, encoding="utf-8").read()

    # 更新 EXPECT
    # 原: + [f"13-0{i}" for i in range(1, 5)] + [f"13-05-{i:02d}" for i in range(1, 35)] + ["99"])
    # 新: + [f"13-0{i}" for i in range(1, 6)] + [f"14-{i:02d}" for i in range(1, 35)] + ["99"])
    txt = re.sub(
        r'\+ \[f"13-0\{i\}" for i in range\(1, \d+\)\]\s*\+ \[f"13-05-\{i:02d\}" for i in range\(1, 35\)\]',
        '+ [f"13-0{i}" for i in range(1, 6)] + [f"14-{i:02d}" for i in range(1, 35)]',
        txt
    )

    # 替换标题匹配规则中的 want:
    # 原: if f.startswith("13-05-"): want = "13.5." + str(int(f[6:8]))
    # 新: elif f.startswith("14-"): want = "14." + str(int(f[3:5]))
    txt = re.sub(
        r'if f\.startswith\("13-05-"\):\s*want = "13\.5\." \+ str\(int\(f\[6:8\]\)\)',
        'if f.startswith("14-"):\n            want = "14." + str(int(f[3:5]))',
        txt
    )

    # 替换六段式判断:
    # 原: if f.startswith("13-05-") and f != "13-05_推进登记.md":
    # 新: if f.startswith("14-") and not f.startswith("14-00"):
    txt = re.sub(
        r'if f\.startswith\("13-05-"\) and f != "13-05_推进登记\.md":',
        'if f.startswith("14-") and not f.startswith("14-00"):',
        txt
    )

    # 替换 extra 判断:
    # 原: extra = [s for s in stems if not s.startswith("13-05_")
    # 新: extra = [s for s in stems if not s.startswith("14-00")
    txt = re.sub(
        r'not s\.startswith\("13-05_"\)',
        'not s.startswith("14-00")',
        txt
    )

    with open(qa_p, "w", encoding="utf-8") as f:
        f.write(txt)
    print("qa_structure.py 更新完成")


def step5_update_build_book():
    """更新 build_book.py 中的 CHAPTERS 列表。"""
    bb_p = os.path.join(ROOT, "scripts", "build_book.py")
    txt = open(bb_p, encoding="utf-8").read()

    # 原:
    #     ("第 13 章　区域地理分论", ["13-0"]),
    #     ("13.5　省级行政区速览（34 个省级行政区）", ["13-05-"]),
    #     ("附录", ["99_"]),
    # 新:
    #     ("第 13 章　区域地理分论", ["13-"]),
    #     ("第 14 章　省级行政区速览（34 个省级行政区）", ["14-"]),
    #     ("附录", ["99_"]),
    txt = txt.replace(
        '    ("第 13 章　区域地理分论", ["13-0"]),\n    ("13.5　省级行政区速览（34 个省级行政区）", ["13-05-"]),\n    ("附录", ["99_"]),',
        '    ("第 13 章　区域地理分论", ["13-"]),\n    ("第 14 章　省级行政区速览（34 个省级行政区）", ["14-"]),\n    ("附录", ["99_"]),'
    )

    with open(bb_p, "w", encoding="utf-8") as f:
        f.write(txt)
    print("build_book.py 更新完成")


if __name__ == "__main__":
    step1_split_ch13_04_05()
    step2_rename_provinces()
    step3_clean_html_cache()
    step4_update_qa_script()
    step5_update_build_book()
