"""柯本气候分类图的中文图例与版式。"""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from PIL import Image

from style import DATA, FIGURES, setup
from volume1_layout import save_volume_figure


def main():
    setup()
    name = "fig4-2_柯本气候分类图.png"
    source = Image.open(Path(DATA) / "reference_images" / "koppen_beck_2023.png").convert("RGB")
    labels = [
        "Am  热带季风", "Aw  热带草原",
        "BWk  冷沙漠", "BSh  热草原（半干旱）", "BSk  冷草原（半干旱）",
        "Cwa  温带冬干夏热", "Cwb  温带冬干夏温", "Cwc  温带冬干夏凉",
        "Cfa  温带全年湿润夏热", "Cfb  温带全年湿润夏温",
        "Dsc  冷温带夏干夏凉", "Dwa  冷温带冬干夏热",
        "Dwb  冷温带冬干夏温", "Dwc  冷温带冬干夏凉",
        "Dfa  冷温带全年湿润夏热", "Dfb  冷温带全年湿润夏温",
        "Dfc  冷温带全年湿润夏凉", "ET  苔原", "EF  冰原",
    ]
    colors = [tuple(channel / 255 for channel in source.getpixel((1480, 244 + i * 24)))
              for i in range(len(labels))]
    fig, ax = plt.subplots(figsize=(10, 10.5))
    fig.subplots_adjust(left=0.025, right=0.975, bottom=0.35, top=0.91)
    ax.imshow(source.crop((35, 55, 1415, 850)))
    ax.axis("off")
    fig.text(0.025, 0.98, "中国柯本—盖格气候类型", fontsize=15, weight="bold")
    fig.text(0.025, 0.93, "1991—2020 年；类型代码与底图颜色一一对应", fontsize=9)
    handles = [Patch(facecolor=color, label=label)
               for color, label in zip(colors, labels)]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.025, 0.345),
               ncol=2, fontsize=9, frameon=False, columnspacing=3.5,
               handlelength=1.8, labelspacing=0.7)
    fig.text(0.025, 0.015,
             "资料：Beck et al. (2023), Scientific Data 10:724；"
             "DOI:10.1038/s41597-023-02549-6。\n"
             "底图与台湾岛放大图沿用所引资料的制图范围；海域及界线参见本册全国行政区划图。",
             fontsize=8)
    save_volume_figure(fig, Path(FIGURES) / name)
    plt.close(fig)


if __name__ == "__main__":
    main()
