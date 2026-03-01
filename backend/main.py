# backend/main.py
# [修改] 导入 Flask 相关模块
from flask import Flask, request, jsonify
from flask_cors import CORS
from pydantic import ValidationError
import os

# 导入模块 (保持不变)
from src.detector import PersonDetector
from src.geolocalizer import GeoLocalizer
from src.visualizer import Visualizer
from src.utils import decode_image, encode_image_to_base64, calculate_geo_polygon
from api.schemas import LocalizationRequest, ApiResponse, SuspectResult

# [修改] 初始化 Flask App
app = Flask(__name__)

# [修改] 允许跨域 (给Vue用)
CORS(app, resources={r"/*": {"origins": "*"}}) # 生产环境建议明确 origins

# [修改] 移除全局写死的 detector，改为模型缓存池 (防止重复加载挤爆显存)
detector_cache = {}
visualizer = Visualizer()

def get_detector(det_name: str, pose_name: str) -> PersonDetector:
    """动态加载模型并缓存，包含文件存在性校验"""
    cache_key = f"{det_name}_{pose_name}"
    
    if cache_key not in detector_cache:
        # 拼接实际的绝对/相对路径
        det_path = f'./models/Detect/{det_name}.pt'
        pose_path = f'./models/Pose/{pose_name}.pt'
        
        # 安全校验：确保文件存在
        if not os.path.exists(det_path):
            raise ValueError(f"检测模型文件不存在: {det_path}")
        if not os.path.exists(pose_path):
            raise ValueError(f"姿态模型文件不存在: {pose_path}")

        print(f"Loading new models into GPU: {det_name} & {pose_name}...")
        detector_cache[cache_key] = PersonDetector(det_path, pose_path)
        
    return detector_cache[cache_key]

# [修改] 路由装饰器和函数签名
@app.route("/api/v1/perception/suspect_localization", methods=["POST"])
def analyze():
    # [新增] 手动解析 JSON 并用 Pydantic 校验
    try:
        req_data = request.get_json()
        if not req_data:
            return jsonify({"detail": "Missing JSON request body"}), 400
        req = LocalizationRequest(**req_data)
    except ValidationError as e:
        # 捕获 Pydantic 校验错误并返回 422 状态码 (对齐 FastAPI 行为)
        return jsonify({"detail": e.errors()}), 422

    # 1. 解码图片
    try:
        image = decode_image(req.image_data)
        if image is None: raise ValueError("Image decoding failed")
        h, w = image.shape[:2]
    except Exception as e:
        # [修改] 替换 HTTPException 为 Flask 的 return jsonify
        return jsonify({"detail": f"Invalid image data: {str(e)}"}), 400

    # 2. 准备配置 (保持不变)
    cam_config = {
        'device_id': req.camera_info.device_id,
        'gps': req.camera_info.extrinsics.gps.model_dump(),
        'height': req.camera_info.extrinsics.height_above_ground,
        'pose': req.camera_info.extrinsics.pose.model_dump(),
        'hardware': req.camera_info.intrinsics.hardware_specs,
        'resolution': req.camera_info.intrinsics.image_resolution,
        'distortion': req.camera_info.intrinsics.distortion_coeffs
    }
    localizer = GeoLocalizer(cam_config)

    # 获取前端传来的地形模式 (保持不变)
    current_terrain = getattr(req, 'terrain', 'flat') 
    use_pose = (current_terrain == 'mount')

    # 根据前端传来的模型名称动态获取检测器，加上 try-catch
    try:
        detector = get_detector(req.det_model, req.pose_model)
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    # 3. 如果请求中 targets 为空，则调用 detector 检测 (保持不变)
    detections = detector.detect(image, use_pose=use_pose)
    
    api_results = []
    processed_viz_data = [] # 用于给 visualizer 画图

    # 4. 遍历检测结果进行定位 (逻辑保持不变)
    for i, det in enumerate(detections):
        target_id = f"person_{i+1:02d}"
        bbox = det['bbox'] 
        conf = det['conf'] 
        kpts = det.get('keypoints') 

        loc_res = None
        if current_terrain == 'flat':
            loc_res = localizer.pixel_to_location_flat(i, conf, bbox, (h, w))
        elif current_terrain == 'mount':
            loc_res = localizer.pixel_to_location_mount(i, conf, bbox, (h, w), keypoints=kpts)

        if loc_res:
            processed_viz_data.append(loc_res)

            # 计算多边形
            d_min, d_max = loc_res['dist_range']
            poly = calculate_geo_polygon(
                req.camera_info.extrinsics.gps.lat,
                req.camera_info.extrinsics.gps.lng,
                loc_res['bearing'],
                d_min, d_max
            )

            res_item = SuspectResult(
                target_id=target_id,
                suspect_geo_location={
                    "lat": loc_res['lat'], "lng": loc_res['lng'], "alt": loc_res.get('alt', 0.0)
                },
                confidence=conf,
                suspect_region_polygon=poly,
                computation_details={
                    "calculated_depth": loc_res['distance'], 
                    "straight_distance": loc_res['distance'],
                    "bearing_angle": loc_res['bearing']
                }
            )
            api_results.append(res_item)

    # 5. 生成可视化图片 (保持不变)
    img_det = visualizer.draw_detections(image, processed_viz_data)
    img_radar = visualizer.draw_radar_map(processed_viz_data)
    img_skel = visualizer.draw_skeleton(image, processed_viz_data)

    # 6. 返回最终 JSON
    # [修改] 使用 Pydantic 组装对象后，转换为 dict，再用 jsonify 返回
    final_response = ApiResponse(
        code=200,
        message="Location estimated successfully",
        data={
            "req_id": req.req_id,
            "results": api_results
        },
        demo_images={
            "detection_image": encode_image_to_base64(img_det),
            "radar_image": encode_image_to_base64(img_radar),
            "skeleton_image": encode_image_to_base64(img_skel) 
        }
    )
    
    # [新增] 返回字典格式
    return jsonify(final_response.model_dump()), 200

if __name__ == "__main__":
    # [修改] 使用 Flask 的启动方式
    app.run(host="0.0.0.0", port=8001, debug=True)
