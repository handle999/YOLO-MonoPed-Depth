# src/utils.py
import base64
import numpy as np
import cv2
import requests
from geopy.distance import geodesic
from geopy.point import Point

def decode_image(image_data):
    img = None
    if image_data.base64:
        # 处理 Base64 (兼容带前缀的情况)
        b64_str = image_data.base64.split(',')[-1]
        img_bytes = base64.b64decode(b64_str)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    elif image_data.image_url:
        resp = requests.get(image_data.image_url, timeout=5)
        nparr = np.frombuffer(resp.content, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img

def encode_image_to_base64(cv_img):
    _, buffer = cv2.imencode('.jpg', cv_img)
    return "data:image/jpeg;base64," + base64.b64encode(buffer).decode('utf-8')

def calculate_geo_polygon(cam_lat, cam_lng, bearing, dist_min, dist_max, width_degrees=3.0):
    """
    dist_min/max 转换成前端地图需要的 lat/lng 数组，计算基于地理坐标的梯形误差区域
    bearing: 目标方位角 (0-360)
    width_degrees: 扇区半宽度 (例如 +/- 3度)
    """
    origin = Point(cam_lat, cam_lng)
    
    # 四个顶点：近左 -> 近右 -> 远右 -> 远左，注意 geopy 的 bearing 是 0=North, 90=East
    
    # 角度计算
    bearings = [
        (bearing - width_degrees) % 360, # 左边界角度
        (bearing + width_degrees) % 360  # 右边界角度
    ]
    
    points = []
    
    # 1. 近端 (左, 右)
    points.append(geodesic(meters=dist_min).destination(origin, bearings[0]))
    points.append(geodesic(meters=dist_min).destination(origin, bearings[1]))
    # 2. 远端 (右, 左) - 顺序要构成闭环
    points.append(geodesic(meters=dist_max).destination(origin, bearings[1]))
    points.append(geodesic(meters=dist_max).destination(origin, bearings[0]))
    
    # 转换为 dict list
    return [{"lat": p.latitude, "lng": p.longitude} for p in points]
