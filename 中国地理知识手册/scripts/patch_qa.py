# -*- coding: utf-8 -*-
p = '中国地理知识手册/scripts/qa_structure.py'
txt = open(p, encoding='utf-8').read().replace('\r\n', '\n')
old = """        if f.startswith("14-"):
            want = "14." + str(int(f[3:5]))"""
new = """        if f.startswith("14-00"):
            want = None
        elif f.startswith("14-"):
            want = "14." + str(int(f[3:5]))"""
txt = txt.replace(old, new)
open(p, 'w', encoding='utf-8').write(txt)
print('Patch applied')
