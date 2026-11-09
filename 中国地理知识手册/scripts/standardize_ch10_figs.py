# -*- coding: utf-8 -*-
"""规范化并生成第 10 章的全部 10 幅高清专业图表 (fig10-1 至 fig10-10)。
确保编号在节内严格连续，各图命名清晰规范。
"""
import os
import shutil
import glob

FIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "figures")

# 目标文件名映射
# 现有文件 -> 目标文件
# fig10-1_城市规模金字塔.png -> fig10-1_城市规模金字塔.png (保持)
# fig10-2_超大特大城市分布.png -> fig10-2_超大特大城市分布.png (保持)
# fig10-8_城镇化进程与收缩型城市空间分异.png -> fig10-3_城镇化进程与收缩型城市空间分异.png
# fig10-3_主要城市群分布.png -> fig10-4_主要城市群分布.png
# fig10-4_五大城市群对比.png -> fig10-5_五大城市群对比.png
# fig10-7_国家中心城市与都市圈通勤同城化.png -> fig10-6_国家中心城市与都市圈通勤同城化.png
# fig10-5_历史文化名城与八大古都.png -> fig10-7_历史文化名城与八大古都.png
# fig10-9_古代城市营建形制演进与中轴线.png -> fig10-8_古代城市营建形制演进与中轴线.png
# fig10-6_传统民居与风味地理.png -> fig10-9_传统民居与风味地理.png
# fig10-10_八大菜系地理成因与茶酒文化分布.png -> fig10-10_八大菜系地理成因与茶酒文化分布.png (保持)

def main():
    # 临时重命名避免覆盖冲突
    temp_map = {
        "fig10-8_城镇化进程与收缩型城市空间分异.png": "temp_fig10-3.png",
        "fig10-3_主要城市群分布.png": "temp_fig10-4.png",
        "fig10-4_五大城市群对比.png": "temp_fig10-5.png",
        "fig10-7_国家中心城市与都市圈通勤同城化.png": "temp_fig10-6.png",
        "fig10-5_历史文化名城与八大古都.png": "temp_fig10-7.png",
        "fig10-9_古代城市营建形制演进与中轴线.png": "temp_fig10-8.png",
        "fig10-6_传统民居与风味地理.png": "temp_fig10-9.png",
    }
    
    for old_name, temp_name in temp_map.items():
        p_old = os.path.join(FIG_DIR, old_name)
        p_temp = os.path.join(FIG_DIR, temp_name)
        if os.path.exists(p_old):
            shutil.move(p_old, p_temp)
            print(f"Move {old_name} -> {temp_name}")

    final_map = {
        "temp_fig10-3.png": "fig10-3_城镇化进程与收缩型城市空间分异.png",
        "temp_fig10-4.png": "fig10-4_主要城市群分布.png",
        "temp_fig10-5.png": "fig10-5_五大城市群对比.png",
        "temp_fig10-6.png": "fig10-6_国家中心城市与都市圈通勤同城化.png",
        "temp_fig10-7.png": "fig10-7_历史文化名城与八大古都.png",
        "temp_fig10-8.png": "fig10-8_古代城市营建形制演进与中轴线.png",
        "temp_fig10-9.png": "fig10-9_传统民居与风味地理.png",
    }
    
    for temp_name, new_name in final_map.items():
        p_temp = os.path.join(FIG_DIR, temp_name)
        p_new = os.path.join(FIG_DIR, new_name)
        if os.path.exists(p_temp):
            shutil.move(p_temp, p_new)
            print(f"Move {temp_name} -> {new_name}")

    print("\nFinal fig10 files:")
    for f in sorted(glob.glob(os.path.join(FIG_DIR, "fig10-*.png"))):
        print(os.path.basename(f))

if __name__ == "__main__":
    main()
