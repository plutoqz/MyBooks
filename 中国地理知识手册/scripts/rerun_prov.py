# -*- coding: utf-8 -*-
"""批量重跑省级图脚本（ch13_prov_*.py），逐脚本子进程执行并记录日志。

用法:
    python scripts/rerun_prov.py            # 全部
    python scripts/rerun_prov.py ningxia    # 名称含 ningxia 的
"""
import glob
import os
import subprocess
import sys
import time
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = r"D:\code\Ideas\MyBooks\.venv\Scripts\python.exe"
LOG = os.path.join(ROOT, "logs", "rerun_prov.log")


def log(msg):
    line = f"{msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def main():
    pat = sys.argv[1] if len(sys.argv) > 1 else ""
    files = sorted(glob.glob(os.path.join(ROOT, "scripts", "ch13_prov_*.py")))
    if pat:
        files = [f for f in files if pat in os.path.basename(f)]
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    log(f"\n===== {time.strftime('%Y-%m-%d %H:%M:%S')} batch {len(files)} scripts =====")
    ok, bad = [], []
    t_all = time.time()
    for i, f in enumerate(files, 1):
        name = os.path.basename(f)
        t0 = time.time()
        try:
            r = subprocess.run(
                [PY, f], cwd=ROOT, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=1800,
            )
            dt = time.time() - t0
            if r.returncode == 0:
                log(f"[{i}/{len(files)}] OK   {name:38s} {dt:6.1f}s")
                ok.append(name)
            else:
                log(f"[{i}/{len(files)}] FAIL {name:38s} {dt:6.1f}s")
                tail = (r.stderr or r.stdout or "").strip().splitlines()[-14:]
                for ln in tail:
                    log("    " + ln)
                bad.append(name)
        except subprocess.TimeoutExpired:
            log(f"[{i}/{len(files)}] TIMEOUT {name}")
            bad.append(name)
        except Exception:
            log(f"[{i}/{len(files)}] ERROR {name}")
            for ln in traceback.format_exc().splitlines()[-8:]:
                log("    " + ln)
            bad.append(name)
    log(f"---- {len(ok)}/{len(files)} ok, total {time.time()-t_all:.0f}s ----")
    if bad:
        log("FAILED: " + ", ".join(bad))


if __name__ == "__main__":
    main()
