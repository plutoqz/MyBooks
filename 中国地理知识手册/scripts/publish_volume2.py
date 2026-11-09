"""将下册修订图件同步到正文引用目录。"""
import filecmp
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "下册修订"


def main():
    inventory = json.loads((OUT / "qa" / "inventory.json").read_text(encoding="utf-8"))
    names = [item["name"] for item in inventory["figures"]]
    for name in names:
        source = OUT / "figures" / name
        target = ROOT / "figures" / name
        shutil.copy2(source, target)
        if not filecmp.cmp(source, target, shallow=False):
            raise OSError(f"图件复制不完整：{name}")
    report = dict(published_png=len(names), byte_comparison="all_equal")
    (OUT / "qa" / "publication.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
