# -*- coding: utf-8 -*-
import urllib.request
import re

url = "https://download.bbbike.org/osm/bbbike/"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        content = resp.read().decode('utf-8', errors='ignore')
        cities = re.findall(r'href="([^"/]+)/"', content)
        print("Total cities:", len(cities))
        tj = [c for c in cities if "tianjin" in c.lower()]
        print("Tianjin matches:", tj)
        chinese = [c for c in cities if any(k in c.lower() for k in ["tianjin", "beijing", "shanghai", "guangzhou", "shenzhen", "chengdu", "wuhan", "chongqing", "hangzhou"])]
        print("Chinese cities in BBBike:", chinese)
except Exception as e:
    print("Error:", e)
