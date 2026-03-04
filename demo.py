import pandas as pd

# 读取英文 CSV 文件
df = pd.read_csv('static/china_water_pollution_data.csv')

# 字段翻译字典
columns_map = {
    'Province': '省份',
    'City': '城市',
    'Monitoring_Station': '监测站点',
    'Latitude': '纬度',
    'Longitude': '经度',
    'Date': '日期',
    'Water_Temperature_C': '水温(℃)',
    'pH': 'pH',
    'Dissolved_Oxygen_mg_L': '溶解氧(mg/L)',
    'Conductivity_uS_cm': '电导率(μS/cm)',
    'Turbidity_NTU': '浊度(NTU)',
    'Nitrate_mg_L': '硝酸盐(mg/L)',
    'Nitrite_mg_L': '亚硝酸盐(mg/L)',
    'Ammonia_N_mg_L': '氨氮(mg/L)',
    'Total_Phosphorus_mg_L': '总磷(mg/L)',
    'Total_Nitrogen_mg_L': '总氮(mg/L)',
    'COD_mg_L': '化学需氧量(mg/L)',
    'BOD_mg_L': '生化需氧量(mg/L)',
    'Heavy_Metals_Pb_ug_L': '铅(ug/L)',
    'Heavy_Metals_Cd_ug_L': '镉(ug/L)',
    'Heavy_Metals_Hg_ug_L': '汞(ug/L)',
    'Coliform_Count_CFU_100mL': '大肠菌群(CFU/100mL)',
    'Water_Quality_Index': '水质指数',
    'Pollution_Level': '污染等级',
    'Remarks': '备注'
}

# 修改字段名
df.rename(columns=columns_map, inplace=True)

# 保存为中文 CSV
df.to_csv('water_quality.csv', index=False, encoding='utf-8-sig')

print("✅ 字段已翻译，文件已保存为 water_quality_中文.csv")
