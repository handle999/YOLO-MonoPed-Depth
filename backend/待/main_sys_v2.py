# backend/main_sys_v2.py
import math
import cv2
import numpy as np
import requests
import pandas as pd
import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS  # 引入跨域组件
from pydantic import ValidationError
from shapely.geometry import Point, LineString
from pyproj import Transformer

# 引入您的底层算法库
from src.detector import PersonDetector
from backend.src.geolocalizertem import GeoLocalizer
# 引入全新 Schema
from api.schemas_sys import (
    LocalRequest, LocalResponse, LocalObjectOut,
    DetectRequest, DetectResponse, DetectObjectOut, BndBox
)

app = Flask(__name__)
# [必须新增] 允许前端跨域访问 8002 端口
CORS(app, resources={r"/*": {"origins": "*"}})

# 为指挥系统专门初始化一个全局的检测器 (使用最优模型)
detector = PersonDetector('./models/Detect/yolo26l.pt', './models/Pose/yolo26l-pose.pt')

# 新增： 加载 CSV 设备配置
CSV_FILE_PATH = "tb_device_202603130925.csv"
try:
    DEVICE_DF = pd.read_csv(CSV_FILE_PATH, encoding='gbk')
    print(f"[+] 成功加载设备配置表，共 {len(DEVICE_DF)} 条记录。")
except Exception as e:
    print(f"[-] 读取 CSV 文件失败，请检查文件路径！错误: {e}")
    DEVICE_DF = pd.DataFrame()


# ==========================================
# 辅助函数区
# ==========================================
def load_image(image_path_or_url: str):
    """
    统一的图片加载函数
    支持 HTTP URL 下载，也支持直接读取本地绝对路径（完美兼容中文路径）
    """
    try:
        # 如果传入的是网络链接
        if str(image_path_or_url).startswith(('http://', 'https://')):
            resp = requests.get(image_path_or_url, timeout=10)
            resp.raise_for_status()
            image_array = np.frombuffer(resp.content, np.uint8)
            img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        else:
            # 否则视作本地绝对路径
            if not os.path.exists(image_path_or_url):
                raise ValueError(f"本地图片文件不存在: {image_path_or_url}")
            
            # 使用 np.fromfile 读取本地文件，完美兼容含有中文的绝对路径
            file_bytes = np.fromfile(image_path_or_url, dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        if img is None:
            raise ValueError("未能成功解码图片文件")
        return img
    except Exception as e:
        raise ValueError(f"图片加载异常: {str(e)}")

def parse_line_to_fence_coords(line_str):
    """解析 CSV 中的 line 字段为经纬度坐标列表"""
    if pd.isna(line_str) or not str(line_str).strip():
        return None
        
    fence_coords = []
    line_str = str(line_str).strip()
    points = line_str.split(';')
    for pt in points:
        if pt.strip():
            try:
                lng_str, lat_str = pt.split(',')
                # 统一转换为 (lat, lon) 格式
                fence_coords.append((float(lat_str.strip()), float(lng_str.strip())))
            except ValueError:
                pass
    return fence_coords if fence_coords else None

def get_distance_professional(person_lat, person_lon, fence_coords):
    """计算人员经纬度到围栏轨迹的最短距离 (单位: 米)"""
    if not fence_coords or len(fence_coords) < 2:
        return None

    p_lat = float(person_lat)
    p_lon = float(person_lon)
    
    # 将经纬度转为墨卡托投影计算真实距离 (米)
    transformer = Transformer.from_crs("epsg:4326", "epsg:3857", always_xy=True)
    px, py = transformer.transform(p_lon, p_lat)
    person_pt = Point(px, py)

    # 转换围栏坐标
    fence_pts = [transformer.transform(float(lon), float(lat)) for lat, lon in fence_coords]
    fence_line = LineString(fence_pts)
    
    return fence_line.distance(person_pt)


@app.route('/imageUrl/<filename>')
def serve_image(filename):
    """
    通过URL访问本地图片的路由函数
    示例：http://127.0.0.1:8111/imageUrl/capture_002.jpg
    """
    # 路径存在性校验
    if not os.path.exists(IMAGE_FOLDER):
        return jsonify({"code": 404, "msg": f"错误：图片文件夹 {IMAGE_FOLDER} 不存在"}), 404
    
    # 构建完整文件路径
    file_path = os.path.join(IMAGE_FOLDER, filename)
    
    # 文件有效性校验
    if not os.path.isfile(file_path):
        return jsonify({"code": 404, "msg": f"错误：文件 {filename} 不存在"}), 404
    
    # 返回图片文件
    return send_from_directory(IMAGE_FOLDER, filename)


# ==========================================
# 接口一：人员定位 (指挥系统传框，本地算坐标)
# ==========================================
@app.route("/xjzhdd/alarmEvent/pull/local", methods=["POST"])
def pull_local():
    try:
        req_data = request.get_json()
        req = LocalRequest(**req_data)
    except ValidationError as e:
        return jsonify({"code": 400, "msg": f"参数校验失败: {str(e.errors())}"}), 400

    try:
        # 1. 下载图片以获取真实宽高 (用于反归一化)
        image = download_image(req.imageUrl)
        img_h, img_w = image.shape[:2]

        # 2. 转换相机姿态 (文档说是弧度，底层算法需要角度)
        pitch_deg = math.degrees(req.pitch)
        yaw_deg = math.degrees(req.yaw)
        roll_deg = math.degrees(req.roll)

        # 3. 构造底层 Localizer 需要的配置格式
        cam_config = {
            'device_id': "zhdd_camera",
            'gps': {'lat': req.latitude, 'lng': req.longitude, 'alt': 0.0},
            'height': req.height,
            'pose': {'pitch': pitch_deg, 'yaw': yaw_deg, 'roll': roll_deg},
            'hardware': {'focal_length_mm': req.f, 'sensor_width_mm': 36.0}, # 假定传感器宽度
            'resolution': {'width': img_w, 'height': img_h},
            'distortion': None 
        }
        localizer = GeoLocalizer(cam_config)

        # 4. 遍历目标框算坐标
        out_objects = []
        for i, obj in enumerate(req.objectList):
            b = obj.bndbox
            # [核心] 反归一化：小数 -> 真实像素坐标
            x1 = b.x * img_w
            y1 = b.y * img_h
            x2 = (b.x + b.width) * img_w
            y2 = (b.y + b.height) * img_h
            bbox_px = [x1, y1, x2, y2]

            # 假设都按平地计算定位
            loc_res = localizer.pixel_to_location_flat(i, conf=1.0, bbox=bbox_px, image_shape=(img_h, img_w))
            
            if loc_res:
                out_objects.append(LocalObjectOut(
                    objectCode=obj.objectCode,
                    objectCategory=obj.objectCategory,
                    # 按照文档示例，格式化为保留 8 位小数的字符串
                    longitude=f"{loc_res['lng']:.8f}",
                    latitude=f"{loc_res['lat']:.8f}"
                ))

        res = LocalResponse(imageUrl=req.imageUrl, currentTime=req.currentTime, objectList=out_objects)
        return jsonify(res.model_dump()), 200

    except Exception as e:
        return jsonify({"code": 500, "msg": f"内部计算错误: {str(e)}"}), 200 # 业务约定可能出错也回 200 伴随 code=500



# ---------------------------------------------------------
# 接口二：人员检测 (指挥系统传图，本地算框)
# ---------------------------------------------------------
@app.route("/xjzhdd/alarmEvent/pull/detection", methods=["POST"])
def pull_detection():
    try:
        req_data = request.get_json()
        req = DetectRequest(**req_data)
    except ValidationError as e:
        return jsonify({"code": 400, "msg": f"参数校验失败: {str(e.errors())}"}), 400

    try:
        # 1. 下载图片并获取尺寸
        image = download_image(req.imageUrl)
        img_h, img_w = image.shape[:2]

        # 2. 调用 YOLO 模型检测
        detections = detector.detect(image, use_pose=False)
        
        # 3. 构造出参
        out_objects = []
        for i, det in enumerate(detections):
            bbox_px = det['bbox'] # [x1, y1, x2, y2]
            
            # [核心] 归一化：真实像素坐标 -> 0~1 的小数
            x_norm = bbox_px[0] / img_w
            y_norm = bbox_px[1] / img_h
            width_norm = (bbox_px[2] - bbox_px[0]) / img_w
            height_norm = (bbox_px[3] - bbox_px[1]) / img_h
            
            bndbox = BndBox(x=x_norm, y=y_norm, width=width_norm, height=height_norm)
            
            # 程序自增编号
            object_code = f"{(i+1):013d}" 
            
            out_objects.append(DetectObjectOut(
                objectCode=object_code,
                objectCategory="1", # 默认识别出的是人
                bndbox=bndbox
            ))

        res = DetectResponse(currentTime=req.currentTime, imageUrl=req.imageUrl, objectList=out_objects)
        return jsonify(res.model_dump()), 200

    except Exception as e:
        return jsonify({"code": 500, "msg": f"检测异常: {str(e)}"}), 200



# ==========================================
# 接口三：人员定位并计算围栏距离 (基于 IP 查表)
# ==========================================
@app.route("/xjzhdd/alarmEvent/pull/disbyip", methods=["POST"])
def pull_fence_distance():
    try:
        req_data = request.get_json()
        
        # 1. 提取入参
        image_url = req_data.get("imageUrl")
        ip = req_data.get("ip")
        bnd = req_data.get("bnd")

        if not all([image_url, ip, bnd]):
            return jsonify({"code": 400, "msg": "缺失必填参数 (imageUrl, ip, bnd)"}), 400

        # 2. 查询 CSV 获取相机参数
        if DEVICE_DF.empty:
            return jsonify({"code": 500, "msg": "系统 CSV 设备表未加载"}), 500
            
        device_row = DEVICE_DF[DEVICE_DF['dev_addr'] == ip]
        if device_row.empty:
            return jsonify({"code": 404, "msg": f"未在配置表中找到设备 IP: {ip}"}), 404
            
        device_data = device_row.iloc[0]
        dev_id = str(device_data.get('dev_id', 'unknown'))
        lat = float(device_data['latitude'])
        lng = float(device_data['longitude'])
        elevation = float(device_data['elevation'])
        pitch_deg = float(device_data['pitch'])      
        direction_deg = float(device_data['direction']) 
        fence_coords = parse_line_to_fence_coords(device_data.get('line'))

        # 3. 下载/加载图片以获取真实宽高
        image = load_image(image_url)
        img_h, img_w = image.shape[:2]

        # 4. 构造底层 Localizer 需要的配置格式
        cam_config = {
            'device_id': dev_id,
            'gps': {'lat': lat, 'lng': lng, 'alt': elevation},
            'height': elevation,
            'pose': {'pitch': pitch_deg, 'yaw': direction_deg, 'roll': 0.0},
            'hardware': {'focal_length_mm': 6.0, 'sensor_width_mm': 5.37},
            'resolution': {'width': img_w, 'height': img_h},
            'distortion': [-0.1, 0.05, 0, 0, 0] 
        }
        localizer = GeoLocalizer(cam_config)

        # 5. 反归一化目标框：小数 -> 真实像素坐标
        x1 = bnd['x'] * img_w
        y1 = bnd['y'] * img_h
        x2 = (bnd['x'] + bnd['width']) * img_w
        y2 = (bnd['y'] + bnd['height']) * img_h
        bbox_px = [x1, y1, x2, y2]

        # 6. 计算人员经纬度
        loc_res = localizer.pixel_to_location_flat(0, conf=1.0, bbox=bbox_px, image_shape=(img_h, img_w))

        if not loc_res:
            return jsonify({"code": 404, "msg": "无法计算出目标的有效地理坐标"}), 404

        person_lat = loc_res['lat']
        person_lng = loc_res['lng']

        # 7. 计算到围栏的距离
        distance_to_fence = None
        if fence_coords:
            dist = get_distance_professional(person_lat, person_lng, fence_coords)
            if dist is not None:
                distance_to_fence = round(dist, 2)

        # 8. 构造出参返回
        result_data = {
            "dev_id": dev_id,
            "person_lat": person_lat,
            "person_lng": person_lng,
            "distance_to_fence": distance_to_fence
            #"message": "计算成功" if distance_to_fence is not None else "人员位置已计算，但围栏数据缺失或无效"
        }

        return jsonify({"code": 200, "data": result_data}), 200

    except Exception as e:
        return jsonify({"code": 500, "msg": f"服务器内部错误: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8111, debug=True)