# -*- coding: utf-8 -*-
"""把组装好的全书 HTML 打印为 PDF（调用本机 Microsoft Edge / Chrome 无头模式）。

用法：
    python scripts/build_pdf.py                 # 输出 output/中国地理知识手册_全书.pdf
    python scripts/build_pdf.py --open          # 生成后自动打开

不依赖第三方 PDF 库；若本机没有 Chromium 内核浏览器，请用浏览器打开
output/中国地理知识手册_全书.html，选择"打印 → 另存为 PDF"。
"""
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "output" / "中国地理知识手册_全书.html"
PDF = ROOT / "output" / "中国地理知识手册_全书.pdf"

CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


def find_browser():
    for p in CANDIDATES:
        if os.path.exists(p):
            return p
    return None


def main():
    if not HTML.exists():
        sys.exit(f"未找到 {HTML}，请先运行 python scripts/build_book.py")
    browser = find_browser()
    if not browser:
        sys.exit("未找到 Edge/Chrome。请手动用浏览器打开 HTML 后打印为 PDF。")

    url = "file:///" + quote(str(HTML).replace("\\", "/"))
    cmd = [browser, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
           f"--print-to-pdf={PDF}", url]
    print("调用浏览器：", browser)
    print("输出：", PDF)
    subprocess.run(cmd, check=False)
    if PDF.exists():
        print(f"完成：{PDF}（{PDF.stat().st_size / 1024 / 1024:.1f} MB）")
        if "--open" in sys.argv:
            os.startfile(PDF)  # noqa: S606 (Windows)
    else:
        sys.exit("生成失败：请改用浏览器手动打印。")


if __name__ == "__main__":
    main()
