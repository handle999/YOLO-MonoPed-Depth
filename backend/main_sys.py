# backend/main_sys.py
import math
import cv2
import numpy as np
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS  # [必须新增] 引入跨域组件
from pydantic import ValidationError

# 引入你的底层算法库
from src.detector import PersonDetector
from src.geolocalizer import GeoLocalizer
# 引入刚才写好的全新 Schema
from api.schemas_sys import (
    LocalRequest, LocalResponse, LocalObjectOut,
    DetectRequest, DetectResponse, DetectObjectOut, BndBox
)

app = Flask(__name__)
# [必须新增] 允许前端跨域访问 8002 端口
CORS(app, resources={r"/*": {"origins": "*"}})

# 为指挥系统专门初始化一个全局的检测器 (使用最优模型)
detector = PersonDetector('./models/Detect/yolo26l.pt', './models/Pose/yolo26l-pose.pt')

def download_image(url: str):
    """通过 URL 下载图片并转为 OpenCV 格式"""
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        image_array = np.frombuffer(resp.content, np.uint8)
        img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Failed to decode image from URL")
        return img
    except Exception as e:
        raise ValueError(f"Image Download Error: {str(e)}")


# ---------------------------------------------------------
# 接口一：人员定位 (指挥系统传框，本地算坐标)
# ---------------------------------------------------------
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


if __name__ == "__main__":
    # 使用 8002 端口专门为指挥系统提供服务
    app.run(host="0.0.0.0", port=8111, debug=True)
