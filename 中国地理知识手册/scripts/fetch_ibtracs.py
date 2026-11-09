# -*- coding: utf-8 -*-
"""IBTrACS 分块续传下载器。

NCEI 的 ibtracs.WP.list.v04r01.csv 有 109 MB，单连接容易被中途掐断
（SSL UNEXPECTED_EOF / RemoteDisconnected）。服务器声明 Accept-Ranges: bytes，
所以这里按 2 MB 分块发 Range 请求，逐块落盘；每块独立重试，断点从
已有文件大小继续，总能收敛。
"""
import os
import sys
import time
from urllib.request import Request, urlopen

URL = ("https://www.ncei.noaa.gov/data/international-best-track-archive-for-"
       "climate-stewardship-ibtracs/v04r01/access/csv/"
       "ibtracs.WP.list.v04r01.csv")
DST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "data", "climatology", "ibtracs",
                   "ibtracs.WP.list.v04r01.csv")
TOTAL = 114_683_518
CHUNK = 8 << 20          # 8 MB：NCEI 实测约 65 KB/s，8 MB 一块约 2 分钟
READ_TIMEOUT = 900       # 单块读取超时须远大于「块大小 / 实测速率」
MAX_TRIES = 40


def head_size():
    req = Request(URL, method="HEAD")
    with urlopen(req, timeout=60) as r:
        return int(r.headers.get("Content-Length") or TOTAL)


def download(dst=DST, total_fallback=TOTAL, chunk=None):
    """可复用的分块续传下载，返回 0 表示成功。"""
    chunk = chunk or CHUNK
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    total = total_fallback
    try:
        total = head_size()
    except Exception as e:
        print("HEAD 失败，使用内置长度", type(e).__name__, flush=True)
    print(f"total = {total:,} bytes", flush=True)

    if os.path.exists(dst) and os.path.getsize(dst) > total:
        os.remove(dst)

    round_ = 0
    while True:
        have = os.path.getsize(dst) if os.path.exists(dst) else 0
        if have >= total:
            break
        round_ += 1
        if round_ > MAX_TRIES * 6:
            print("超过最大轮次，放弃", flush=True)
            return 1
        end = min(have + chunk, total) - 1
        req = Request(URL, headers={"Range": f"bytes={have}-{end}"})
        try:
            with urlopen(req, timeout=READ_TIMEOUT) as r:
                data = r.read()
            if not data:
                raise IOError("空响应")
            mode = "ab" if have else "wb"
            with open(dst, mode) as f:
                f.write(data)
            got = os.path.getsize(dst)
            print(f"\r{got/1e6:7.2f} / {total/1e6:7.2f} MB "
                  f"({got*100.0/total:5.1f}%)", end="", flush=True)
        except Exception as e:
            print(f"\n  块 {have}-{end} 失败：{type(e).__name__}，重试",
                  flush=True)
            time.sleep(3)
    print("\ndone", os.path.getsize(dst))
    return 0


def main():
    return download()


if __name__ == "__main__":
    sys.exit(main())
