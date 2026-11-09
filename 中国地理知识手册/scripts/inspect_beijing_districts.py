# -*- coding: utf-8 -*-
import json
import geopandas as gpd

path = r"D:\code\Ideas\MyBooks\中国地理知识手册\data\boundaries\datav\110000_full.json"
gdf = gpd.read_file(path)
print(gdf[["adcode", "name", "level", "center"]].to_string())
