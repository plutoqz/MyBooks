"""离线重建上册图件；输出至 output/上册修订，不替换下册或现有成品。"""
import argparse
import ast
import json
import subprocess
import sys
import time
from pathlib import Path

from audit_volume1 import inventory

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "上册修订"


def render_province_figures(script, kind="charts"):
    import runpy
    namespace = runpy.run_path(script, run_name="province_charts")
    tree = ast.parse(Path(script).read_text(encoding="utf-8"))
    bodies = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "run":
            bodies.append(node.body)
        elif isinstance(node, ast.If) and "__name__" in ast.unparse(node.test):
            bodies.append(node.body)
    chart_names = {
        "fig_pop", "barh_chart", "barv_chart", "fig_gdp", "fig_region_gdp",
        "fig_nepal_compare", "fig08_stats", "fig134_boards", "fig148_hk_sz",
        "fig150_gdp_visitors",
    }
    map_names = {"fig_relief", "fig07_relief", "fig149_locator"}
    selected = chart_names if kind == "charts" else map_names
    namespace["setup"]()
    for body in bodies:
        for node in body:
            value = (node.value if isinstance(node, (ast.Expr, ast.Assign))
                     else None)
            if (isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
                    and value.func.id in selected):
                eval(compile(ast.Expression(value), script, "eval"), namespace)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scripts", nargs="*")
    parser.add_argument("--province-charts", action="store_true")
    parser.add_argument("--province-maps", action="store_true")
    args = parser.parse_args()
    (OUT / "logs").mkdir(parents=True, exist_ok=True)
    manifest = OUT / "qa" / "inventory.json"
    items = (json.loads(manifest.read_text(encoding="utf-8"))["figures"]
             if manifest.exists() else inventory()["figures"])
    scripts = args.scripts or sorted({
        script for item in items for script in item["scripts"]
        if script not in {"standardize_ch10_figs.py", "ch13_prov_common.py",
                          "ch13_prov_south.py"}
    })
    if not args.scripts and "ch04_koppen.py" not in scripts:
        scripts.append("ch04_koppen.py")
    results = []
    for i, job in enumerate(scripts, 1):
        script, _, function = job.partition(":")
        log_name = job.replace(":", "_")
        code = (
            "import sys,runpy; from pathlib import Path; "
            f"sys.path.insert(0,{str(ROOT / 'scripts')!r}); "
            "import volume1_layout; "
            f"volume1_layout.OUTPUT_DIR=Path({str(OUT / 'figures')!r}); "
            f"volume1_layout.AUDIT_DIR=Path({str(OUT / 'qa')!r}); "
            + (f"from rebuild_volume1 import render_province_figures; "
             f"render_province_figures({str(ROOT / 'scripts' / script)!r},"
             f"{'maps' if args.province_maps else 'charts'!r})"
             if args.province_charts or args.province_maps else
             (f"ns=runpy.run_path({str(ROOT / 'scripts' / script)!r},run_name='volume1_plot'); "
              "ns.get('setup',lambda:None)(); "
              f"ns[{function!r}]()"
              if function else
              f"runpy.run_path({str(ROOT / 'scripts' / script)!r},run_name='__main__')"))
        )
        started = time.monotonic()
        result = subprocess.run([sys.executable, "-X", "utf8", "-c", code],
                                cwd=ROOT, capture_output=True, text=True,
                                encoding="utf-8", errors="replace")
        (OUT / "logs" / f"{log_name}.log").write_text(
            result.stdout + "\n" + result.stderr, encoding="utf-8"
        )
        entry = dict(script=job, returncode=result.returncode,
                     seconds=round(time.monotonic() - started, 1))
        results.append(entry)
        (OUT / "logs" / f"{log_name}.result.json").write_text(
            json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"{i}/{len(scripts)} {job} rc={result.returncode} "
              f'{entry["seconds"]}s', flush=True)
        if result.returncode:
            print(result.stderr[-1600:], flush=True)
        (OUT / "qa" / "build_results.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    if any(item["returncode"] for item in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
