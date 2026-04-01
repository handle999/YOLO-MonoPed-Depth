# backend/main_v2.py
##功能：在已有main.py基础上，实现功能：围栏到人计算距离，距离结果加入已有接口输出
from flask import Flask, request, jsonify
from flask_cors import CORS
from pydantic import ValidationError
import os
from decimal import Decimal

# 导入空间计算相关的库
from shapely.geometry import Point, LineString
from pyproj import Transformer

# 导入模块 (保持不变)
from src.detector import PersonDetector
from backend.src.geolocalizertem import GeoLocalizer
from src.visualizer import Visualizer
from src.utils import decode_image, encode_image_to_base64, calculate_geo_polygon
from api.schemas import LocalizationRequest, ApiResponse, SuspectResult

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

detector_cache = {}
visualizer = Visualizer()

# ==========================================
# [新增] 写死的护栏轨迹坐标 (全局变量)
# 格式: (lat, lon)
# ==========================================
FENCE_COORDS = [
    (40.049478, 116.273055),
    (40.050859, 116.280843)
]

def get_detector(det_name: str, pose_name: str) -> PersonDetector:
    cache_key = f"{det_name}_{pose_name}"
    
    if cache_key not in detector_cache:
        det_path = f'./models/Detect/{det_name}.pt'
        pose_path = f'./models/Pose/{pose_name}.pt'
        
        if not os.path.exists(det_path):
            raise ValueError(f"检测模型文件不存在: {det_path}")
        if not os.path.exists(pose_path):
            raise ValueError(f"姿态模型文件不存在: {pose_path}")

        print(f"Loading new models into GPU: {det_name} & {pose_name}...")
        detector_cache[cache_key] = PersonDetector(det_path, pose_path)
        
    return detector_cache[cache_key]

def get_distance_professional(person_lat, person_lon, fence_coords):
    """计算人员经纬度到围栏轨迹的最短距离 (单位: 米)"""
    if not fence_coords or len(fence_coords) < 2:
        return None

    p_lat = float(person_lat)
    p_lon = float(person_lon)
    
    transformer = Transformer.from_crs("epsg:4326", "epsg:3857", always_xy=True)

    px, py = transformer.transform(p_lon, p_lat)
    person_pt = Point(px, py)

    # 转换围栏坐标 (lat, lon) 
    fence_pts = [transformer.transform(float(lon), float(lat)) for lat, lon in fence_coords]
    
    fence_line = LineString(fence_pts)
    
    return fence_line.distance(person_pt)

@app.route("/api/v1/perception/suspect_localization", methods=["POST"])
def analyze():
    try:
        req_data = request.get_json()
        if not req_data:
            return jsonify({"detail": "Missing JSON request body"}), 400
        # 新增：围栏坐标入参
        current_fence_coords = req_data.get("fence_coords")
        if not current_fence_coords:
            current_fence_coords = FENCE_COORDS
        req = LocalizationRequest(**req_data)

    except ValidationError as e:
        return jsonify({"detail": e.errors()}), 422

    try:
        image = decode_image(req.image_data)
        if image is None: raise ValueError("Image decoding failed")
        h, w = image.shape[:2]
    except Exception as e:
        return jsonify({"detail": f"Invalid image data: {str(e)}"}), 400

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

    current_terrain = getattr(req, 'terrain', 'flat') 
    use_pose = (current_terrain == 'mount')

    try:
        detector = get_detector(req.det_model, req.pose_model)
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400

    detections = detector.detect(image, use_pose=use_pose)
    
    api_results = []
    processed_viz_data = []

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

            d_min, d_max = loc_res['dist_range']
            poly = calculate_geo_polygon(
                req.camera_info.extrinsics.gps.lat,
                req.camera_info.extrinsics.gps.lng,
                loc_res['bearing'],
                d_min, d_max
            )

            # [修改] 计算人到围栏的距离
            dist_to_fence = None
            try:
                print("loc_res['lat']:",loc_res['lat'])
                dist = get_distance_professional(loc_res['lat'], loc_res['lng'], current_fence_coords)
                if dist is not None:
                    dist_to_fence = round(dist, 2)
            except Exception as e:
                print(f"围栏距离计算失败: {e}")

            computation_details = {
                "calculated_depth": loc_res['distance'], 
                "straight_distance": loc_res['distance'],
                "bearing_angle": loc_res['bearing']
            }
            
            # 把算好的距离放进返回值里
            if dist_to_fence is not None:
                computation_details["distance_to_fence"] = dist_to_fence
            #print("computation_details:",computation_details)
            #print("loc_res:",loc_res)
            res_item = SuspectResult(
                target_id=target_id,
                suspect_geo_location={
                    "lat": loc_res['lat'], "lng": loc_res['lng'], "alt": loc_res.get('alt', 0.0)
                },
                confidence=conf,
                suspect_region_polygon=poly,
                computation_details=computation_details
            )
            api_results.append(res_item)

    img_det = visualizer.draw_detections(image, processed_viz_data)
    img_radar = visualizer.draw_radar_map(processed_viz_data)
    img_skel = visualizer.draw_skeleton(image, processed_viz_data)

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
    
    return jsonify(final_response.model_dump()), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8110, debug=True)