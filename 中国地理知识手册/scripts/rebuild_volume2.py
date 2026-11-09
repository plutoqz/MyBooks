"""按清单离线重建下册图件。"""
import argparse
import fnmatch
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "下册修订"


def worker(script, code=None, pattern="*"):
    import runpy
    import volume2_layout
    manifest = json.loads((OUT / "qa" / "inventory.json").read_text(encoding="utf-8"))
    names = [item["name"] for item in manifest["figures"]
             if script in item["scripts"] and fnmatch.fnmatch(item["name"], pattern)]
    volume2_layout.install(names)
    sys.argv = [script]
    if "overview" in script or script == "update_haidian_maps.py":
        runpy.run_path(str(ROOT / "scripts" / script), run_name="__main__")
    else:
        ns = runpy.run_path(str(ROOT / "scripts" / script), run_name="volume2_plot")
        function = ns.get("generate_unit_maps") or ns.get("generate_district_maps")
        configs = [value for name, value in ns.items()
                   if "CONFIGS" in name and isinstance(value, dict)
                   and value and all(isinstance(v, dict) for v in value.values())
                   and any("sec_id" in v for v in value.values())]
        if len(configs) != 1:
            raise ValueError(f"{script}: 配置表数量 {len(configs)}")
        for adcode in configs[0]:
            if code is None or str(adcode) == code:
                function(adcode)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scripts", nargs="*")
    parser.add_argument("--worker")
    parser.add_argument("--code")
    parser.add_argument("--pattern", default="*")
    args = parser.parse_args()
    if args.worker:
        worker(args.worker, args.code, args.pattern)
        return
    (OUT / "logs").mkdir(parents=True, exist_ok=True)
    manifest = json.loads((OUT / "qa" / "inventory.json").read_text(encoding="utf-8"))
    scripts = args.scripts or sorted({name for item in manifest["figures"]
                                     for name in item["scripts"]})
    failed = False
    for script in scripts:
        started = time.monotonic()
        command = [sys.executable, "-X", "utf8", __file__, "--worker", script]
        command += ["--pattern", args.pattern]
        if args.code:
            command += ["--code", args.code]
        tag = script.replace(".py", "") + ("_" + args.code if args.code else "")
        with (OUT / "logs" / f"{tag}.log").open("w", encoding="utf-8") as log:
            result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        report = dict(script=script, code=args.code, returncode=result.returncode,
                      seconds=round(time.monotonic() - started, 1))
        (OUT / "logs" / f"{tag}.result.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(report, flush=True)
        if result.returncode:
            failed = True
            print((OUT / "logs" / f"{tag}.log").read_text(encoding="utf-8")[-2200:])
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
