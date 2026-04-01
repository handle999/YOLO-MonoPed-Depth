# backend/main_sys.py
import math
import cv2
import numpy as np
import requests
import pandas as pd
import os
import base64
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS  # 引入跨域组件
from pydantic import ValidationError
from shapely.geometry import Point, LineString
from pyproj import Transformer

# 引入您的底层算法库
from src.detector import PersonDetector
from src.geolocalizer import GeoLocalizer
# 引入全新 Schema
from api.schemas_sys import (
    LocalRequest, LocalResponse, LocalObjectOut,
    DetectRequest, DetectResponse, DetectObjectOut, BndBox
)

app = Flask(__name__)
# 允许前端跨域访问
CORS(app, resources={r"/*": {"origins": "*"}})

# ==========================================
# 全局配置区
# ==========================================
# 1. 静态图片存储路径（用于 /imageUrl 接口）
IMAGE_FOLDER = 'D:/BIT_CV/Location/capture_pic/captures/10米'  

# 2. 为指挥系统专门初始化全局检测器 (使用最优模型)
detector = PersonDetector('./models/Detect/yolo26l.pt', './models/Pose/yolo26l-pose.pt')

# 3. 加载 CSV 设备配置
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
def decode_base64_image(base64_string):
    """将 base64 字符串解码为 cv2 图像矩阵"""
    try:
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        
        img_data = base64.b64decode(base64_string)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise ValueError("未能成功解码 Base64 图片")
        return img
    except Exception as e:
        raise ValueError(f"Base64 图片解析异常: {str(e)}")

def load_image(image_data=None, image_path_or_url=None):
    """
    统一的图片加载函数 (主要供接口一和接口二使用)
    优先级：1. Base64 (image_data)  2. HTTP URL  3. 本地绝对路径
    """
    try:
        if image_data:
            return decode_base64_image(image_data)
            
        if not image_path_or_url:
            raise ValueError("未提供图片数据 (imageData) 或图片路径 (imageUrl)")

        if str(image_path_or_url).startswith(('http://', 'https://')):
            resp = requests.get(image_path_or_url, timeout=10)
            resp.raise_for_status()
            image_array = np.frombuffer(resp.content, np.uint8)
            img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        else:
            if not os.path.exists(image_path_or_url):
                raise ValueError(f"本地图片文件不存在: {image_path_or_url}")
            
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


# ==========================================
# 接口零：本地图片代理服务
# ==========================================
@app.route('/imageUrl/<filename>')
def serve_image(filename):
    if not os.path.exists(IMAGE_FOLDER):
        return jsonify({"code": 404, "msg": f"错误：图片文件夹 {IMAGE_FOLDER} 不存在"}), 404
    
    file_path = os.path.join(IMAGE_FOLDER, filename)
    if not os.path.isfile(file_path):
        return jsonify({"code": 404, "msg": f"错误：文件 {filename} 不存在"}), 404
    
    return send_from_directory(IMAGE_FOLDER, filename)


# ==========================================
# 接口一：人员定位 (指挥系统传框，本地算坐标)
# ==========================================
@app.route("/xjzhdd/alarmEvent/pull/local", methods=["POST"])
def pull_local():
    try:
        req_data = request.get_json()
        image_data = req_data.pop('imageData', None) 
        req = LocalRequest(**req_data)
    except ValidationError as e:
        return jsonify({"code": 400, "msg": f"参数校验失败: {str(e.errors())}"}), 400

    try:
        image = load_image(image_data=image_data, image_path_or_url=req.imageUrl)
        img_h, img_w = image.shape[:2]

        pitch_deg = math.degrees(req.pitch)
        yaw_deg = math.degrees(req.yaw)
        roll_deg = math.degrees(req.roll)

        cam_config = {
            'device_id': "zhdd_camera",
            'gps': {'lat': req.latitude, 'lng': req.longitude, 'alt': 0.0},
            'height': req.height,
            'pose': {'pitch': pitch_deg, 'yaw': yaw_deg, 'roll': roll_deg},
            'hardware': {'focal_length_mm': req.f, 'sensor_width_mm': 36.0}, 
            'resolution': {'width': img_w, 'height': img_h},
            'distortion': None 
        }
        localizer = GeoLocalizer(cam_config)

        out_objects = []
        for i, obj in enumerate(req.objectList):
            b = obj.bndbox
            x1 = b.x * img_w
            y1 = b.y * img_h
            x2 = (b.x + b.width) * img_w
            y2 = (b.y + b.height) * img_h
            bbox_px = [x1, y1, x2, y2]

            loc_res = localizer.pixel_to_location_flat(i, conf=1.0, bbox=bbox_px, image_shape=(img_h, img_w))
            
            if loc_res:
                out_objects.append(LocalObjectOut(
                    objectCode=obj.objectCode,
                    objectCategory=obj.objectCategory,
                    longitude=f"{loc_res['lng']:.8f}",
                    latitude=f"{loc_res['lat']:.8f}"
                ))

        res = LocalResponse(imageUrl=req.imageUrl, currentTime=req.currentTime, objectList=out_objects)
        return jsonify(res.model_dump()), 200

    except Exception as e:
        return jsonify({"code": 500, "msg": f"内部计算错误: {str(e)}"}), 200 


# ==========================================
# 接口二：人员检测 (指挥系统传图，本地算框)
# ==========================================
@app.route("/xjzhdd/alarmEvent/pull/detection", methods=["POST"])
def pull_detection():
    try:
        req_data = request.get_json()
        image_data = req_data.pop('imageData', None)
        req = DetectRequest(**req_data)
    except ValidationError as e:
        return jsonify({"code": 400, "msg": f"参数校验失败: {str(e.errors())}"}), 400

    try:
        image = load_image(image_data=image_data, image_path_or_url=req.imageUrl)
        img_h, img_w = image.shape[:2]

        detections = detector.detect(image, use_pose=False)
        
        out_objects = []
        for i, det in enumerate(detections):
            bbox_px = det['bbox'] 
            
            x_norm = bbox_px[0] / img_w
            y_norm = bbox_px[1] / img_h
            width_norm = (bbox_px[2] - bbox_px[0]) / img_w
            height_norm = (bbox_px[3] - bbox_px[1]) / img_h
            
            bndbox = BndBox(x=x_norm, y=y_norm, width=width_norm, height=height_norm)
            object_code = f"{(i+1):013d}" 
            
            out_objects.append(DetectObjectOut(
                objectCode=object_code,
                objectCategory="1",
                bndbox=bndbox
            ))

        res = DetectResponse(currentTime=req.currentTime, imageUrl=req.imageUrl, objectList=out_objects)
        return jsonify(res.model_dump()), 200

    except Exception as e:
        return jsonify({"code": 500, "msg": f"检测异常: {str(e)}"}), 200


# ==========================================
# 接口三：人员定位并计算围栏距离 (基于 IP 查表)
# ==========================================
@app.route("/xjzhdd/alarmEvent/pull/fence_distance", methods=["POST"])
def pull_fence_distance():
    try:
        req_data = request.get_json()
        
        image_data = req_data.get("imageData")
        ip = req_data.get("ip")
        bnd = req_data.get("bnd")
        #print(bnd)
        # 1. 严格校验参数
        if not ip or not bnd:
            return jsonify({"code": 400, "msg": "缺失必填参数 (ip, bnd)"}), 400
        if not image_data:
            return jsonify({"code": 400, "msg": "必须提供 imageData(Base64格式图片数据)"}), 400

        # 2. 查询设备信息
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

        
        image = decode_base64_image(image_data)
        img_h, img_w = image.shape[:2]

        # 2. 转换相机姿态 (文档说是弧度，底层算法需要角度)
        pitch = math.degrees(pitch_deg)
        yaw_deg = math.degrees(direction_deg)
        

        # 4. 构造相机参数
        cam_config = {
            'device_id': dev_id,
            'gps': {'lat': lat, 'lng': lng, 'alt': 0.0},
            'height': elevation,
            'pose': {'pitch': pitch, 'yaw': yaw_deg, 'roll': 0.0},
            'hardware': {'focal_length_mm': 6.0, 'sensor_width_mm': 36.0},
            'resolution': {'width': img_w, 'height': img_h},
            'distortion': None
        }
        localizer = GeoLocalizer(cam_config)

        # 5. 反归一化
        x1 = bnd['x'] * img_w
        y1 = bnd['y'] * img_h
        x2 = (bnd['x'] + bnd['width']) * img_w
        y2 = (bnd['y'] + bnd['height']) * img_h
        bbox_px = [x1, y1, x2, y2]

        # 6. 计算位置
        loc_res = localizer.pixel_to_location_flat(0, conf=1.0, bbox=bbox_px, image_shape=(img_h, img_w))

        if not loc_res:
            return jsonify({"code": 404, "msg": "无法计算出目标的有效地理坐标"}), 404

        person_lat = loc_res['lat']
        person_lng = loc_res['lng']

        # 7. 计算距离
        distance_to_fence = None
        if fence_coords:
            dist = get_distance_professional(person_lat, person_lng, fence_coords)
            if dist is not None:
                distance_to_fence = round(dist, 2)
        print(distance_to_fence)
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