# -*- coding: utf-8 -*-
import pandas as pd

df = pd.read_csv(r"D:\code\Ideas\MyBooks\中国地理知识手册\data\beijing_nightlight_1986_2024.csv")
print("Columns:", df.columns.tolist())
print(df.iloc[0])
print("Distinct district codes and counts:")
# Find the code column
for c in df.columns:
    if "110101" in str(df[c].values):
        print("Found code col:", c)
        print(df.groupby(c).size())
