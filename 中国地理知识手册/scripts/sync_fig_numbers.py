# -*- coding: utf-8 -*-
"""同步分省图号：把 ch13_prov_* 生成的 fig13-1xx 覆盖到迁移后的 fig14-xxx。

第 13.5 节独立为第 14 章时，成品图统一重命名为 fig14-*，但绘图脚本仍输出
fig13-1xx。重跑脚本后必须本步骤，否则新版图只会落在旧号文件上，正文引用的
仍是旧图。

按"图名后缀"匹配（图名唯一），不改动 fig13-1..13-11 等真正的第 13 章图。
"""
import os
import re
import shutil

FIG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "figures")

pat13 = re.compile(r"^fig13-(\d{1,3})_(.+)\.png$")
pat14 = re.compile(r"^fig14-(\d{1,3})_(.+)\.png$")

by_name14 = {}
for fn in os.listdir(FIG):
    m = pat14.match(fn)
    if m:
        by_name14[m.group(2)] = fn

done, missing = [], []
for fn in sorted(os.listdir(FIG)):
    m = pat13.match(fn)
    if not m:
        continue
    name = m.group(2)
    # 分省系列从 fig13-7（北京市地势图）起编号，一直排到 fig13-218，
    # 旧区间只覆盖 100~218，导致北京—陕西（7~26）的新版图没同步过去。
    # 这里不再按号段过滤，改为纯按图名匹配：真正的第 13 章图
    # （四大地理区域划分图 / 北方地区专题图 …）没有同名 fig14 文件，
    # 自然落进 missing 而不会被误覆盖。
    target = by_name14.get(name)
    if not target:
        missing.append(fn)
        continue
    src = os.path.join(FIG, fn)
    dst = os.path.join(FIG, target)
    if os.path.getmtime(src) > os.path.getmtime(dst):
        shutil.copyfile(src, dst)
        done.append((fn, target))
    else:
        done.append((fn, target + "（已是最新，跳过）"))

print(f"同步 {len(done)} 项：")
for a, b in done:
    print(f"  {a}  →  {b}")
if missing:
    print(f"\n无对应 fig14 文件 {len(missing)} 项（需人工确认图号）：")
    for fn in missing:
        print("  ", fn)
