import argparse
import cv2
import os
import yaml
from src.detector import PersonDetector
from src.geolocalizer import GeoLocalizer
from src.visualizer import Visualizer

# 模拟加载配置 (实际项目中建议从 yaml 文件读取)
# 这里为了演示方便，用硬编码默认值，但可以通过 args 覆盖部分参数
DEFAULT_CONFIG = {
    'gps': {
        'lat': 22.54321, 
        'lng': 114.05755, 
        'alt': 15.0
    },
    'height': 3.5,
    'pose': {
        'pitch': -15.0,
        'yaw': 36.0,
        'roll': 0.0
    },
    'hardware': {
        'focal_length_mm': 6.0, 
        'sensor_width_mm': 5.37
    },
    # 可选: 'distortion': [] 
}

def parse_args():
    parser = argparse.ArgumentParser(description="YOLOv8 人员定位与可视化工具")
    
    # 基础参数
    parser.add_argument('--source', type=str, required=True, help='输入图片路径或视频路径')
    parser.add_argument('--det_weight', type=str, default='./models/Detect/yolo26l.pt', help='YOLO检测模型路径')
    parser.add_argument('--pose_weight', type=str, default=None, help='YOLO姿态模型路径 (可选)')
    parser.add_argument('--output_dir', type=str, default='data/outputs', help='结果保存目录')
    
    # 功能开关
    parser.add_argument('--show', action='store_true', help='实时显示窗口')
    parser.add_argument('--save_radar', action='store_true', help='是否生成并保存雷达图')
    parser.add_argument('--terrain', help='地形（决定定位模式)', choices=['flat', 'mount'], default='flat')
    
    # 相机参数覆盖 (可选，方便调试)
    parser.add_argument('--cam_height', type=float, default=3.5, help='相机离地高度(米)')
    parser.add_argument('--cam_pitch', type=float, default=-15.0, help='相机俯仰角(度)')

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    
    # 1. 准备目录
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 2. 更新配置
    camera_config = DEFAULT_CONFIG.copy()
    camera_config['height'] = args.cam_height
    camera_config['pose']['pitch'] = args.cam_pitch
    
    # 3. 初始化模块
    if args.pose_weight:
        detector = PersonDetector(det_model_path=args.det_weight, pose_model_path=args.pose_weight)
    else:
        detector = PersonDetector(det_model_path=args.det_weight, pose_model_path=None)
    localizer = GeoLocalizer(camera_config)
    visualizer = Visualizer()
    
    # 4. 读取图片
    frame = cv2.imread(args.source)
    if frame is None:
        print(f"Error: 无法读取图片 {args.source}")
        exit(1)
    
    img_shape = frame.shape[:2] # h, w

    # 5. 核心流程
    # A. 检测
    use_pose = (args.terrain == 'mount') # 或者直接 True
    raw_detections = detector.detect(args.source, use_pose=use_pose) # detect方法需支持返回纯list
    
    processed_results = []
    
    # B. 定位
    for i, det in enumerate(raw_detections):
        # det: [{'bbox': [x1,y1,x2,y2], 'conf': float}]
        bbox = det['bbox'] # [x1, y1, x2, y2]
        conf = det['conf']
        kpts = det.get('keypoints') # [新增] 如果检测器支持关键点输出，可以在这里获取，供山地模式使用
        
        if args.terrain == 'flat':
            loc_result = localizer.pixel_to_location_flat(i, conf, bbox, img_shape)
        elif args.terrain == 'mount':
            loc_result = localizer.pixel_to_location_mount(i, conf, bbox, img_shape, keypoints=kpts)
        
        if loc_result:
            processed_results.append(loc_result)
            
            print(f"目标[{i+1}]: Dist={loc_result['distance']:.2f}m, Conf={conf:.2f}, "
                  f"Range={loc_result['dist_range']}, "
                  f"Loc=({loc_result['lat']:.6f}, {loc_result['lng']:.6f})")

    # 6. 可视化
    base_name = os.path.basename(args.source)
    name_only, ext = os.path.splitext(base_name)

    # [图1] 保存 Detection Only (只有框)
    img_det = visualizer.draw_detections(frame, processed_results)
    save_path_det = os.path.join(args.output_dir, f"{name_only}_det{ext}")
    cv2.imwrite(save_path_det, img_det)
    print(f"检测结果已保存至: {save_path_det}")

    # [图2] 保存 Skeleton (框 + 骨架) - 仅在开启 Pose 模式时生成
    # 注意：如果不开启 use_pose，keypoints 为 None，这张图和图1是一样的
    img_skel = visualizer.draw_skeleton(frame, processed_results)
    save_path_skel = os.path.join(args.output_dir, f"{name_only}_pose{ext}")
    cv2.imwrite(save_path_skel, img_skel)
    print(f"骨架分析图已保存至: {save_path_skel}")

    # [图3] 保存 Radar Map (雷达图)
    if args.save_radar:
        img_radar = visualizer.draw_radar_map(processed_results)
        save_path_radar = os.path.join(args.output_dir, f"{name_only}_radar{ext}")
        cv2.imwrite(save_path_radar, img_radar)
        print(f"雷达俯视图已保存至: {save_path_radar}")

    # C. 显示 (这里任选一张显示，通常显示骨架图最直观)
    if args.show:
        cv2.imshow("Detection + Pose", img_skel) # 显示最全的那张
        if args.save_radar:
            cv2.imshow("Radar Map", img_radar)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
