"""下册正文、图件和生产脚本清单。"""
import ast
import json
import re
import shutil
from pathlib import Path

from audit_volume1 import contact_sheets

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "下册修订"
QA = OUT / "qa"


def inventory():
    files = sorted((ROOT / "sections_vol2").glob("*.md"))
    figures = []
    for section in files:
        for alt, ref in re.findall(r"!\[([^\]]*)\]\(([^)]+)\)",
                                   section.read_text(encoding="utf-8-sig")):
            path = (section.parent / ref).resolve()
            figures.append(dict(section=section.name, name=path.name,
                                path=str(path), alt=alt, exists=path.exists()))
    scripts = sorted(
        set((ROOT / "scripts").glob("gen_*overview_figs.py"))
        | set((ROOT / "scripts").glob("gen_*unit_maps.py"))
        | set((ROOT / "scripts").glob("gen_*district_maps.py")))
    metadata = {}
    for script in scripts:
        tree = ast.parse(script.read_text(encoding="utf-8-sig"))
        codes = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                codes.update(re.findall(r"fig(\d{2})-\d{2}-\d", node.value))
            if isinstance(node, ast.ImportFrom) and node.module and "configs" in node.module:
                config = ROOT / "scripts" / f"{node.module}.py"
                text = config.read_text(encoding="utf-8-sig")
                codes.update(re.findall(r'["\']sec_id["\']:\s*["\'](\d{2})-', text))
        metadata[script.name] = sorted(codes)
    metadata["gen_district_maps.py"] = ["01"]
    for item in figures:
        chapter, section = re.match(r"fig(\d{2})-(\d{2})-", item["name"]).groups()
        kind = "overview" if section == "00" else "unit"
        item["scripts"] = [
            name for name, codes in metadata.items()
            if chapter in codes and
            (("overview" in name) if kind == "overview" else ("overview" not in name))]
        if item["name"].startswith("fig01-06-4_"):
            item["scripts"] = ["update_haidian_maps.py"]
    return dict(sections=len(files), figures=figures, scripts=metadata)


def main():
    QA.mkdir(parents=True, exist_ok=True)
    manifest = QA / "inventory.json"
    if manifest.exists():
        result = json.loads(manifest.read_text(encoding="utf-8"))
    else:
        result = inventory()
        manifest.write_text(json.dumps(result, ensure_ascii=False, indent=2),
                            encoding="utf-8")
    originals = OUT / "originals"
    for kind, source in [("sections", ROOT / "sections_vol2"),
                         ("scripts", ROOT / "scripts")]:
        target = originals / kind
        target.mkdir(parents=True, exist_ok=True)
        for path in source.glob("*.md" if kind == "sections" else "*.py"):
            if not (target / path.name).exists():
                shutil.copy2(path, target / path.name)
    target = originals / "figures"
    target.mkdir(exist_ok=True)
    for item in result["figures"]:
        if not (target / item["name"]).exists():
            shutil.copy2(item["path"], target / item["name"])
    selected = [item for item in result["figures"]
                if re.match(r"fig\d{2}-00-[145]_", item["name"])]
    contact_sheets(selected, QA, "original_overview")
    print("sections", result["sections"], "figures", len(result["figures"]))
    print("unmapped", [item["name"] for item in result["figures"] if not item["scripts"]])
    print(json.dumps(result["scripts"], ensure_ascii=False))


if __name__ == "__main__":
    main()
