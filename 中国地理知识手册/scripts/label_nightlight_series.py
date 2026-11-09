"""依据分区观测值为省级夜光曲线补齐地名图例。"""

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CSV_NAMES = {
    1: "beijing", 2: "tianjin", 3: "hebei", 4: "shanxi", 5: "liaoning",
    6: "jilin", 7: "heilongjiang", 8: "shandong", 9: "shanghai",
    10: "jiangsu", 11: "zhejiang", 12: "anhui", 13: "fujian",
    14: "jiangxi", 15: "henan", 16: "hubei", 17: "hunan",
    18: "guangdong", 19: "guangxi", 20: "hainan", 21: "chongqing",
    22: "sichuan", 23: "guizhou", 24: "yunnan", 25: "shaanxi",
    29: "neimenggu", 30: "gansu", 31: "ningxia", 32: "xinjiang",
    33: "qinghai", 34: "xizang",
}


def main():
    directory = ROOT / "output" / "下册修订" / "qa"
    changed, unresolved = [], []
    for path in directory.glob("fig*-00-*.data.json"):
        chapter = int(path.name[3:5])
        if chapter not in CSV_NAMES:
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        panels = [p for p in data["panels"] if len(p["lines"]) > 1
                  and re.search(r"夜光|灯光|辐射", p["title"])]
        if not panels:
            continue
        frame = pd.read_csv(ROOT / "data" / f"{CSV_NAMES[chapter]}_nightlight_clean.csv")
        candidates = {}
        for column in ["city_name", "district_name", "unit_name"]:
            if column not in frame:
                continue
            for name, part in frame.groupby(column):
                candidates[str(name)] = part.groupby("year")["sum"].sum()
        revised = False
        for panel in panels:
            for line in panel["lines"]:
                matches = []
                years = np.array(line["x"], dtype=int)
                for name, series in candidates.items():
                    if all(year in series.index for year in years) and np.allclose(
                        series.loc[years].values, line["y"], rtol=1e-8, atol=1e-4
                    ):
                        matches.append(name)
                if len(matches) == 1:
                    if line["label"] != matches[0]:
                        line["label"] = matches[0]
                        revised = True
                elif line["label"].startswith("_"):
                    unresolved.append(dict(figure=path.name, curve=line["label"]))
        if revised:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
            changed.append(path.name)
    report = dict(chart_data=changed, unresolved=unresolved)
    target = ROOT / "output" / "修订20261105" / "qa" / "nightlight_labels.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
