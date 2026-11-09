"""整理地理条目中的重复套用说明。"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / "output" / "修订20261105" / "qa"
SUFFIXES = [
    "构成区域地形骨架与分水岭",
    "构成区域地形骨架与分水岭生态安全屏障",
    "对全区工农业灌溉生产",
    "发挥着行洪排涝、农田自流引灌",
    "承担区域行政综合治理、公共资源集散",
    "区域公共行政治理中枢、公共服务均等化",
    "区域重点客货运交通流集散",
    "客流高铁干线高效集散转换、大宗工业",
    "集聚新质生产力与先进制造业的核心",
    "区域战略性新兴产业深度集聚",
    "区域重点文化名胜与生态康养",
    "承载数千年深厚历史文脉",
]


def main():
    changes = []
    for p in (ROOT / "sections_vol2").glob("*.md"):
        original = p.read_text(encoding="utf-8")
        notes = [line for line in original.splitlines()
                 if line.startswith(("2024 年统计来源：", "地市统计来源："))]
        text = re.sub(
            r"(?ms)^##\s+[^\n]*(?:发展展望|战略展望|发展愿景|新时期自贸港封关运作|"
            r"新征程高质量跨越式发展愿景)[^\n]*\n.*?(?=^##\s|\Z)",
            "", original,
        )
        city = p.stem.split("_", 1)[1]
        revised = []
        suffixes_removed = 0
        for line in text.splitlines():
            if line.startswith("-"):
                for phrase in SUFFIXES:
                    pattern = r"[：:]\s*" + re.escape(phrase) + r"[^\n]*"
                    line, count = re.subn(pattern, "；", line)
                    suffixes_removed += count
            if "在大地构造演化史上" in line and any(
                s in line for s in ["关键部位", "隶属于", "重要地质构造交接地带"]
            ):
                continue
            if "在气候水热配置方面" in line and ("（或" in line or "或向" in line):
                continue
            if "深度融入黄河、淮河或长江大水系" in line:
                line = "本节列示的主要河湖与水系节点："
            if "依托高标准时速 350 公里高铁干线" in line:
                line = "本节列示的主要交通节点与通道："
            if "拥有数量众多的世界文化遗产、国家 5A" in line:
                line = city + "的文化旅游与相关地标："
            if "进一步加速交通基础设施数字化与智慧绿色转型" in line:
                continue
            if "全国首条跨市域高水平地铁快线" in line:
                line = line.replace("全国首条跨市域高水平地铁快线", "市域轨道交通")
            revised.append(line)
        text = re.sub(r"\n{3,}", "\n\n", "\n".join(revised)).rstrip() + "\n"
        for note in notes:
            if note not in text:
                text += "\n" + note + "\n"
        if text != original:
            p.write_text(text, encoding="utf-8")
            changes.append(dict(section=p.name, point_descriptions=suffixes_removed,
                                characters_before=len(original), characters_after=len(text)))
    report = dict(
        sections=len(changes),
        point_descriptions=sum(row["point_descriptions"] for row in changes),
        removed_characters=sum(row["characters_before"] - row["characters_after"] for row in changes),
        details=changes,
    )
    (QA / "gazetteer_editing.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "details"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
