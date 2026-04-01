# backend/main_sys_v2.py
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
from pyproj import CRS, Transformer

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

# [优化点3.1：性能优化] 将投影转换器变为全局单例，避免高并发下每次请求重复初始化 C++ 对象耗时
GLOBAL_TRANSFORMER = Transformer.from_crs("epsg:4490", "epsg:3857", always_xy=True)

# 3. 加载 CSV 设备配置
# [优化点3.2：性能优化] 将 DataFrame 转化为 Hash 字典，将查询时间复杂度从 O(N) 全表扫描降为 O(1) 极速哈希查询
DEVICE_DICT = {}
CSV_FILE_PATH = "tb_device_202603231527.csv"
try:
    DEVICE_DF = pd.read_csv(CSV_FILE_PATH, encoding='gbk')
    # 因为会报错“读取 CSV 文件失败”，发现csv中dev_addr不是唯一值
    # [关键修复] 强制去重：如果发现重复的 IP (dev_addr)，保留最后出现的一条记录
    DEVICE_DF = DEVICE_DF.drop_duplicates(subset=['dev_addr'], keep='last')
    # 以 IP (dev_addr) 为 Key，整行数据转换为字典作为 Value
    DEVICE_DICT = DEVICE_DF.set_index('dev_addr').to_dict('index')
    print(f"[+] 成功加载设备配置表，共 {len(DEVICE_DICT)} 条记录已缓存至内存字典。")
except Exception as e:
    print(f"[-] 读取 CSV 文件失败，请检查文件路径！错误: {e}")


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
    # [注意] 这里不能转换为4326，因为shapely的distance是欧式距离，不是球面
    # 同时也不能用3857，会在不同纬度有拉伸，比如北京的40，会大概1.3倍
    # if not fence_coords:
    #     return None
    # p_lat = float(person_lat)
    # p_lon = float(person_lon)
    # transformer = Transformer.from_crs("epsg:4490", "epsg:3857", always_xy=True)
    # px, py = transformer.transform(p_lon, p_lat)
    # person_pt = Point(px, py)
    # # 转换围栏坐标
    # fence_pts = [transformer.transform(float(lon), float(lat)) for lat, lon in fence_coords]
    # fence_line = LineString(fence_pts)
    # return fence_line.distance(person_pt)

    # 采用局部正方位等距投影 (AEQD)，消除墨卡托拉伸误差
    # 但是效率太低了，Gemini说，可以利用 EPSG:3857 全局单例保证性能，利用 Cosine 补偿保证物理精度
    if not fence_coords or len(fence_coords) < 2:
        return None

    p_lat = float(person_lat)
    p_lon = float(person_lon)
    
    # 1. 极速投影：使用全局单例将人员坐标转为 3857 墨卡托米
    px, py = GLOBAL_TRANSFORMER.transform(p_lon, p_lat)
    person_pt = Point(px, py)

    # 2. 极速投影：围栏坐标转换
    fence_pts = []
    for f_lat, f_lon in fence_coords:
        fx, fy = GLOBAL_TRANSFORMER.transform(float(f_lon), float(f_lat))
        fence_pts.append((fx, fy))
        
    fence_line = LineString(fence_pts)
    
    # 3. 计算 3857 坐标系下的距离 (带有拉伸误差的假距离)
    dist_3857 = fence_line.distance(person_pt)
    
    # 4. [核心魔法] 墨卡托反向缩放补偿
    # 计算当前纬度下的拉伸补偿系数 (纬度转换为弧度后求余弦)
    compensation_factor = math.cos(math.radians(p_lat))
    
    # 真实的物理距离 = 假距离 * 补偿系数
    real_dist_meters = dist_3857 * compensation_factor
    
    return real_dist_meters


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

        # [优化点2：统一角度] API约定已改为角度，移除 math.degrees，直接原样透传给算法
        cam_config = {
            'device_id': "zhdd_camera",
            'gps': {'lat': req.latitude, 'lng': req.longitude, 'alt': 0.0},
            'height': req.height,
            'pose': {'pitch': req.pitch, 'yaw': req.yaw, 'roll': req.roll},
            'hardware': {'focal_length_mm': req.f, 'sensor_width_mm': 36.0}, 
            'resolution': {'width': img_w, 'height': img_h},
            'distortion': None 
        }
        localizer = GeoLocalizer(cam_config)

        out_objects = []
        for i, obj in enumerate(req.objectList):
            b = obj.bndbox
            # [优化点1：绝对像素] API约定已改为绝对像素整数，移除归一化反算乘以宽高的逻辑
            bbox_px = [b.x, b.y, b.x + b.width, b.y + b.height]

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
            
            # x_norm = bbox_px[0] / img_w
            # y_norm = bbox_px[1] / img_h
            # width_norm = (bbox_px[2] - bbox_px[0]) / img_w
            # height_norm = (bbox_px[3] - bbox_px[1]) / img_h
            
            # bndbox = BndBox(x=x_norm, y=y_norm, width=width_norm, height=height_norm)
            bndbox = BndBox(x=int(bbox_px[0]), y=int(bbox_px[1]), width=int(bbox_px[2] - bbox_px[0]), height=int(bbox_px[3] - bbox_px[1]))
            object_code = f"{(i+1):013d}" 
            
            out_objects.append(DetectObjectOut(
                objectCode=object_code,
                objectCategory="1",
                bndbox=bndbox
            ))

        res = DetectResponse(currentTime=req.currentTime, imageUrl=req.imageUrl, objectList=out_objects)
        return jsonify(res.model_dump()), 200

    except Exception as e:
        print(f"检测异常: {str(e)}")
        return jsonify({"code": 500, "msg": f"检测异常: {str(e)}"}), 200


# ==========================================
# 接口三：人员定位并计算围栏距离 (基于 IP 查表) - 路由与逻辑分离
# ==========================================
@app.route("/xjzhdd/alarmEvent/pull/fence_distance", methods=["POST"])
def pull_fence_distance():
    """主路由：根据请求中的 camera_type 字段分发给不同的处理逻辑"""
    try:
        req_data = request.get_json()

        # 通过入参路由。如果没传，默认当做 bullet 枪机处理
        camera_type = req_data.get("camera_type", "bullet")
        
        if camera_type == "bullet":
            return process_bullet_localization(req_data)
        elif camera_type == "ptz":
            return process_ptz_localization(req_data)
        else:
            return jsonify({"code": 400, "msg": "未知的 camera_type，仅支持 bullet 或 ptz"}), 400
            
    except Exception as e:
        print(f"服务器内部错误: {str(e)}")
        return jsonify({"code": 500, "msg": f"服务器内部错误: {str(e)}"}), 500


# [新增] 模拟的 PTZ 动态参数获取接口
@app.route("/xjzhdd/alarmEvent/sub", methods=["GET", "POST"])
def mock_ptz_sub():
    """模拟上游系统返回的实时 PTZ 数据"""
    import time
    return jsonify({
        "code": 200,
        "data": {
            "timestamp": int(time.time()),
            "pan": 35.5,    # 假设此时镜头向右转了 35.5 度
            "tilt": -12.0,  # 假设此时镜头向下低了 12 度
            "zoom": 2.5     # 假设此时镜头放大了 2.5 倍
        }
    })


def process_bullet_localization(req_data):
    """固定枪机 (Bullet Camera) 的处理逻辑：参数全部查表：支持平地与山地模式""" 
    img_h, img_w = req_data.get("image_h"), req_data.get("image_w")
    ip = req_data.get("ip")
    bnd = req_data.get("bnd")
    print("--------------距离接口入参---------------------")
    print(ip)
    print(bnd)
    # 获取地形模式与图像数据
    terrain_mode = req_data.get("terrain_mode", "flat").lower()
    image_data = req_data.get("imageData")

    # 1. 严格校验参数
    if not ip or not bnd:
        return jsonify({"code": 400, "msg": "缺失必填参数 (ip, bnd)"}), 400

    # 2. 查询设备信息 (字典查询加速)
    if ip not in DEVICE_DICT:
        return jsonify({"code": 404, "msg": f"未在配置表中找到设备 IP: {ip}"}), 404
        
    device_data = DEVICE_DICT[ip]
    dev_id = str(device_data.get('dev_id', 'unknown'))

    lat = float(device_data['latitude'])
    lng = float(device_data['longitude'])
    elevation = float(device_data['elevation'])
    pitch_deg = float(device_data['pitch'])      
    direction_deg = float(device_data['direction']) 
    fence_coords = parse_line_to_fence_coords(device_data.get('line'))
    print(f"pitch_deg: {pitch_deg}\ndirection_deg: {direction_deg}\nfence_coords: {fence_coords}")
    
    # 3. 构造相机参数，枪机：所有参数都以 CSV 表里的基准数据为准
    cam_config = {
        'device_id': dev_id,
        'gps': {'lat': lat, 'lng': lng, 'alt': 15},
        'height': elevation,
        'pose': {'pitch': pitch_deg, 'yaw': direction_deg, 'roll': 0.0},
        'hardware': {'focal_length_mm': 6, 'sensor_width_mm': 5.37},
        'resolution': {'width': img_w, 'height': img_h},
        'distortion': [-0.1, 0.05, 0, 0, 0]
    }
    
    # 交给核心引擎统一计算
    return _execute_localization_core(cam_config, bnd, img_h, img_w, terrain_mode, image_data, fence_coords, dev_id)


def process_ptz_localization(req_data):
    """【球机处理逻辑】：静态经纬度查表 + 动态姿态调接口融合"""
    img_h, img_w = req_data.get("image_h"), req_data.get("image_w")
    ip = req_data.get("ip")
    bnd = req_data.get("bnd")
    # 获取地形模式与图像数据
    terrain_mode = req_data.get("terrain_mode", "flat").lower()
    image_data = req_data.get("imageData")

    # 1. 严格校验参数
    if not ip or not bnd:
        return jsonify({"code": 400, "msg": "缺失必填参数 (ip, bnd)"}), 400
    
    # 2. 读取设备ip
    if ip not in DEVICE_DICT:
        return jsonify({"code": 404, "msg": f"未在配置表中找到设备 IP: {ip}"}), 404
        
    device_data = DEVICE_DICT[ip]
    dev_id = str(device_data.get('dev_id', 'unknown'))
    
    # 3. 读取相机的初始/基准安装参数
    base_yaw = float(device_data['direction'])
    base_pitch = float(device_data['pitch'])
    base_focal = float(device_data.get('focal_length_mm', 6.0))

    # [核心修复] 动态参数获取：前端传参优先级 > 外部接口
    # ==========================================
    realtime_yaw = req_data.get("realtime_yaw")
    realtime_pitch = req_data.get("realtime_pitch")
    realtime_focal = req_data.get("realtime_focal")

    # 4. 调用外部/子接口获取当前真实的 PTZ 瞬时参数
    # (注意：因为当前是单机测试，Flask 默认开多线程才能自己请求自己。生产环境这会是另一个微服务地址)
    # 如果前端在调试，传了这三个值，优先使用！
    if realtime_yaw is not None and realtime_pitch is not None and realtime_focal is not None:
        current_pan = float(realtime_yaw)
        current_tilt = float(realtime_pitch)
        current_zoom = float(realtime_focal)
        print("[PTZ] 正在使用前端 UI 传入的调试参数进行测距计算...")
    else:
        # 否则，走生产环境流程，去调 /sub 接口
        ptz_api_url = f"http://127.0.0.1:8112/xjzhdd/alarmEvent/sub?ip={ip}"
        try:
            resp = requests.get(ptz_api_url, timeout=3)
            resp.raise_for_status()
            ptz_res = resp.json().get("data", {})
            current_pan = float(ptz_res.get("pan", 0.0))
            current_tilt = float(ptz_res.get("tilt", 0.0))
            current_zoom = float(ptz_res.get("zoom", 1.0))
            print("[PTZ] 正在使用外部 /sub 接口获取的实时参数...")
        except Exception as e:
            print(f"获取 PTZ 参数失败: {e}")
            return jsonify({"code": 500, "msg": f"无法获取球机实时 PTZ 参数: {e}"}), 500

    # 5. 将实时偏移量叠加到安装基准上
    final_yaw = (base_yaw + current_pan) % 360     # 水平偏航：基准方向 + 旋转度数 (取模保证在0-360)
    final_pitch = base_pitch + current_tilt        # 垂直俯仰：基准下倾角 + 动态下倾角
    final_focal = base_focal * current_zoom        # 实时焦距：基准物理焦距 * 光学变倍因子 (例如 6mm * 2.5倍 = 15mm)

    print(f"[PTZ] 计算后融合参数 -> Yaw: {final_yaw:.2f}, Pitch: {final_pitch:.2f}, Focal: {final_focal:.2f}mm")

    # 6. 组装最终给到底层算法的球机参数
    cam_config = {
        'device_id': dev_id,
        'gps': {
            'lat': float(device_data['latitude']), 
            'lng': float(device_data['longitude']), 
            'alt': float(device_data['elevation'])
        },
        'height': float(device_data['elevation']),
        'pose': {
            'pitch': final_pitch, 
            'yaw': final_yaw, 
            'roll': 0.0
        },
        'hardware': {
            'focal_length_mm': final_focal, 
            'sensor_width_mm': float(device_data.get('sensor_width_mm', 5.37))
        },
        'resolution': {'width': img_w, 'height': img_h},
        'distortion': [-0.1, 0.05, 0, 0, 0]
    }
    
    fence_coords = parse_line_to_fence_coords(device_data.get('line'))

    # 交给核心引擎统一计算
    return _execute_localization_core(cam_config, bnd, img_h, img_w, terrain_mode, image_data, fence_coords, dev_id)


# 核心计算引擎 (枪机和球机共享，消灭重复代码)
def _execute_localization_core(cam_config, bnd, img_h, img_w, terrain_mode, image_data, fence_coords, dev_id):
    """
    无论上游是枪机还是球机，只要拼好了 cam_config 丢进来，
    剩下的 Flat/Mount 逻辑、抠图切片逻辑、坐标反算逻辑都在这里统一执行。
    """
    if terrain_mode == "mount" and not image_data:
        return jsonify({"code": 400, "msg": "山地模式(mount)必须提供 imageData (全图或图片切片)"}), 400
    
    localizer = GeoLocalizer(cam_config)
    
    # 1. 解包定位，[应用优化] 接口约定为绝对像素整数，直接解包组装为 bbox，去掉杂乱的注释
    x1, y1 = bnd['x'], bnd['y']
    x2, y2 = bnd['x'] + bnd['width'], bnd['y'] + bnd['height']
    bbox_px = [x1, y1, x2, y2]

    # [容错校验] 保护底层算子，防止前端传过来的框越界爆错
    if x1 < 0 or x2 > img_w or y1 < 0 or y2 > img_h:
        print(f"警告：传入的绝对像素框越界 (img_size={img_w}x{img_h}, bbox={bbox_px})")
        return jsonify({"code": 400, "msg": "传入的绝对像素框越界，请检查 x, y, width, height 是否合理"}), 400
    
    loc_res = None
    
    # 2. 根据模式选择推算逻辑 (Flat vs Mount)
    if terrain_mode == "flat":
        # 平地模式：纯几何运算，无需图片
        loc_res = localizer.pixel_to_location_flat(0, conf=1.0, bbox=bbox_px, image_shape=(img_h, img_w))

    elif terrain_mode == "mount":
        # 山地模式：带切片与 Pose 推理
        try:
            # 解析前端传来的图片
            input_img = decode_base64_image(image_data)
            in_h, in_w = input_img.shape[:2]
            
            # 判断传过来的是“全图”还是“切片”
            is_crop = not (in_h == img_h and in_w == img_w)
            
            offset_x, offset_y = 0, 0
            img_to_detect = input_img

            if not is_crop:
                # 【全图模式优化】：先根据 bndbox 裁剪，再跑 pose 检测；同时记录裁剪的偏移量，方便后续将骨骼坐标映射回全图尺度
                # 1. 计算扩展边界（Padding），上下左右各扩展 20%，防止肢体被截断
                bnd_w = x2 - x1
                bnd_h = y2 - y1
                pad_w = int(bnd_w * 0.2)
                pad_h = int(bnd_h * 0.2)
                
                # 2. 计算裁剪坐标并防止越界
                crop_x1 = max(0, x1 - pad_w)
                crop_y1 = max(0, y1 - pad_h)
                crop_x2 = min(img_w, x2 + pad_w)
                crop_y2 = min(img_h, y2 + pad_h)
                
                # 3. 截取图片切片
                img_to_detect = input_img[crop_y1:crop_y2, crop_x1:crop_x2]
                
                # 4. 记录全图偏移量
                offset_x, offset_y = crop_x1, crop_y1
            else:
                # 【切片模式】：假设前端传来的切片，其左上角就是目标框的 x1, y1
                # （如果前端做过 Padding 扩展，前端需要额外把真实的切片起始点 offset_x, offset_y 传过来。这里默认用 x1, y1）
                offset_x, offset_y = x1, y1

            # YOLO Pose 检测，此时送入的 img_to_detect 是切片，大概只有几百像素
            detections = detector.detect(img_to_detect, use_pose=True)
            if not detections:
                return jsonify({"code": 406, "msg": "山地模式：未能从局部图像中识别出人体骨骼"}), 406
            
            # 取切片中置信度最高的人（通常切片里就只有目标这一个人）
            best_det = max(detections, key=lambda x: x['conf'])
            crop_kpts = best_det.get('keypoints', [])
            
            target_keypoints = []
            for kp in crop_kpts:
                kx, ky, kconf = kp
                # 核心映射：将局部切片内的坐标 (kx, ky) 加上偏移量，还原到真实的 1080P 全图尺度上
                target_keypoints.append([kx + offset_x, ky + offset_y, kconf])

            # 调用山地模式进行推算 (bbox_px 依然是全图尺度的完整目标框)
            loc_res = localizer.pixel_to_location_mount(
                0, conf=1.0, bbox=bbox_px, image_shape=(img_h, img_w), keypoints=target_keypoints
            )

        except Exception as e:
            return jsonify({"code": 500, "msg": f"山地骨骼提取及推算异常: {str(e)}"}), 500
    
    if not loc_res:
        print("----------------bbox_px-----------------------------")
        print(bbox_px)
        print("----------------img_h, img_w-----------------------------")
        print(img_h)
        print(img_w)
        print("----------------loc_res-----------------------------")
        print(loc_res)
        return jsonify({"code": 406, "msg": "无法计算出目标的有效地理坐标"}), 406

    person_lat, person_lng = loc_res['lat'], loc_res['lng']
    print("---------------------人的经纬度--------------------")
    print(f"person_lat: {person_lat}\nperson_lng: {person_lng}\nfence_coords: {fence_coords}")

    # 7. 计算距离
    distance_to_fence = None
    if fence_coords:
        dist = get_distance_professional(person_lat, person_lng, fence_coords)
        if dist is not None:
            distance_to_fence = round(dist, 5)

    print("与墙之间距离distance_to_fence: ", distance_to_fence)

    # 加上 camera_lat 和 camera_lng
    result_data = {
        "dev_id": dev_id,
        "person_lat": person_lat,
        "person_lng": person_lng,
        "distance_to_fence": distance_to_fence,
        "terrain_mode": terrain_mode,
        # 这两个只是为了前端展示，实际中不用。理论上不占太多带宽，如果感觉别扭，可以去掉
        "camera_lat": cam_config['gps']['lat'],  # [新增] 真实相机纬度
        "camera_lng": cam_config['gps']['lng'],  # [新增] 真实相机经度
        # 下面两个也是为了前端展示
        "distance_from_camera": loc_res.get('distance', 0), # [新增] 返回人离相机的直线距离
        "fence_coords": fence_coords,          # [新增] 将围栏坐标原样返回给前端画线
    }

    return jsonify({"code": 200, "data": result_data}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8112, debug=True)
