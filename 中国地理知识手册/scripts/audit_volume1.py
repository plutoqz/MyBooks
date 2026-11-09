"""上册图文清单与缩略图审阅页。"""
import ast
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "上册修订" / "qa"


def inventory():
    sections = sorted(
        p for p in (ROOT / "sections").glob("*.md") if "推进登记" not in p.name
    )
    figures = []
    typography = []
    for section in sections:
        text = section.read_text(encoding="utf-8")
        for alt, ref in re.findall(r"!\[([^\]]*)\]\(([^)]+)\)", text):
            path = (section.parent / ref).resolve()
            figures.append({
                "section": section.name, "name": path.name,
                "path": str(path), "alt": alt, "exists": path.exists(),
            })
        if re.search(r"\$|\\\(|\\\[|```|[┌┐└┘│]", text):
            typography.append(section.name)
    producers = {}
    for script in (ROOT / "scripts").glob("*.py"):
        tree = ast.parse(script.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if re.fullmatch(r"fig[\w-]+_.+\.png", node.value):
                    producers.setdefault(node.value, []).append(script.name)
    for item in figures:
        name = item["name"]
        item["scripts"] = sorted(set(producers.get(name, []) + producers.get(
            name.replace("fig14-", "fig13-", 1), []
        )))
    return {"sections": len(sections), "figures": figures,
            "typography_candidates": typography}


def contact_sheets(items, directory=OUT, prefix="contact"):
    directory.mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 20)
    for start in range(0, len(items), 12):
        page = Image.new("RGB", (1800, 1760), "white")
        draw = ImageDraw.Draw(page)
        for slot, item in enumerate(items[start:start + 12]):
            x, y = (slot % 3) * 600, (slot // 3) * 440
            image = Image.open(item["path"]).convert("RGB")
            image.thumbnail((580, 390))
            page.paste(image, (x + (600 - image.width) // 2, y + 28))
            draw.text((x + 12, y + 2), item["name"][:36], font=font, fill="#222222")
        page.save(directory / f"{prefix}_{start // 12 + 1:02d}.jpg", quality=92)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    result = inventory()
    (OUT / "inventory.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    contact_sheets(result["figures"])
    print(f'{result["sections"]} sections, {len(result["figures"])} figures')
    for item in result["figures"]:
        print(item["name"], " | ", ", ".join(item["scripts"]))
