# kitti_infer.py
import os
import cv2
import json
import time
import argparse
import numpy as np
import torch
from tqdm import tqdm

# 引入自定义模块
from src.detector import PersonDetector
from src.geolocalizer import GeoLocalizer
from src.visualizer import Visualizer

def parse_args():
    """配置所有命令行参数，消除硬编码"""
    parser = argparse.ArgumentParser(description="KITTI 3D Pedestrian Localization Inference")

    # --- 1. 文件路径配置 ---
    group_path = parser.add_argument_group('Paths')
    group_path.add_argument('--kitti_root', type=str, default='data/kitti', help='KITTI 数据集根目录')
    group_path.add_argument('--output_dir', type=str, default='data/yolo26_rsts', help='结果输出目录')
    group_path.add_argument('--det_model', type=str, default='./models/Detect/yolo26l.pt', help='检测模型路径')
    group_path.add_argument('--pose_model', type=str, default='./models/Pose/yolo26l-pose.pt', help='姿态模型路径')

    # --- 2. 硬件与模型配置 ---
    group_hw = parser.add_argument_group('Hardware & Model')
    group_hw.add_argument('--device', type=str, default='0', help='运行设备 e.g., "0", "cpu", "mps"')
    group_hw.add_argument('--conf_thres', type=float, default=0.2, help='检测置信度阈值')
    group_hw.add_argument('--limit', type=int, default=0, help='限制测试图片数量 (0为不限制)')

    # --- 3. 算法参数配置 ---
    group_algo = parser.add_argument_group('Algorithm')
    group_algo.add_argument('--mode', type=str, default='mount', choices=['flat', 'mount'], help='测距模式')
    group_algo.add_argument('--cam_height', type=float, default=1.65, help='相机离地高度 (KITTI 默认为 1.65m)')
    
    return parser.parse_args()

def parse_calib(calib_path):
    """
    [修改] 从 P2 矩阵提取完整投影矩阵 (3x4) 以及焦距 fx
    返回: (fx, P2_matrix)
    """
    if not os.path.exists(calib_path): return None, None
    with open(calib_path, 'r') as f:
        for line in f.readlines():
            if line.startswith('P2:'):
                parts = line.split()
                if len(parts) > 12:
                    # P2 是 3x4 矩阵
                    p2 = np.array([float(x) for x in parts[1:]]).reshape(3, 4)
                    fx = p2[0, 0]
                    return fx, p2
    return None, None

def generate_kitti_line(obj, calib_p2):
    """
    [新增] 将检测结果转换为 KITTI 提交格式字符串 (16列)
    obj: dict, 包含 'bbox', 'distance', 'conf'
    calib_p2: 3x4 numpy array
    """
    cls_type = "Pedestrian"
    truncation = 0.00
    occlusion = 0 # 默认无遮挡
    alpha = -10.0 # 观测角 (未知填-10)
    
    x1, y1, x2, y2 = obj['bbox']
    
    # 3D 尺寸先验 (H, W, L)
    h, w, l = 1.75, 0.6, 0.7 
    
    # 3D 位置计算 (Camera Coordinate)
    z = obj['distance']
    
    fx = calib_p2[0, 0]
    cx = calib_p2[0, 2]
    fy = calib_p2[1, 1]
    cy = calib_p2[1, 2]
    
    # 基于 BBox 中心和底部反推 x, y
    u_c = (x1 + x2) / 2
    v_b = y2 
    
    x = (u_c - cx) * z / fx
    y = (v_b - cy) * z / fy 
    
    ry = -10.0 # 朝向 (未知填-10)
    score = obj['conf']
    
    return f"{cls_type} {truncation:.2f} {occlusion} {alpha:.2f} " \
           f"{x1:.2f} {y1:.2f} {x2:.2f} {y2:.2f} " \
           f"{h:.2f} {w:.2f} {l:.2f} " \
           f"{x:.2f} {y:.2f} {z:.2f} " \
           f"{ry:.2f} {score:.2f}"

def main():
    args = parse_args()

    # 1. 目录准备
    base_img_dir = os.path.join(args.kitti_root, 'data_object_image_2', 'training', 'image_2')
    base_calib_dir = os.path.join(args.kitti_root, 'data_object_calib', 'training', 'calib')
    
    # [修改] 定义两种输出目录
    save_json_dir = os.path.join(args.output_dir, 'json') # 存 JSON (你的格式)
    save_txt_dir = os.path.join(args.output_dir, 'data') # [新增] 存 TXT (KITTI格式)
    save_vis_dir = os.path.join(args.output_dir, 'vis')
    
    os.makedirs(save_json_dir, exist_ok=True)
    os.makedirs(save_txt_dir, exist_ok=True) # [新增]
    os.makedirs(save_vis_dir, exist_ok=True)

    # 2. 初始化模型
    print(f"🚀 Loading models on device: {args.device}...")
    detector = PersonDetector(
        det_model_path=args.det_model, 
        pose_model_path=args.pose_model,
        device=args.device
    )
    visualizer = Visualizer()

    # ================= [预热] GPU 冷启动 Warmup =================
    print("🔥 Warming up GPU...")
    dummy_img = np.zeros((375, 1242, 3), dtype=np.uint8)
    detector.detect(dummy_img, use_pose=False) 
    if detector.pose_model:
        detector.pose_model(dummy_img, verbose=False, device=args.device)
    print("✅ Warmup complete. Starting benchmark...")
    # ==========================================================

    if not os.path.exists(base_img_dir):
        print(f"Error: Image directory not found: {base_img_dir}")
        return
        
    img_files = sorted([f for f in os.listdir(base_img_dir) if f.endswith('.png')])
    if args.limit > 0: img_files = img_files[:args.limit]

    print(f"Start Inference on {len(img_files)} images...")
    
    # 3. 批量推理循环
    for img_file in tqdm(img_files):
        file_id = os.path.splitext(img_file)[0]
        
        # A. 读图
        img_path = os.path.join(base_img_dir, img_file)
        frame = cv2.imread(img_path)
        if frame is None: continue
        h, w = frame.shape[:2]

        # B. 读 Calib
        calib_path = os.path.join(base_calib_dir, f"{file_id}.txt")
        # [修改] 获取完整 P2 矩阵
        fx, p2_matrix = parse_calib(calib_path)
        if fx is None: continue

        # C. 动态配置 Geolocalizer
        config = {
            'gps': {'lat': 0, 'lng': 0, 'alt': 0},
            'height': args.cam_height, 
            'pose': {'pitch': 0, 'yaw': 0, 'roll': 0}, 
            'hardware': {'focal_length_mm': fx, 'sensor_width_mm': w}
        }
        localizer = GeoLocalizer(config)

        # --- 计时开始 ---
        t_start_total = time.time()
        
        # Phase 1: Detection
        t_det_start = time.time()
        detections = detector.detect(frame, use_pose=False) 
        t_det_end = time.time()
        
        # Phase 2: Pose Estimation
        t_pose_start = time.time()
        
        if args.mode == 'mount' and detector.pose_model:
            pose_crops = []
            pose_indices = []
            pose_offsets = []

            for i, det in enumerate(detections):
                x1, y1, x2, y2 = det['bbox']
                
                w_box, h_box = x2 - x1, y2 - y1
                pad_w, pad_h = int(w_box * 0.15), int(h_box * 0.15)
                crop_x1 = max(0, x1 - pad_w)
                crop_y1 = max(0, y1 - pad_h)
                crop_x2 = min(w, x2 + pad_w)
                crop_y2 = min(h, y2 + pad_h)
                
                person_crop = frame[crop_y1:crop_y2, crop_x1:crop_x2]
                
                if person_crop.size > 0:
                    pose_crops.append(person_crop)
                    pose_indices.append(i)
                    pose_offsets.append((crop_x1, crop_y1))

            if len(pose_crops) > 0:
                batch_results = detector.pose_model(pose_crops, verbose=False, conf=0.5, device=args.device)
                
                for idx, result in enumerate(batch_results):
                    target_idx = pose_indices[idx]
                    off_x, off_y = pose_offsets[idx]
                    
                    if result.keypoints is not None and len(result.keypoints.data) > 0:
                        kpts_local = result.keypoints.data[0].cpu().numpy()
                        kpts_global = []
                        for kp in kpts_local:
                            kpts_global.append([kp[0] + off_x, kp[1] + off_y, kp[2]])
                        
                        detections[target_idx]['keypoints'] = kpts_global

        t_pose_end = time.time()

        # Phase 3: Localization
        processed_results = []
        for det in detections:
            loc_res = None
            kpts = det.get('keypoints')
            
            if args.mode == 'mount':
                loc_res = localizer.pixel_to_location_mount(0, det['conf'], det['bbox'], (h,w), kpts)
            else:
                loc_res = localizer.pixel_to_location_flat(0, det['conf'], det['bbox'], (h,w))
            
            if loc_res:
                loc_res['target_id'] = "P"
                loc_res['conf'] = det['conf']
                if kpts: loc_res['keypoints'] = kpts
                processed_results.append(loc_res)

        t_end_total = time.time()

        # --- 保存结果 1: JSON (你的格式) ---
        save_data = {
            'file_id': file_id,
            'image_size': [w, h],
            'time_stats': {
                'total_ms': (t_end_total - t_start_total) * 1000,
                'det_ms': (t_det_end - t_det_start) * 1000,
                'pose_ms': (t_pose_end - t_pose_start) * 1000,
                'post_ms': (t_end_total - t_pose_end) * 1000
            },
            'objects': []
        }

        # [新增] 准备 KITTI TXT 内容列表
        kitti_lines = []

        for res in processed_results:
            # 1. 填充 JSON
            obj_data = {
                'bbox': res['bbox'],
                'depth_pred': res['distance'],
                'conf': res['conf'],
                'mode': res.get('mode', 'N/A')
            }
            save_data['objects'].append(obj_data)
            
            # 2. [新增] 生成 KITTI Line
            line = generate_kitti_line(res, p2_matrix)
            kitti_lines.append(line)

        # 写 JSON
        with open(os.path.join(save_json_dir, f"{file_id}.json"), 'w') as f:
            json.dump(save_data, f, indent=2)
            
        # [新增] 写 TXT (KITTI 格式)
        with open(os.path.join(save_txt_dir, f"{file_id}.txt"), 'w') as f:
            f.write('\n'.join(kitti_lines))

        # --- 保存可视化 ---
        if args.mode == 'mount':
            vis_img = visualizer.draw_skeleton(frame, processed_results)
        else:
            vis_img = visualizer.draw_detections(frame, processed_results)
            
        cv2.imwrite(os.path.join(save_vis_dir, f"{file_id}.jpg"), vis_img)

    print(f"\nInference Complete! Results saved to {args.output_dir}")

if __name__ == "__main__":
    main()
