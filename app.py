from flask import Flask, render_template, request, session, redirect, url_for, jsonify, flash
import pandas as pd
import random
from datetime import datetime
import bcrypt
import mysql.connector
from mysql.connector import Error
import json
import os
import requests
from flask import request, jsonify
import decimal
import csv
from werkzeug.exceptions import HTTPException


app = Flask(__name__)
app.secret_key = 'super_secret_random_string_123456'  # 修改为你自己的密钥

# 添加错误处理
@app.errorhandler(500)
def internal_error(error):
    import traceback
    print(f"500错误详情: {error}")
    print(f"错误堆栈: {traceback.format_exc()}")
    return "服务器内部错误，请稍后重试", 500

@app.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        return e
    import traceback
    print(f"未处理的异常: {e}")
    print(f"异常堆栈: {traceback.format_exc()}")
    return "发生未知错误，请稍后重试", 500


@app.route('/favicon.ico')
def favicon():
    return '', 204
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 创建 uploads 文件夹
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# 注册 zip 到 Jinja2 环境
app.jinja_env.globals['zip'] = zip

# 数据库配置
db_config = {
    'host': 'localhost',
    'database': 'heavymetal',  # 你的数据库名
    'user': 'root',  # 你的用户名
    'password': '123456'  # 你的密码
}

# OneNet 云平台配置（请替换为你的真实信息）
ONENET_API_KEY = os.environ.get('ONENET_API_KEY', '')
ONENET_DEVICE_ID = os.environ.get('ONENET_DEVICE_ID', '')

# 期望从云端获取的监测数据流（需与设备上报到 OneNet 的 datastream 名称一致）
ION_STREAMS = [
    "Pb","Cd","Hg","Cu","Cr","Ni","As","Mn","Fe","Zn","Se","Ba","Al","Ag",
    "TDS","Temperature","pH","Turbidity"
]

# 水质常规指标 + 重金属阈值表
THRESHOLDS = {
    "pH": (6.5, 8.5),            # pH值正常范围（无单位）
    "DO": 5.0,                   # 溶解氧（mg/L）≥5.0
    "Conductivity": 1500,        # 电导率（μS/cm）≤1500
    "Turbidity": 1.0,            # 浊度（NTU）≤1.0
    "Nitrate": 10.0,             # 硝酸盐（mg/L）≤10
    "Nitrite": 0.1,              # 亚硝酸盐（mg/L）≤0.1
    "Ammonia_N": 0.5,            # 氨氮（mg/L）≤0.5
    "Phosphorus": 0.2,           # 磷（mg/L）≤0.2
    "Nitrogen": 1.0,             # 氮（mg/L）≤1.0
    "COD": 3.0,                  # 化学需氧量（mg/L）≤3.0
    "BOD": 3.0,                  # 生化需氧量（mg/L）≤3.0

    # ⚛ 重金属指标（mg/L）
    "Pb": 0.01,    # 铅 Lead ≤ 0.01 mg/L
    "Cd": 0.005,   # 镉 Cadmium ≤ 0.005 mg/L
    "Hg": 0.001,   # 汞 Mercury ≤ 0.001 mg/L
    "Cu": 1.0,     # 铜 Copper ≤ 1.0 mg/L
    "Cr": 0.05,    # 铬 Chromium ≤ 0.05 mg/L
    "Ni": 0.07,    # 镍 Nickel ≤ 0.07 mg/L
    "As": 0.01,    # 砷 Arsenic ≤ 0.01 mg/L
    "Mn": 0.1,     # 锰 Manganese ≤ 0.1 mg/L
    "Fe": 0.3,     # 铁 Iron ≤ 0.3 mg/L
    "Zn": 1.0,     # 锌 Zinc ≤ 1.0 mg/L
    "Se": 0.01,    # 硒 Selenium ≤ 0.01 mg/L
    "Ba": 0.7,     # 钡 Barium ≤ 0.7 mg/L
    "Al": 0.2,     # 铝 Aluminium ≤ 0.2 mg/L
    "Ag": 0.05     # 银 Silver ≤ 0.05 mg/L
}


# 中文字段名到英文金属名及单位的映射
CHINESE_METAL_MAP = {
    "水温(℃)": ("Temperature", None),
    "pH": ("pH", None),
    "溶解氧(mg/L)": ("DO", "mg/L"),
    "电导率(μS/cm)": ("Conductivity", "μS/cm"),
    "浊度(NTU)": ("Turbidity", "NTU"),
    "硝酸盐(mg/L)": ("Nitrate", "mg/L"),
    "亚硝酸盐(mg/L)": ("Nitrite", "mg/L"),
    "氨氮(mg/L)": ("Ammonia_N", "mg/L"),
    "磷(mg/L)": ("Phosphorus", "mg/L"),
    "氮(mg/L)": ("Nitrogen", "mg/L"),
    "化学需氧量(mg/L)": ("COD", "mg/L"),
    "生化需氧量(mg/L)": ("BOD", "mg/L"),
    "铅(ug/L)": ("Pb", "ug/L"),
    "镉(ug/L)": ("Cd", "ug/L"),
    "汞(ug/L)": ("Hg", "ug/L"),
    "铜(ug/L)": ("Cu", "ug/L"),
    "铬(ug/L)": ("Cr", "ug/L"),
    "镍(ug/L)": ("Ni", "ug/L"),
    "大肠菌群(CFU/100mL)": ("E_coli", None)
}


def analyze_csv_file(filepath):
    results = []
    try:
        # 确保文件路径是绝对路径，并处理Windows路径问题
        if not os.path.isabs(filepath):
            filepath = os.path.abspath(filepath)
        
        # 检查文件是否存在
        if not os.path.exists(filepath):
            print(f"文件不存在: {filepath}")
            return results
            
        with open(filepath, 'r', encoding='utf-8-sig', errors='ignore') as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                return results
            # 新的映射，带单位
            field_map = {}
            for ch in reader.fieldnames:
                mapping = CHINESE_METAL_MAP.get(ch, (ch, None))
                if isinstance(mapping, tuple):
                    en_col, unit = mapping
                else:
                    en_col, unit = mapping, None
                field_map[ch] = (en_col, unit)
            for row in reader:
                result = {}
                for ch_col, (en_col, unit) in field_map.items():
                    if en_col in THRESHOLDS and row.get(ch_col) not in (None, '', 'NA'):
                        try:
                            value = float(row[ch_col])
                        except Exception:
                            value = None
                        if value is not None:
                            # 单位换算
                            if unit == "ug/L":
                                value = value / 1000  # ug/L -> mg/L
                            threshold = THRESHOLDS[en_col]
                            # pH 特殊处理
                            if en_col == "pH" and isinstance(threshold, tuple):
                                exceed = not (threshold[0] <= value <= threshold[1])
                            elif en_col == "DO":  # 溶解氧是下限
                                exceed = value < threshold
                            else:
                                exceed = value > threshold
                            result[en_col] = {
                                "value": value,
                                "exceed": exceed
                            }
                if result:
                    results.append(result)
    except Exception as e:
        print(f"分析文件 {filepath} 失败: {e}")
    return results


# 数据库连接函数
def create_db_connection():
    try:
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"数据库连接错误: {e}")
        return None


# 初始化数据库（创建表）
def init_db():
    connection = create_db_connection()
    if connection:
        cursor = connection.cursor()
        # 创建用户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT PRIMARY KEY AUTO_INCREMENT,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # 创建水质数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS water_quality_data (
                id INT PRIMARY KEY AUTO_INCREMENT,
                user_id INT NOT NULL,
                file_name VARCHAR(255) NOT NULL,
                upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                latitude DECIMAL(10, 6),
                longitude DECIMAL(10, 6),
                province VARCHAR(50),
                city VARCHAR(50),
                metals JSON,
                data JSON,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        # 创建 points 表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS points (
                id INT PRIMARY KEY AUTO_INCREMENT,
                user_id INT NOT NULL,
                file_name VARCHAR(255) NOT NULL,
                upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                city VARCHAR(50),
                latitude DECIMAL(10, 6),
                longitude DECIMAL(10, 6),
                is_exceed BOOLEAN,
                exceed_items VARCHAR(255),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        # 创建 analysis_results 表（用于设备数据）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analysis_results (
                id INT PRIMARY KEY AUTO_INCREMENT,
                user_id INT NOT NULL,
                file_name VARCHAR(255) NOT NULL,
                upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                latitude DECIMAL(10, 6),
                longitude DECIMAL(10, 6),
                city VARCHAR(50),
                is_exceed BOOLEAN,
                exceed_items VARCHAR(255),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        connection.commit()
        cursor.close()
        connection.close()


# 模拟传感器数据
def generate_sensor_data():
    cities = ["武汉", "长沙", "南京", "杭州", "成都"]
    data = []
    for city in cities:
        data.append({
            "city": city,
            "latitude": round(random.uniform(29, 32), 4),
            "longitude": round(random.uniform(112, 121), 4),
            "cadmium": round(random.uniform(0.01, 0.5), 4),
            "lead": round(random.uniform(0.01, 0.5), 4),
            "mercury": round(random.uniform(0.001, 0.1), 4),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    return data


# 登录校验
def check_login(username, password):
    connection = create_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        connection.close()

        if user and isinstance(user, dict) and 'password_hash' in user and isinstance(user['password_hash'], str):
            try:
                if bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                    return True
            except Exception as e:
                print(f"密码校验异常: {e}")
        
        # 兼容 password_hash 已为 bytes 的情况
        if user and isinstance(user, dict) and 'password_hash' in user and isinstance(user['password_hash'], bytes):
            try:
                if bcrypt.checkpw(password.encode('utf-8'), user['password_hash']):
                    return True
            except Exception as e:
                print(f"密码校验异常: {e}")
        
    return False


# 用户注册
def register_user(username, password):
    connection = create_db_connection()
    if connection:
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        try:
            cursor = connection.cursor()
            cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                           (username, password_hash))
            connection.commit()
            cursor.close()
            connection.close()
            return True
        except Error as e:
            print(f"注册失败: {e}")
            connection.close()
    return False


# 保存上传的数据
def save_water_quality_data(user_id, file_name, latitude, longitude, province, city, metals, data):
    connection = create_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO water_quality_data 
                (user_id, file_name, latitude, longitude, province, city, metals, data)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (user_id, file_name, latitude, longitude, province, city, json.dumps(metals), json.dumps(data))
            )
            connection.commit()
            cursor.close()
            connection.close()
            return True
        except Error as e:
            print(f"保存数据失败: {e}")
            connection.close()
    return False


# 获取用户上传的数据
def get_user_data(user_id):
    """
    获取指定用户上传的水质检测数据
    """
    connection = create_db_connection()
    user_data = []

    def safe_float(val):
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, decimal.Decimal):
            return float(val)
        if isinstance(val, str) and val.strip() != '':
            try:
                return float(val)
            except Exception:
                return None
        return None

    if connection:
        cursor = connection.cursor(dictionary=True)
        try:
            # 查询用户上传的数据
            sql = """
                SELECT 
                    id, 
                    file_name, 
                    upload_time, 
                    latitude, 
                    longitude, 
                    province, 
                    city, 
                    metals, 
                    data
                FROM water_quality_data
                WHERE user_id = %s
                ORDER BY upload_time DESC
            """
            cursor.execute(sql, (user_id,))
            rows = cursor.fetchall()

            for row in rows:
                # 确保 row 是 dict
                if not isinstance(row, dict):
                    continue
                # 解析 metals JSON 字段
                metals_data = {}
                if row.get("metals"):
                    try:
                        metals_data = json.loads(row["metals"]) if isinstance(row["metals"], str) else row["metals"]
                    except Exception:
                        metals_data = {}  # 如果 JSON 解析失败，返回空字典
                # 解析 data JSON 字段
                raw_data = {}
                if row.get("data"):
                    try:
                        raw_data = json.loads(row["data"]) if isinstance(row["data"], str) else row["data"]
                    except Exception:
                        raw_data = {}
                # 构建更友好的数据结构
                user_data.append({
                    "id": row.get("id"),
                    "file_name": row.get("file_name") or "手动录入",
                    "upload_time": str(row.get("upload_time")),
                    "latitude": safe_float(row.get("latitude")),
                    "longitude": safe_float(row.get("longitude")),
                    "province": row.get("province") or "",
                    "city": row.get("city") or "",
                    "metals": metals_data,  # 已解析为字典
                    "raw_data": raw_data  # 保留原始数据 JSON（如果需要）
                })

        finally:
            cursor.close()
            connection.close()

    return user_data


# 路由：首页（登录页）
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if check_login(username, password):
            session["user"] = username
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="用户名或密码错误")
    return render_template("login.html", error="")


# 路由：注册页
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if register_user(username, password):
            return redirect(url_for("index"))
        else:
            return render_template("register.html", error="注册失败，用户名可能已存在")
    return render_template("register.html", error="")


PROVINCE_TO_ECHARTS = {
    "北京": "北京市",
    "天津": "天津市",
    "上海": "上海市",
    "重庆": "重庆市",
    "河北": "河北省",
    "山西": "山西省",
    "辽宁": "辽宁省",
    "吉林": "吉林省",
    "黑龙江": "黑龙江省",
    "江苏": "江苏省",
    "浙江": "浙江省",
    "安徽": "安徽省",
    "福建": "福建省",
    "江西": "江西省",
    "山东": "山东省",
    "河南": "河南省",
    "湖北": "湖北省",
    "湖南": "湖南省",
    "广东": "广东省",
    "海南": "海南省",
    "四川": "四川省",
    "贵州": "贵州省",
    "云南": "云南省",
    "陕西": "陕西省",
    "甘肃": "甘肃省",
    "青海": "青海省",
    "台湾": "台湾省",
    "内蒙古": "内蒙古自治区",
    "广西": "广西壮族自治区",
    "西藏": "西藏自治区",
    "宁夏": "宁夏回族自治区",
    "新疆": "新疆维吾尔自治区",
    "香港": "香港特别行政区",
    "澳门": "澳门特别行政区"
}

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("index"))

    import json
    connection = create_db_connection()
    sensor_data = []
    pollution_counter = {}
    province_exceed_count = {}
    warnings = []
    bar_top_provinces = []
    def norm_coord(val):
        try:
            return f"{float(val):.6f}"
        except Exception:
            return str(val)
    def norm_city(val):
        return (val or '').strip()
    def safe_float(val):
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            try:
                return float(val)
            except Exception:
                return None
        return None
    if connection:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id, city, province, latitude, longitude, is_exceed, exceed_items, upload_time FROM points")
            rows = cursor.fetchall()
            cursor.execute("SELECT city, latitude, longitude, metals FROM water_quality_data")
            wq_rows = cursor.fetchall()
            wq_map = {}
            for wq in wq_rows:
                key = (norm_city(wq.get("city")), norm_coord(wq.get("latitude")), norm_coord(wq.get("longitude")))
                metals = {}
                if wq.get("metals"):
                    try:
                        metals = json.loads(wq["metals"]) if isinstance(wq["metals"], str) else wq["metals"]
                    except Exception:
                        metals = {}
                wq_map[key] = metals
            for row in rows:
                city = norm_city(row.get("city"))
                province = row.get("province") or ""
                echarts_province = PROVINCE_TO_ECHARTS.get(province, province)
                cadmium = None
                exceed_items = row.get("exceed_items")
                upload_time = str(row.get("upload_time")) if "upload_time" in row else ""
                if exceed_items and isinstance(exceed_items, str):
                    items = exceed_items.split(",")
                else:
                    items = []
                for item in items:
                    if item == "Cd":
                        cadmium = 1
                    if item:
                        pollution_counter[item] = pollution_counter.get(item, 0) + 1
                        # 预警信息收集
                        warnings.append({
                            "time": upload_time[:19],
                            "province": echarts_province,
                            "city": city,
                            "metal": item
                        })
                if items and echarts_province:
                    province_exceed_count[echarts_province] = province_exceed_count.get(echarts_province, 0) + 1
                lat = safe_float(row.get("latitude"))
                lon = safe_float(row.get("longitude"))
                wq_key = (city, norm_coord(lat), norm_coord(lon))
                metals = wq_map.get(wq_key, {})
                if not metals:
                    metals = {}
                    if exceed_items:
                        for metal in exceed_items.split(","):
                            if metal:
                                metals[metal] = {"value": None, "exceed": True}
                    if not metals:
                        metals["未知"] = {"value": None, "exceed": False}
                sensor_data.append({
                    "city": city,
                    "province": echarts_province,
                    "latitude": lat,
                    "longitude": lon,
                    "cadmium": cadmium if cadmium is not None else 0,
                    "metals": metals
                })
            # 只保留最近5条预警，按时间倒序
            warnings = sorted(warnings, key=lambda x: x["time"], reverse=True)[:5]
            # 生成超标排行榜（前10名）
            bar_top_provinces = sorted(province_exceed_count.items(), key=lambda x: x[1], reverse=True)[:10]
        finally:
            cursor.close()
            connection.close()
    pollution = {
        "types": list(pollution_counter.keys()),
        "counts": list(pollution_counter.values())
    }
    return render_template(
        "dashboard.html",
        sensor_data=json.dumps(sensor_data, ensure_ascii=False),
        pollution=json.dumps(pollution, ensure_ascii=False),
        province_exceed_count=json.dumps(province_exceed_count, ensure_ascii=False),
        warnings=warnings,
        bar_top_provinces=bar_top_provinces
    )


# =============== OneNet 设备数据拉取 ===============
def fetch_onenet_datapoints():
    """从 OneNet 拉取最近一段时间的数据点，返回 {stream_id: latest_value}。"""
    import time
    url = f"https://iot-api.heclouds.com/devices/{ONENET_DEVICE_ID}/datapoints"
    headers = {"api-key": ONENET_API_KEY}
    now = int(time.time())
    params = {"start": now - 300, "limit": 200}
    r = requests.get(url, headers=headers, params=params, timeout=10)
    r.raise_for_status()
    payload = r.json()
    latest = {}
    if payload and isinstance(payload.get("data"), dict):
        streams = payload["data"].get("datastreams", [])
        for s in streams:
            sid = s.get("id")
            if not sid or sid not in ION_STREAMS:
                continue
            pts = s.get("datapoints") or []
            if pts:
                latest[sid] = pts[-1].get("value")
    return latest


@app.route("/api/device/start_detection", methods=["POST"])
def api_start_detection():
    if "user" not in session:
        return jsonify({"ok": False, "error": "未登录"}), 401
    
    # 检查配置是否完整
    if not ONENET_API_KEY or not ONENET_DEVICE_ID or ONENET_API_KEY == '' or ONENET_DEVICE_ID == '':
        return jsonify({"ok": False, "error": "OneNet配置未完成，请在app.py中设置ONENET_API_KEY和ONENET_DEVICE_ID"}), 400
    
    try:
        values = fetch_onenet_datapoints()
        result = {k: values.get(k) for k in ION_STREAMS}
        return jsonify({"ok": True, "data": result})
    except Exception as e:
        return jsonify({"ok": False, "error": f"OneNet连接失败: {str(e)}"}), 500


# 路由：数据上传页
@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # 获取经纬度和省市信息
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        province = request.form.get('province')
        city = request.form.get('city')

        # 获取手动录入的金属值
        pb = request.form.get('pb')
        cd = request.form.get('cd')
        hg = request.form.get('hg')
        cu = request.form.get('cu')
        other_names = request.form.getlist('other_name[]')
        other_values = request.form.getlist('other_value[]')
        # metals = {...}
        metals = {}
        if pb:
            metals["Pb"] = pb
        if cd:
            metals["Cd"] = cd
        if hg:
            metals["Hg"] = hg
        if cu:
            metals["Cu"] = cu
        for name, value in zip(other_names, other_values):
            if name and value:
                metals[name] = value

        # 获取当前用户ID
        user_id = None
        if 'user' in session:
            connection = create_db_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                cursor.execute("SELECT id FROM users WHERE username = %s", (session["user"],))
                user = cursor.fetchone()
                cursor.close()
                connection.close()
                if user and isinstance(user, dict) and 'id' in user:
                    user_id = user['id']
        if not user_id:
            flash("用户未登录或获取用户ID失败", "danger")
            return redirect(url_for('upload_file'))

        # 文件上传处理
        file = request.files.get('file')
        if file and file.filename != '':
            filename = str(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            flash(f"文件 {filename} 上传成功！", "success")
            # metals和data字段可根据实际需求解析文件后填充，这里简单存空字典
            save_water_quality_data(user_id, filename, latitude, longitude, province, city, metals, data={})

            # 新增：分析CSV并写入points表
            import csv
            from datetime import datetime
            from decimal import Decimal
            connection = create_db_connection()
            if connection:
                try:
                    cursor = connection.cursor()
                    upload_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    # 确保文件路径是绝对路径
                    if not os.path.isabs(filepath):
                        filepath = os.path.abspath(filepath)
                    
                    # 检查文件是否存在
                    if not os.path.exists(filepath):
                        print(f"文件不存在: {filepath}")
                        return redirect(url_for('upload_file'))
                        
                    file_analysis = analyze_csv_file(filepath)
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        reader = csv.DictReader(f)
                        for idx, csv_row in enumerate(reader):
                            lat = csv_row.get("纬度")
                            lon = csv_row.get("经度")
                            city_val = csv_row.get("城市") or ""
                            # 匹配分析结果
                            is_exceed = False
                            exceed_items = []
                            if idx < len(file_analysis):
                                record = file_analysis[idx]
                                for item, info in record.items():
                                    if info["exceed"]:
                                        is_exceed = True
                                        exceed_items.append(item)
                            # 类型转换
                            try:
                                lat = float(lat) if lat not in (None, "") else None
                            except Exception:
                                lat = None
                            try:
                                lon = float(lon) if lon not in (None, "") else None
                            except Exception:
                                lon = None
                            is_exceed_int = 1 if is_exceed else 0
                            # 写入points表
                            cursor.execute(
                                """
                                INSERT INTO points (user_id, file_name, upload_time, city, latitude, longitude, is_exceed, exceed_items)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                """,
                                (user_id, filename, upload_time, city_val, lat, lon, is_exceed_int, ','.join(exceed_items))
                            )
                    connection.commit()
                    cursor.close()
                except Exception as e:
                    print(f"写入points表失败: {e}")
                finally:
                    connection.close()
        elif any([pb, cd, hg, cu] + other_names + other_values):
            # 生成唯一文件名
            from datetime import datetime
            unique_filename = f"manual_entry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            # 保存手动录入数据
            data = {
                "纬度": latitude,
                "经度": longitude,
                "省份": province,
                "城市": city,
                **metals
            }
            # 只保留最新一行，覆盖写入
            df = pd.DataFrame([data])
            df.to_csv(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename),
                      index=False, encoding='utf-8-sig', mode='w', header=True)
            flash("手动录入数据已保存", "success")
            save_water_quality_data(user_id, unique_filename, latitude, longitude, province, city, metals, data)

            # 新增：写入points表，增加调试输出
            print('准备写入points表 user_id:', user_id, 'file_name:', unique_filename)
            connection = create_db_connection()
            if connection:
                try:
                    cursor = connection.cursor()
                    upload_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    try:
                        lat = float(latitude) if latitude not in (None, "") else None
                    except Exception:
                        lat = None
                    try:
                        lon = float(longitude) if longitude not in (None, "") else None
                    except Exception:
                        lon = None
                    city_val = city or ""
                    is_exceed = 0
                    exceed_items = []
                    THRESHOLDS = {
                        "Pb": 0.01, "Cd": 0.005, "Hg": 0.001, "Cu": 1.0
                    }
                    for metal, value in metals.items():
                        try:
                            v = float(value)
                            if metal in THRESHOLDS and v > THRESHOLDS[metal]:
                                is_exceed = 1
                                exceed_items.append(metal)
                        except Exception:
                            pass
                    print('写入points表数据:', user_id, unique_filename, upload_time, city_val, lat, lon, is_exceed, ','.join(exceed_items))
                    cursor.execute(
                        """
                        INSERT INTO points (user_id, file_name, upload_time, city, latitude, longitude, is_exceed, exceed_items)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (user_id, unique_filename, upload_time, city_val, lat, lon, is_exceed, ','.join(exceed_items))
                    )
                    connection.commit()
                    cursor.close()
                    print('写入points表成功')
                except Exception as e:
                    print(f"写入points表失败: {e}")
                finally:
                    connection.close()
        else:
            flash("请上传文件或输入至少一个金属值", "danger")
        return redirect(url_for('upload_file'))
    return render_template('upload.html', amap_js_key=GAODE_JS_KEY)


# 路由：数据分析页
@app.route("/analyze")
def analyze():
    print('进入 analyze 路由')
    
    # 检查用户登录状态
    if "user" not in session:
        print('未登录，session["user"] 不存在，重定向到首页')
        return redirect(url_for("index"))

    username = session["user"]
    print('当前用户名:', username)

    # 获取用户 ID
    user_id = None
    try:
        connection = create_db_connection()
        if not connection:
            print('❌ 数据库连接失败')
            flash("数据库连接失败，请稍后重试", "error")
            return redirect(url_for("dashboard"))
            
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            print('用户查询结果:', user)
            
            if not user or not isinstance(user, dict) or 'id' not in user:
                print('用户不存在，返回 404')
                flash("用户不存在", "error")
                return redirect(url_for("index"))

            user_id = user.get("id")
            if not isinstance(user_id, (int, str)) or (isinstance(user_id, str) and not user_id.isdigit()):
                print('用户ID无效，返回 404')
                flash("用户ID无效", "error")
                return redirect(url_for("index"))
                
            user_id = int(user_id)
            print(f'用户ID: {user_id}')
            
        except Exception as e:
            print(f'❌ 用户查询错误: {e}')
            flash("用户查询失败", "error")
            return redirect(url_for("dashboard"))
        finally:
            cursor.close()
            connection.close()
            
    except Exception as e:
        print(f'❌ 数据库操作错误: {e}')
        flash("数据库操作失败", "error")
        return redirect(url_for("dashboard"))

    # 获取用户数据
    try:
        connection = create_db_connection()
        if not connection:
            print('❌ 数据库连接失败')
            flash("数据库连接失败，请稍后重试", "error")
            return redirect(url_for("dashboard"))
            
        cursor = connection.cursor(dictionary=True)
        try:
            # 安全地查询 points 表
            cursor.execute("""
                SELECT file_name, upload_time, city, latitude, longitude, is_exceed, exceed_items
                FROM points
                WHERE user_id = %s
                ORDER BY upload_time DESC
                LIMIT 1000
            """, (user_id,))
            points_rows = cursor.fetchall()
            print('points表数据行数:', len(points_rows))

            # 安全地处理地图数据
            map_data = []
            for row in points_rows:
                try:
                    lat = row.get("latitude")
                    lon = row.get("longitude")
                    
                    # 安全地转换经纬度
                    lat = float(lat) if lat is not None and str(lat).strip() != '' else None
                    lon = float(lon) if lon is not None and str(lon).strip() != '' else None
                    
                    # 安全地处理超标项目
                    exceed_items_str = row.get("exceed_items", "")
                    exceed_items = []
                    if exceed_items_str and isinstance(exceed_items_str, str):
                        exceed_items = [item.strip() for item in exceed_items_str.split(",") if item.strip()]
                    
                    map_data.append({
                        "latitude": lat,
                        "longitude": lon,
                        "city": str(row.get("city", "")).strip(),
                        "is_exceed": bool(row.get("is_exceed", 0)),
                        "exceed_items": exceed_items,
                        "file_name": str(row.get("file_name", "")).strip(),
                        "upload_time": str(row.get("upload_time", ""))
                    })
                except Exception as e:
                    print(f'处理地图数据行时出错: {e}')
                    continue
                    
            print('map_data 处理完成，共', len(map_data), '条记录')

            # 安全地统计金属种类
            pollution_counter = {}
            exceed_stats = {}
            for row in points_rows:
                try:
                    items = row.get("exceed_items")
                    if items and isinstance(items, str):
                        for item in items.split(","):
                            item = item.strip()
                            if item:
                                pollution_counter[item] = pollution_counter.get(item, 0) + 1
                                exceed_stats[item] = exceed_stats.get(item, 0) + 1
                except Exception as e:
                    print(f'统计金属种类时出错: {e}')
                    continue
                    
            pollution_stats = [{"name": k, "value": v} for k, v in pollution_counter.items()]
            print('metal_stats:', pollution_stats)
            print('exceed_stats:', exceed_stats)

            # 安全地查询上传文件列表
            print('准备查询 water_quality_data 表 user_id:', user_id)
            cursor.execute('''
                SELECT MIN(id) as id, file_name, MIN(upload_time) as upload_time
                FROM water_quality_data
                WHERE user_id = %s
                GROUP BY file_name
                ORDER BY upload_time DESC
            ''', (user_id,))
            user_data_rows = cursor.fetchall()
            print('water_quality_data表文件列表:', [row.get("file_name", "") for row in user_data_rows])
            
            user_data = []
            for row in user_data_rows:
                try:
                    if row.get("file_name"):
                        user_data.append({
                            "id": row.get("id"),
                            "file_name": str(row.get("file_name", "")).strip(),
                            "upload_time": str(row.get("upload_time", ""))
                        })
                except Exception as e:
                    print(f'处理用户数据行时出错: {e}')
                    continue
                    
            print('最终 user_data:', user_data)

            # 确保所有数据都是JSON可序列化的
            try:
                # 验证数据格式
                import json
                json.dumps(map_data)
                json.dumps(pollution_stats)
                json.dumps(exceed_stats)
                json.dumps(user_data)
                
                return render_template(
                    "analyze.html",
                    user_data=user_data,
                    map_data=map_data,
                    metal_stats=pollution_stats,
                    analysis_results=[],  # 如需详情可扩展
                    exceed_stats=exceed_stats,
                    amap_js_key=GAODE_JS_KEY
                )
            except Exception as e:
                print(f'数据序列化错误: {e}')
                # 使用安全的默认值
                return render_template(
                    "analyze.html",
                    user_data=[],
                    map_data=[],
                    metal_stats=[],
                    analysis_results=[],
                    exceed_stats={},
                    amap_js_key=GAODE_JS_KEY
                )
            
        except Exception as e:
            print(f'❌ 数据处理错误: {e}')
            flash("数据处理失败", "error")
            return redirect(url_for("dashboard"))
        finally:
            cursor.close()
            connection.close()
            
    except Exception as e:
        print(f'❌ 获取用户数据失败: {e}')
        flash("获取用户数据失败", "error")
        return redirect(url_for("dashboard"))



# 路由：预留接口页面（功能待定）
@app.route("/api_page")
def api_page():
    if "user" not in session:
        return redirect(url_for("index"))

    # 这里可以添加未来要实现的接口逻辑
    return render_template("api_page.html")


# 兼容旧链接：/temp 重定向到新设备页面 /device
@app.route("/temp")
def legacy_temp_redirect():
    return redirect(url_for("device_page"))


# API: 保存设备数据到数据库
@app.route("/api/save-device-data", methods=["POST"])
def api_save_device_data():
    if "user" not in session:
        return jsonify({"ok": False, "error": "未登录"}), 401
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"ok": False, "error": "无效的请求数据"}), 400
        
        # 提取数据
        device_data = data.get("data", {})
        latitude = data.get("latitude")
        longitude = data.get("longitude")
        city = data.get("city", "").strip()
        location_name = data.get("location_name", "设备检测点").strip()
        
        # 验证必填字段
        if latitude is None or longitude is None or not city:
            return jsonify({"ok": False, "error": "缺少必填字段：纬度、经度或城市"}), 400
        
        # 验证坐标范围
        if not (-90 <= latitude <= 90):
            return jsonify({"ok": False, "error": "纬度范围应在 -90 到 90 之间"}), 400
        if not (-180 <= longitude <= 180):
            return jsonify({"ok": False, "error": "经度范围应在 -180 到 180 之间"}), 400
        
        # 检查是否有超标数据
        exceed_items = []
        is_exceed = False
        
        # 定义阈值（与前端保持一致）
        thresholds = {
            "Pb": 0.01, "Cd": 0.005, "Hg": 0.001, "Cu": 1.0, "Cr": 0.05,
            "Ni": 0.07, "As": 0.01, "Mn": 0.1, "Fe": 0.3, "Zn": 1.0,
            "Se": 0.01, "Ba": 0.7, "Al": 0.2, "Ag": 0.05,
            "TDS": 1000, "Turbidity": 1.0
        }
        
        # pH 有范围阈值
        ph_value = device_data.get("pH")
        if ph_value is not None:
            try:
                ph_float = float(ph_value)
                if not (6.5 <= ph_float <= 8.5):
                    exceed_items.append("pH")
                    is_exceed = True
            except (ValueError, TypeError):
                pass
        
        # 检查其他参数
        for param, threshold in thresholds.items():
            value = device_data.get(param)
            if value is not None:
                try:
                    value_float = float(value)
                    if value_float > threshold:
                        exceed_items.append(param)
                        is_exceed = True
                except (ValueError, TypeError):
                    pass
        
        # 生成文件名（基于时间戳）
        import time
        timestamp = int(time.time())
        file_name = f"device_data_{timestamp}.json"
        
        # 获取用户ID
        user_id = None
        if 'user' in session:
            connection = create_db_connection()
            if connection:
                cursor = connection.cursor(dictionary=True)
                cursor.execute("SELECT id FROM users WHERE username = %s", (session["user"],))
                user = cursor.fetchone()
                cursor.close()
                connection.close()
                if user and isinstance(user, dict) and 'id' in user:
                    user_id = user['id']
        
        if not user_id:
            return jsonify({"ok": False, "error": "用户未登录或获取用户ID失败"}), 401

        # 插入数据库
        connection = create_db_connection()
        if not connection:
            return jsonify({"ok": False, "error": "数据库连接失败"}), 500
            
        try:
            cursor = connection.cursor()
            insert_query = """
            INSERT INTO analysis_results 
            (latitude, longitude, city, is_exceed, exceed_items, file_name, upload_time, user_id)
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s)
            """
            
            cursor.execute(insert_query, (
                latitude, longitude, city, is_exceed, 
                ','.join(exceed_items) if exceed_items else '', 
                file_name, user_id
            ))
            
            # 获取插入的记录ID
            record_id = cursor.lastrowid
            
            # 保存详细数据到文件（可选，或者也可以存储到数据库的另一个表）
            import json
            import os
            
            # 创建数据目录（如果不存在）
            data_dir = "uploaded_data"
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
            
            # 保存设备数据到JSON文件
            device_data_file = os.path.join(data_dir, file_name)
            with open(device_data_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "record_id": record_id,
                    "location": {
                        "latitude": latitude,
                        "longitude": longitude,
                        "city": city,
                        "location_name": location_name
                    },
                    "data": device_data,
                    "timestamp": timestamp,
                    "is_exceed": is_exceed,
                    "exceed_items": exceed_items
                }, f, ensure_ascii=False, indent=2)
            
            connection.commit()
            cursor.close()
            connection.close()
            
        except Exception as db_error:
            if connection:
                connection.rollback()
                connection.close()
            print(f"数据库操作错误: {db_error}")
            return jsonify({"ok": False, "error": f"数据库操作失败: {str(db_error)}"}), 500
        
        return jsonify({
            "ok": True, 
            "message": "数据保存成功",
            "record_id": record_id,
            "is_exceed": is_exceed,
            "exceed_items": exceed_items
        })
        
    except Exception as e:
        print(f"保存设备数据错误: {e}")
        return jsonify({"ok": False, "error": f"保存失败: {str(e)}"}), 500


# 设备管理页面
@app.route("/device")
def device_page():
    if "user" not in session:
        return redirect(url_for("index"))
    return render_template("device.html")

# 路由：退出登录
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("index"))


# 路由：查看数据详情
@app.route("/view_data/<int:data_id>")
def view_data(data_id):
    if "user" not in session:
        return redirect(url_for("index"))

    connection = create_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM water_quality_data WHERE id = %s", (data_id,))
        data_entry = cursor.fetchone()
        cursor.close()
        connection.close()

        if data_entry and isinstance(data_entry, dict):
            try:
                # 解析 data 字段
                data_str = data_entry.get('data')
                if not data_str or data_str in ('', 'None', None):
                    data = {}
                elif isinstance(data_str, dict):
                    data = data_str
                elif isinstance(data_str, str):
                    data = json.loads(data_str)
                else:
                    data = {}
                # 解析 metals 字段
                metals_str = data_entry.get('metals')
                if not metals_str or metals_str in ('', 'None', None):
                    metals = {}
                elif isinstance(metals_str, dict):
                    metals = metals_str
                elif isinstance(metals_str, str):
                    metals = json.loads(metals_str)
                else:
                    metals = {}
                # 分析该文件
                file_name = data_entry.get('file_name')
                analysis = []
                if isinstance(file_name, str) and file_name.lower().endswith('.csv'):
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
                    # 确保文件路径是绝对路径
                    if not os.path.isabs(filepath):
                        filepath = os.path.abspath(filepath)
                    
                    # 检查文件是否存在
                    if os.path.exists(filepath):
                        analysis = analyze_csv_file(filepath)
                # 传递更多信息到模板
                return render_template(
                    "data_detail.html",
                    data={
                        "file_name": file_name,
                        "upload_time": data_entry.get("upload_time"),
                        "analysis": analysis
                    }
                )
            except Exception as e:
                return f"数据解析失败: {str(e)}"

    return "数据不存在"

# 高德 Key 配置：允许只配置一个 key（GAODE_WEB_KEY 或 GAODE_JS_KEY）即可同时用于两类场景
_DEFAULT_GAODE_KEY = '131c82664ed5c484aedad8082e2af203'
GAODE_KEY = os.environ.get('GAODE_WEB_KEY') or os.environ.get('GAODE_JS_KEY') or _DEFAULT_GAODE_KEY
GAODE_JS_KEY = os.environ.get('GAODE_JS_KEY') or os.environ.get('GAODE_WEB_KEY') or _DEFAULT_GAODE_KEY

@app.route('/api/regeo', methods=['POST'])
def api_regeo():
    data = request.get_json(silent=True) or {}
    lng = data.get('lng')
    lat = data.get('lat')
    if lng is None or lat is None:
        return jsonify({'error': '缺少经纬度'}), 400
    try:
        lng = float(lng)
        lat = float(lat)
    except (TypeError, ValueError):
        return jsonify({'error': '经纬度格式错误'}), 400

    if not GAODE_KEY:
        return jsonify({'error': '高德Web服务Key未配置'}), 500

    url = 'https://restapi.amap.com/v3/geocode/regeo'
    params = {
        'key': GAODE_KEY,
        'location': f'{lng},{lat}',
        'output': 'json'
    }

    try:
        resp = requests.get(url, params=params, timeout=8)
        resp.raise_for_status()
        result = resp.json()
    except requests.RequestException as e:
        print(f"/api/regeo 请求高德失败: {e}")
        return jsonify({'error': '地理编码服务不可用'}), 502
    except ValueError as e:
        print(f"/api/regeo 解析高德响应失败: {e}")
        return jsonify({'error': '地理编码响应解析失败'}), 502

    if result.get('status') == '1' and isinstance(result.get('regeocode'), dict):
        address = result['regeocode'].get('addressComponent', {})
        province = address.get('province', '') or ''
        city = address.get('city', '') or address.get('district', '') or ''
        return jsonify({'province': province, 'city': city})

    info = result.get('info', '')
    print(f"/api/regeo 高德返回失败: {info}, 响应: {result}")
    return jsonify({'error': '逆地理编码失败', 'info': info}), 502


# 路由：AI分析页面
@app.route("/ai_analysis")
def ai_analysis():
    if "user" not in session:
        return redirect(url_for("index"))
    
    return render_template("ai_analysis.html")


# API接口：AI水质分析
@app.route('/api/ai_analysis', methods=['POST'])
def ai_water_analysis():
    try:
        data = request.get_json()
        
        # 验证必要的数据字段
        required_fields = ['tds', 'temperature', 'ph', 'turbidity']
        for field in required_fields:
            if field not in data or data[field] is None:
                return jsonify({'error': f'缺少必要字段: {field}'}), 400
        
        # 调用AI分析函数
        analysis_result = analyze_water_quality_with_ai(data)
        
        return jsonify(analysis_result)
        
    except Exception as e:
        print(f"AI分析错误: {str(e)}")
        return jsonify({'error': 'AI分析失败', 'details': str(e)}), 500




def analyze_water_quality_with_ai(data):
    """
    使用百度千帆AI分析水质数据
    """
    
    # 构建分析提示词
    prompt = build_analysis_prompt(data)
    
    # 调用百度千帆API
    try:
        print("正在调用百度千帆AI进行分析...")
        analysis_result = call_qianfan_api(prompt)
        if analysis_result:
            print("✅ 使用百度千帆大模型分析结果")
            return analysis_result
        else:
            print("❌ 百度千帆API调用失败")
    except Exception as e:
        print(f"❌ 百度千帆API调用异常: {str(e)}")
    
    # 如果AI API调用失败，回退到模拟分析
    print("⚠️ 回退到模拟分析")
    analysis_result = simulate_ai_analysis(data)
    print("📊 使用模拟分析结果")
    return analysis_result








def call_qianfan_api(prompt):
    """
    调用百度千帆·大模型平台API（新版v2接口）
    只需要 API Key，无需 Secret Key
    """
    import requests
    import json
    import time

    API_KEY = "bce-v3/ALTAK-gfsX1fgtbC7Jf5x6XFym8/d1e260d87997d8182f2fd63338ab0a327c7db9b7"

    api_url = "https://qianfan.baidubce.com/v2/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }

    data = {
        # ✅ 改成免费可用模型
        "model": "deepseek-v3.1-250821",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "top_p": 0.8,
        "penalty_score": 1.0,
        "max_output_tokens": 2000,
    }

    # 简化的重试机制
    max_retries = 2  # 减少到2次重试
    retry_delay = 3  # 减少到3秒等待
    
    for attempt in range(max_retries):
        try:
            print(f"API调用尝试 {attempt + 1}/{max_retries}")
            response = requests.post(api_url, headers=headers, json=data)
            print("状态码:", response.status_code)
            result = response.json()

            # 检查是否是速率限制错误
            if response.status_code == 429:
                if attempt < max_retries - 1:
                    print(f"遇到速率限制，等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
                    continue
                else:
                    print("达到最大重试次数，API调用失败")
                    return None
            
            # 检查其他错误
            if response.status_code != 200:
                print(f"API调用失败，状态码: {response.status_code}")
                if attempt < max_retries - 1:
                    print(f"等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
                    continue
                else:
                    return None

            # 解析成功响应
            if "result" in result:
                ai_response = result["result"]
                print(f"✅ 获得真实大模型分析结果")
                return parse_ai_response(ai_response)
            elif "choices" in result and result["choices"]:
                ai_response = result["choices"][0]["message"]["content"]
                print(f"✅ 获得真实大模型分析结果")
                return parse_ai_response(ai_response)
            else:
                print("百度千帆API调用失败:", result)
                if attempt < max_retries - 1:
                    print(f"等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
                    continue
                else:
                    return None
                
        except Exception as e:
            print(f"调用百度千帆API时发生错误: {e}")
            if attempt < max_retries - 1:
                print(f"等待 {retry_delay} 秒后重试...")
                time.sleep(retry_delay)
            else:
                return None
    
    return None


def parse_ai_response(ai_response):
    """
    解析AI返回的响应，提取结构化数据
    """
    print(f"开始解析AI响应: {ai_response[:200]}...")
    
    try:
        # 尝试直接解析JSON
        if ai_response.strip().startswith('{'):
            parsed_result = json.loads(ai_response)
            print(f"JSON解析成功: {parsed_result}")
            return parsed_result
        
        # 如果不是JSON格式，尝试提取关键信息
        import re
        
        # 提取风险等级
        risk_level_match = re.search(r'风险等级[：:]\s*([低中高]风险)', ai_response)
        risk_level = risk_level_match.group(1) if risk_level_match else "未知"
        
        # 提取风险评估
        risk_assessment_match = re.search(r'风险评估[：:](.*?)(?=数据分析|改善建议|$)', ai_response, re.DOTALL)
        risk_assessment = risk_assessment_match.group(1).strip() if risk_assessment_match else "AI分析结果"
        
        # 提取数据分析
        data_analysis_match = re.search(r'数据分析[：:](.*?)(?=改善建议|$)', ai_response, re.DOTALL)
        data_analysis = data_analysis_match.group(1).strip() if data_analysis_match else "数据分析结果"
        
        # 提取建议
        recommendations_match = re.search(r'改善建议[：:](.*?)$', ai_response, re.DOTALL)
        recommendations_text = recommendations_match.group(1).strip() if recommendations_match else "建议咨询专业机构"
        
        # 将建议文本转换为列表
        recommendations = []
        if recommendations_text:
            # 按行分割建议
            lines = recommendations_text.split('\n')
            for line in lines:
                line = line.strip()
                if line and (line.startswith('-') or line.startswith('•') or line.startswith('1.') or line.startswith('2.') or line.startswith('3.')):
                    # 移除列表标记
                    clean_line = re.sub(r'^[-•\d\.\s]+', '', line)
                    if clean_line:
                        recommendations.append(clean_line)
        
        if not recommendations:
            recommendations = ["建议咨询专业水质检测机构"]
        
        parsed_result = {
            'risk_level': risk_level,
            'risk_assessment': risk_assessment,
            'data_analysis': data_analysis,
            'recommendations': recommendations,
            'ai_source': '百度千帆',
            'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        print(f"正则解析结果: {parsed_result}")
        return parsed_result
        
    except Exception as e:
        print(f"解析AI响应时发生错误: {str(e)}")
        return None


def build_analysis_prompt(data):
    """构建AI分析提示词"""
    
    prompt = f"""
    你是一位专业的水质分析专家，请分析以下水质检测数据：

    基础水质参数：
    - TDS (总溶解固体): {data.get('tds', 'N/A')} ppm
    - 温度: {data.get('temperature', 'N/A')} °C  
    - pH值: {data.get('ph', 'N/A')}
    - 浊度: {data.get('turbidity', 'N/A')} NTU

    重金属离子浓度：
    - 铅 (Pb2+): {data.get('pb', 0)} mg/L
    - 镉 (Cd2+): {data.get('cd', 0)} mg/L
    - 汞 (Hg): {data.get('hg', 0)} mg/L
    - 六价铬 (Cr6+): {data.get('cr6', 0)} mg/L
    - 铜 (Cu2+): {data.get('cu', 0)} mg/L
    - 镍 (Ni2+): {data.get('ni', 0)} mg/L

    请按照以下格式提供分析结果：

    风险等级: [低风险/中风险/高风险]

    风险评估: [详细说明当前水质的安全状况，指出主要风险因素]

    数据分析: [分析各项参数的健康状况，包括是否超标及原因]

    改善建议: 
    - [具体建议1]
    - [具体建议2] 
    - [具体建议3]
    - [更多建议...]

    请确保建议实用且具有可操作性。
    """
    
    return prompt


def simulate_ai_analysis(data):
    """模拟AI分析结果（实际应用中替换为真实的AI API调用）"""
    
    # 计算风险等级
    risk_score = 0
    risk_factors = []
    
    # TDS评估
    tds = data.get('tds', 0)
    if tds > 1000:
        risk_score += 3
        risk_factors.append(f"TDS值{tds}ppm过高，超过1000ppm标准")
    elif tds > 500:
        risk_score += 1
        risk_factors.append(f"TDS值{tds}ppm偏高")
    
    # pH评估
    ph = data.get('ph', 7)
    if ph < 6.5 or ph > 8.5:
        risk_score += 2
        risk_factors.append(f"pH值{ph}超出正常范围(6.5-8.5)")
    
    # 浊度评估
    turbidity = data.get('turbidity', 0)
    if turbidity > 1.0:
        risk_score += 2
        risk_factors.append(f"浊度{turbidity}NTU过高，超过1.0NTU标准")
    
    # 重金属评估
    heavy_metals = {
        'pb': {'value': data.get('pb', 0), 'threshold': 0.01, 'name': '铅'},
        'cd': {'value': data.get('cd', 0), 'threshold': 0.003, 'name': '镉'},
        'hg': {'value': data.get('hg', 0), 'threshold': 0.001, 'name': '汞'},
        'cr6': {'value': data.get('cr6', 0), 'threshold': 0.05, 'name': '六价铬'},
        'cu': {'value': data.get('cu', 0), 'threshold': 1.0, 'name': '铜'},
        'ni': {'value': data.get('ni', 0), 'threshold': 0.02, 'name': '镍'}
    }
    
    for metal, info in heavy_metals.items():
        if info['value'] > info['threshold']:
            risk_score += 4
            risk_factors.append(f"{info['name']}浓度{info['value']}mg/L严重超标，超过{info['threshold']}mg/L标准")
        elif info['value'] > info['threshold'] * 0.5:
            risk_score += 2
            risk_factors.append(f"{info['name']}浓度{info['value']}mg/L接近超标")
    
    # 确定风险等级
    if risk_score >= 8:
        risk_level = "高风险"
    elif risk_score >= 4:
        risk_level = "中风险"
    else:
        risk_level = "低风险"
    
    # 生成风险评估说明
    risk_assessment = f"基于当前水质检测数据，评估风险等级为{risk_level}。"
    if risk_factors:
        risk_assessment += f"主要风险因素包括：{'; '.join(risk_factors)}。"
    else:
        risk_assessment += "各项指标均在正常范围内。"
    
    # 生成数据分析
    data_analysis = f"""
    水质数据分析结果：
    
    基础参数分析：
    - TDS值{tds}ppm {'正常' if tds <= 500 else '偏高' if tds <= 1000 else '过高'}
    - pH值{ph} {'正常' if 6.5 <= ph <= 8.5 else '异常'}
    - 温度{data.get('temperature', 0)}°C {'正常' if 15 <= data.get('temperature', 0) <= 30 else '异常'}
    - 浊度{turbidity}NTU {'正常' if turbidity <= 1.0 else '过高'}
    
    重金属污染分析：
    """
    
    for metal, info in heavy_metals.items():
        status = "正常" if info['value'] <= info['threshold'] else "超标"
        data_analysis += f"- {info['name']}: {info['value']}mg/L ({status})\n"
    
    # 生成改善建议
    recommendations = []
    
    if tds > 1000:
        recommendations.append("建议安装反渗透净水设备降低TDS值")
    
    if ph < 6.5 or ph > 8.5:
        recommendations.append("调节pH值至6.5-8.5范围内，可使用pH调节剂")
    
    if turbidity > 1.0:
        recommendations.append("加强过滤处理，降低浊度至1.0NTU以下")
    
    if any(info['value'] > info['threshold'] for info in heavy_metals.values()):
        recommendations.append("重金属超标严重，建议立即停止饮用并联系专业水处理公司")
        recommendations.append("安装重金属过滤设备，如活性炭过滤器或离子交换树脂")
    
    if not recommendations:
        recommendations.append("水质状况良好，建议定期监测保持现状")
        recommendations.append("建议每季度进行一次全面水质检测")
    
    recommendations.append("建议咨询专业水质检测机构进行详细分析")
    
    return {
        'risk_level': risk_level,
        'risk_assessment': risk_assessment,
        'data_analysis': data_analysis.strip(),
        'recommendations': recommendations,
        'risk_score': risk_score,
        'ai_source': '模拟分析',
        'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }


if __name__ == "__main__":
    init_db()  # 初始化数据库
    print("Flask应用启动中...")
    print("访问地址: http://127.0.0.1:5000")
    print("数据分析页面: http://127.0.0.1:5000/analyze")
    app.run(debug=True, host='127.0.0.1', port=5000)