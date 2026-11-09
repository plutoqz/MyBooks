# -*- coding: utf-8 -*-
"""批量重跑指定绘图脚本，逐个执行并汇总结果。

用法：python rerun_all.py ch03_terrain.py ch03_maps.py ...
每个脚本独立子进程执行，失败不影响后续；结果追加写入 logs/rerun.log。
"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
LOGDIR = os.path.join(HERE, "..", "logs")


def run(script, timeout=3600):
    t0 = time.time()
    try:
        p = subprocess.run([PY, script], cwd=HERE, capture_output=True,
                           text=True, encoding="utf-8", errors="replace",
                           timeout=timeout)
        ok = p.returncode == 0
        tail = (p.stderr or "").strip().splitlines()[-6:]
        return ok, time.time() - t0, "\n".join(tail)
    except subprocess.TimeoutExpired:
        return False, time.time() - t0, "TIMEOUT"


if __name__ == "__main__":
    os.makedirs(LOGDIR, exist_ok=True)
    scripts = sys.argv[1:]
    log = open(os.path.join(LOGDIR, "rerun.log"), "a", encoding="utf-8")
    log.write(f"\n===== {time.strftime('%Y-%m-%d %H:%M:%S')} =====\n")
    nok = 0
    for sc in scripts:
        ok, sec, tail = run(sc)
        nok += ok
        line = f"{'OK  ' if ok else 'FAIL'} {sc:34s} {sec:6.1f}s"
        print(line, flush=True)
        log.write(line + "\n")
        if not ok:
            log.write(tail + "\n")
            print(tail, flush=True)
    log.write(f"---- {nok}/{len(scripts)} ok ----\n")
    log.close()
    print(f"\n合计 {nok}/{len(scripts)} 成功")
