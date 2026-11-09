"""检查上册导出 PDF 的文字碰撞与最小字号。"""
import json
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "上册修订"
TOOLS = Path.home() / ".codex" / "skills" / "nature-figure" / "scripts"
sys.path.insert(0, str(TOOLS))
from audit_figure_collisions import audit_pdf as audit_collisions
from audit_pdf_text import audit_pdf as audit_fonts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("patterns", nargs="*", default=["*.pdf"])
    args = parser.parse_args()
    reports = []
    paths = sorted({p for pattern in args.patterns
                    for p in (OUT / "figures").glob(pattern)})
    for path in paths:
        audit_file = OUT / "qa" / f"{path.stem}.audit.json"
        if audit_file.exists() and audit_file.stat().st_mtime > path.stat().st_mtime:
            report = json.loads(audit_file.read_text(encoding="utf-8"))
        else:
            collision = audit_collisions(path)
            font = audit_fonts(path.read_bytes(), minimum_pt=5)
            (OUT / "qa" / f"{path.stem}.collisions.json").write_text(
                json.dumps(collision, ensure_ascii=False, indent=2), encoding="utf-8")
            report = dict(name=path.name, collision=collision["summary"], font=font)
            audit_file.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
        reports.append(report)
        if report["collision"]["fail"] or report["collision"]["warn"]:
            print(path.name, report["collision"], flush=True)
    (OUT / "qa" / "export_audit.json").write_text(
        json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Audited {len(reports)} figures; "
          f"{sum(r['collision']['fail'] for r in reports)} FAIL; "
          f"{sum(r['collision']['warn'] for r in reports)} WARN.", flush=True)


if __name__ == "__main__":
    main()
