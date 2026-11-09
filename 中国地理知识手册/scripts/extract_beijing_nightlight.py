# -*- coding: utf-8 -*-
import os
import pandas as pd

base_data = r"D:\code\Ideas\MyBooks\中国地理知识手册\中国省市数据"
nl_file = os.path.join(base_data, "夜间灯光数据-省、市、县（1986-2024年）", "夜间灯光数据-区县（1986-2024年）.xlsx")

print("Loading Excel...")
df = pd.read_excel(nl_file)
print("Columns:", df.columns.tolist())
print("Head:")
print(df.head(2))

# Filter Beijing
# Check which column has province code or name
prov_col = [c for c in df.columns if "省" in c or "prov" in c.lower()][0]
name_col = [c for c in df.columns if "名称" in c or "name" in c.lower()]
code_col = [c for c in df.columns if "代码" in c or "code" in c.lower()]
print(f"prov_col: {prov_col}, name_cols: {name_col}, code_cols: {code_col}")

bj = df[df[prov_col].astype(str).str.contains("110000|北京")]
districts = bj[[c for c in df.columns if "区" in c or "县" in c or "名称" in c]].drop_duplicates()
print("Beijing Districts in Nightlight data:")
print(districts.to_string())

# Save filtered Beijing nightlight data as a quick feather/parquet/csv for fast lookup
out_csv = r"D:\code\Ideas\MyBooks\中国地理知识手册\data\beijing_nightlight_1986_2024.csv"
bj.to_csv(out_csv, index=False, encoding="utf-8-sig")
print(f"Saved {len(bj)} rows to {out_csv}")
