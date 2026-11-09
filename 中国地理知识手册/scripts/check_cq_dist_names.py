# -*- coding: utf-8 -*-
import pandas as pd

df = pd.read_excel(r'D:\code\Ideas\MyBooks\中国地理知识手册\中国省市数据\夜间灯光数据-省、市、县（1986-2024年）\夜间灯光数据-区县（1986-2024年）.xlsx')
cols = ['year', 'prov_name', 'city_name', 'district_name', 'prov_code', 'city_code', 'district_code', 'sum', 'mean', 'min', 'max', 'std', 'count', 'extra']
df.columns = cols[:len(df.columns)]
df_cq = df[df['prov_code'].astype(str).str.startswith('50') | df['prov_name'].astype(str).str.contains('重庆')]
dists = df_cq[['district_code', 'district_name', 'city_name']].drop_duplicates()

with open(r'D:\code\Ideas\MyBooks\中国地理知识手册\data\cq_dist_names.txt', 'w', encoding='utf-8') as f:
    for idx, r in dists.iterrows():
        f.write(f"{r['district_code']}\t{r['district_name']}\t{r['city_name']}\n")
print("Done writing cq_dist_names.txt")
