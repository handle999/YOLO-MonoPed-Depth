import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# 导入模块
from src.detector import PersonDetector
from src.geolocalizer import GeoLocalizer
from src.visualizer import Visualizer
from src.utils import decode_image, encode_image_to_base64, calculate_geo_polygon
from api.schemas import LocalizationRequest, ApiResponse, SuspectResult

app = FastAPI(title="Monocular Localization API")

# 允许跨域 (给Vue用)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 生产环境建议改为 ["http://localhost:5173"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局初始化检测器 (节省显存)
detector = PersonDetector('./models/Detect/yolo26l.pt', './models/Pose/yolo11l-pose.pt')
visualizer = Visualizer()

@app.post("/api/v1/perception/suspect_localization", response_model=ApiResponse)
async def analyze(req: LocalizationRequest):
    # 1. 解码图片
    try:
        image = decode_image(req.image_data)
        if image is None: raise ValueError("Image decoding failed")
        h, w = image.shape[:2]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image data: {str(e)}")

    # 2. 准备配置
    cam_config = {
        'device_id': req.camera_info.device_id,

        'gps': req.camera_info.extrinsics.gps.dict(),
        'height': req.camera_info.extrinsics.height_above_ground,
        'pose': req.camera_info.extrinsics.pose.dict(),

        'hardware': req.camera_info.intrinsics.hardware_specs,
        'resolution': req.camera_info.intrinsics.image_resolution,

        'distortion': req.camera_info.intrinsics.distortion_coeffs
    }
    localizer = GeoLocalizer(cam_config)

    # [新增] 获取前端传来的地形模式 (默认为 flat)
    # 注意：你需要去 api/schemas.py 给 LocalizationRequest 加一个 terrain 字段
    current_terrain = getattr(req, 'terrain', 'flat') 
    use_pose = (current_terrain == 'mount')

    # 3. 如果请求中 targets 为空，则调用 detector 检测
    # 注意：API 定义里 targets 有数据说明前端可能已经有框了，
    # 但作为Demo，我们这里强制重新检测以保证流程闭环，或者混合使用
    detections = detector.detect(image, use_pose=use_pose)
    
    api_results = []
    processed_viz_data = [] # 用于给 visualizer 画图

    # 4. 遍历检测结果进行定位
    for i, det in enumerate(detections):
        # 统一编号
        target_id = f"person_{i+1:02d}"
        bbox = det['bbox'] # [x1, y1, x2, y2]
        conf = det['conf'] # [新增] 获取置信度
        kpts = det.get('keypoints') # [新增] 获取骨架

        # [修改] 核心定位逻辑分支 (对齐 infer_loc.py 的参数签名)
        loc_res = None
        if current_terrain == 'flat':               # 传参变更: 增加 i(index), conf, bbox, img_shape
            loc_res = localizer.pixel_to_location_flat(i, conf, bbox, (h, w))
        elif current_terrain == 'mount':            # 传参变更: 增加 keypoints
            loc_res = localizer.pixel_to_location_mount(i, conf, bbox, (h, w), keypoints=kpts)

        if loc_res:
            processed_viz_data.append(loc_res)

            # 计算多边形 (用于前端地图)
            d_min, d_max = loc_res['dist_range']
            poly = calculate_geo_polygon(
                req.camera_info.extrinsics.gps.lat,
                req.camera_info.extrinsics.gps.lng,
                loc_res['bearing'],
                d_min, d_max
            )

            # 构造结果对象
            res_item = SuspectResult(
                target_id=target_id,
                suspect_geo_location={
                    "lat": loc_res['lat'], "lng": loc_res['lng'], "alt": loc_res.get('alt', 0.0)
                },
                confidence=conf,
                suspect_region_polygon=poly,
                computation_details={
                    "calculated_depth": loc_res['distance'], # 垂直深度近似
                    "straight_distance": loc_res['distance'],
                    "bearing_angle": loc_res['bearing']
                }
            )
            api_results.append(res_item)

    # 5. 生成可视化图片 (Detection + Radar)
    img_det = visualizer.draw_detections(image, processed_viz_data)
    img_radar = visualizer.draw_radar_map(processed_viz_data)
    img_skel = visualizer.draw_skeleton(image, processed_viz_data)

    # 6. 返回最终 JSON
    return ApiResponse(
        code=200,
        message="Location estimated successfully",
        data={
            "req_id": req.req_id,
            "results": api_results
        },
        demo_images={
            "detection_image": encode_image_to_base64(img_det),
            "radar_image": encode_image_to_base64(img_radar),
            "skeleton_image": encode_image_to_base64(img_skel) # [新增] 返回骨架图
        }
    )

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
