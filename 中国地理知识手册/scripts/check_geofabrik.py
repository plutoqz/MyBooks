# -*- coding: utf-8 -*-
import urllib.request
import re

url = 'https://download.geofabrik.de/asia/china/tianjin.html'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
        matches = [h for h in re.findall(r'href=[\'"]([^\'"]+)[\'"]', html)]
        print("Tianjin files:", matches)
except Exception as e:
    print("Error:", e)
