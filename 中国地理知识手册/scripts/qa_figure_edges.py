# -*- coding: utf-8 -*-
"""批量检查成品图的画布边界问题：标题/内容触边、地图溢出画布。"""
import os, glob
from PIL import Image
import numpy as np

FIG = r"D:\code\Ideas\MyBooks\中国地理知识手册\figures"

rows = []
for p in sorted(glob.glob(os.path.join(FIG, "*.png"))):
    try:
        im = Image.open(p).convert("RGB")
    except Exception as e:
        rows.append((os.path.basename(p), -1, -1, "OPEN_FAIL", "", ""))
        continue
    a = np.asarray(im)
    h, w, _ = a.shape
    # 背景判定：与四角众数颜色接近即视为背景
    corners = np.concatenate([a[0, 0], a[0, -1], a[-1, 0], a[-1, -1]]).reshape(4, 3)
    bg = np.median(corners, axis=0)
    nonbg = (np.abs(a.astype(int) - bg.astype(int)).sum(axis=2) > 30)
    # 每条边向内 3 像素内的非背景像素比例
    def edge_ratio(sl):
        return nonbg[sl].mean() if nonbg[sl].size else 0.0
    top = edge_ratio(np.s_[:3, :])
    bot = edge_ratio(np.s_[-3:, :])
    left = edge_ratio(np.s_[:, :3])
    right = edge_ratio(np.s_[:, -3:])
    # 内容外接框到画布四边的距离
    ys, xs = np.where(nonbg)
    if len(ys) == 0:
        rows.append((os.path.basename(p), w, h, "BLANK", "", ""))
        continue
    d_top, d_bot = ys.min(), h - 1 - ys.max()
    d_left, d_right = xs.min(), w - 1 - xs.max()
    flags = []
    for name, v in (("上", top), ("下", bot), ("左", left), ("右", right)):
        if v > 0.02:
            flags.append(name)
    rows.append((os.path.basename(p), w, h, ",".join(flags) if flags else "OK",
                 f"{d_top}/{d_bot}", f"{d_left}/{d_right}"))

bad = [r for r in rows if r[3] not in ("OK", "BLANK")]
print(f"总计 {len(rows)} 张；边缘触边 {len(bad)} 张\n")
print(f"{'文件':<62}{'宽x高':<13}{'触边':<8}{'上下距':<10}{'左右距'}")
for r in bad:
    print(f"{r[0][:60]:<62}{str(r[1])+'x'+str(r[2]):<13}{r[3]:<8}{r[4]:<10}{r[5]}")
