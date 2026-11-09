# -*- coding: utf-8 -*-
import pandas as pd

df = pd.read_csv(r"D:\code\Ideas\MyBooks\中国地理知识手册\data\beijing_nightlight_1986_2024.csv")
cols = ['year', 'prov_name', 'city_name', 'district_name', 'prov_code', 'city_code', 'district_code', 'sum', 'mean', 'min', 'max', 'std', 'count', 'extra']
df.columns = cols[:len(df.columns)]

name_map = {
    110101: "东城区",
    110102: "西城区",
    110105: "朝阳区",
    110106: "丰台区",
    110107: "石景山区",
    110108: "海淀区",
    110109: "门头沟区",
    110111: "房山区",
    110112: "通州区",
    110113: "顺义区",
    110114: "昌平区",
    110115: "大兴区",
    110116: "怀柔区",
    110117: "平谷区",
    110118: "密云区",
    110119: "延庆区"
}

df["district_code"] = df["district_code"].astype(int)
df["district_name"] = df["district_code"].map(name_map)
df["year"] = df["year"].astype(int)
df["prov_name"] = "北京市"
df["city_name"] = "北京市"

out_csv = r"D:\code\Ideas\MyBooks\中国地理知识手册\data\beijing_nightlight_clean.csv"
df.to_csv(out_csv, index=False, encoding="utf-8-sig")
print("Saved clean nightlight data successfully. Sample:")
print(df[["year", "district_code", "district_name", "sum", "mean"]].head())
