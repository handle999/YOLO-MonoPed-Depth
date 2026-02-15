# kitti_infer.py
import os
import cv2
import json
import time
import argparse
import numpy as np
from tqdm import tqdm
from src.detector import PersonDetector
from src.geolocalizer import GeoLocalizer
from src.visualizer import Visualizer

# KITTI 车载相机高度 (固定值)
KITTI_CAM_HEIGHT = 1.65 

def parse_calib(calib_path):
    """从 P2 矩阵提取焦距 fx"""
    if not os.path.exists(calib_path): return None
    with open(calib_path, 'r') as f:
        for line in f.readlines():
            if line.startswith('P2:'):
                # P2 是 3x4 矩阵，P2[0,0] 即为 fx (像素焦距)
                return float(line.split()[1])
    return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--kitti_root', type=str, default='data/kitti', help='数据根目录')
    parser.add_argument('--output_dir', type=str, default='data/kitti_rsts', help='结果保存目录')
    parser.add_argument('--mode', type=str, default='mount', choices=['flat', 'mount'], help='测距模式')
    parser.add_argument('--limit', type=int, default=0, help='测试数量限制')
    args = parser.parse_args()

    # 1. 目录准备
    base_img_dir = os.path.join(args.kitti_root, 'data_object_image_2', 'training', 'image_2')
    base_calib_dir = os.path.join(args.kitti_root, 'data_object_calib', 'training', 'calib')
    
    save_json_dir = os.path.join(args.output_dir, 'data')
    save_vis_dir = os.path.join(args.output_dir, 'vis')
    os.makedirs(save_json_dir, exist_ok=True)
    os.makedirs(save_vis_dir, exist_ok=True)

    # 2. 初始化模型
    print("Loading models...")
    # 确保你的 detector.py 已更新支持 print 时间
    detector = PersonDetector('./models/Detect/yolo26l.pt', './models/Pose/yolo11x-pose.pt')
    visualizer = Visualizer()

    # ================= [新增] 1. GPU 冷启动预热 (Warmup) =================
    print("🔥 Warming up GPU...")
    dummy_img = np.zeros((375, 1242, 3), dtype=np.uint8)
    # 强制运行一次 Detect 和 Pose
    detector.detect(dummy_img, use_pose=False) 
    if detector.pose_model:
        detector.pose_model(dummy_img, verbose=False)
    print("✅ Warmup complete. Starting benchmark...")
    # ====================================================================

    img_files = sorted([f for f in os.listdir(base_img_dir) if f.endswith('.png')])
    if args.limit > 0: img_files = img_files[:args.limit]

    print(f"Start Inference on {len(img_files)} images...")
    
    # 3. 批量推理
    for img_file in tqdm(img_files):
        file_id = os.path.splitext(img_file)[0]
        
        # A. 读图
        img_path = os.path.join(base_img_dir, img_file)
        frame = cv2.imread(img_path)
        h, w = frame.shape[:2]

        # B. 读 Calib 获取焦距
        calib_path = os.path.join(base_calib_dir, f"{file_id}.txt")
        fx = parse_calib(calib_path)
        if fx is None: continue

        # C. 动态配置 Geolocalizer
        # 技巧: 设 sensor_width_mm = w, focal_length_mm = fx
        # 这样内部计算: f_pix = fx * (w/w) = fx，完美对齐
        config = {
            'gps': {'lat': 0, 'lng': 0, 'alt': 0},
            'height': KITTI_CAM_HEIGHT,
            'pose': {'pitch': 0, 'yaw': 0, 'roll': 0}, # 车载相机 pitch 近似 0
            'hardware': {'focal_length_mm': fx, 'sensor_width_mm': w}
        }
        localizer = GeoLocalizer(config)

        # D. 推理 (计时)
        t_start_total = time.time()
        
        # A. Detection 阶段
        t_det_start = time.time()
        detections = detector.detect(frame, use_pose=False) # 只跑检测
        t_det_end = time.time()
        
        # B. Pose 阶段 (手动复现 detector 内部逻辑以实现独立计时)
        t_pose_start = time.time()
        if args.mode == 'mount':
            for det in detections:
                bbox = det['bbox']
                x1, y1, x2, y2 = bbox
                
                # 1. Padding & Crop (逻辑需与 Detector 保持一致)
                w_box, h_box = x2 - x1, y2 - y1
                pad_w, pad_h = int(w_box * 0.15), int(h_box * 0.15)
                crop_x1 = max(0, x1 - pad_w)
                crop_y1 = max(0, y1 - pad_h)
                crop_x2 = min(w, x2 + pad_w)
                crop_y2 = min(h, y2 + pad_h)
                
                person_crop = frame[crop_y1:crop_y2, crop_x1:crop_x2]
                
                # 2. Pose Inference
                if person_crop.size > 0:
                    pose_res = detector.pose_model(person_crop, verbose=False, conf=0.5)
                    
                    # 3. Coordinate Mapping
                    if (len(pose_res) > 0 and 
                        pose_res[0].keypoints is not None and 
                        pose_res[0].keypoints.data.shape[1] > 0):
                        
                        kpts_local = pose_res[0].keypoints.data[0].cpu().numpy()
                        kpts_global = []
                        for kp in kpts_local:
                            gx = kp[0] + crop_x1
                            gy = kp[1] + crop_y1
                            v = kp[2]
                            kpts_global.append([gx, gy, v])
                        
                        det['keypoints'] = kpts_global # 注入回 det 字典
        
        t_pose_end = time.time()

        # C. Localization 阶段
        processed_results = []
        for det in detections:
            # ... (调用 localizer 的逻辑保持不变) ...
            # ... (注意：这里直接用 det['keypoints'] 即可) ...
            
            # 为了完整性展示这部分修改：
            loc_res = None
            kpts = det.get('keypoints')
            if args.mode == 'mount':
                loc_res = localizer.pixel_to_location_mount(0, det['conf'], det['bbox'], (h,w), kpts)
            else:
                loc_res = localizer.pixel_to_location_flat(0, det['conf'], det['bbox'], (h,w))
            
            if loc_res:
                loc_res['target_id'] = f"P"
                loc_res['conf'] = det['conf']
                if kpts: loc_res['keypoints'] = kpts
                processed_results.append(loc_res)

        t_end_total = time.time()

        # E. 保存结果 (JSON)
        # 构造要保存的数据结构
        save_data = {
            'file_id': file_id,
            'image_size': [w, h],
            'time_stats': {
                'total_ms': (t_end_total - t_start_total) * 1000,
                'det_ms': (t_det_end - t_det_start) * 1000,
                'pose_ms': (t_pose_end - t_pose_start) * 1000, # 纯 Pose 推理耗时
                'post_ms': (t_end_total - t_pose_end) * 1000   # 测距算法耗时
            },
            'objects': []
        }

        for res in processed_results:
            # 只保存必要的评测字段
            obj_data = {
                'bbox': res['bbox'], # [x1, y1, x2, y2]
                'depth_pred': res['distance'],
                'conf': res['conf'],
                'mode': res.get('mode', 'N/A')
            }
            save_data['objects'].append(obj_data)

        with open(os.path.join(save_json_dir, f"{file_id}.json"), 'w') as f:
            json.dump(save_data, f, indent=2)

        # F. 保存可视化 (Mount模式保存 Skeleton 图)
        if args.mode == 'mount':
            vis_img = visualizer.draw_skeleton(frame, processed_results)
        else:
            vis_img = visualizer.draw_detections(frame, processed_results)
            
        cv2.imwrite(os.path.join(save_vis_dir, f"{file_id}.jpg"), vis_img)

    print(f"\nInference Complete! Results saved to {args.output_dir}")

if __name__ == "__main__":
    main()
