# src/detector.py
import cv2
import numpy as np
import torch # [新增] 用于检查CUDA
from ultralytics import YOLO

class PersonDetector:
    def __init__(self, det_model_path='models/Detect/yolo26l.pt', pose_model_path=None, device='0'):
        """
        初始化检测器
        :param det_model_path: 检测模型路径 (必填)
        :param pose_model_path: 姿态模型路径 (可选，传入则加载)
        :param device: 运行设备, e.g. '0', 'cpu', 'mps'
        """
        # [新增] 设备检查与配置
        if device == '0' and not torch.cuda.is_available():
            print("Warning: GPU requested but not available. Falling back to CPU.")
            self.device = 'cpu'
        else:
            self.device = device

        # 1. 加载检测模型
        # print(f"Loading Detect model: {det_model_path}...")
        self.det_model = YOLO(det_model_path)
        
        # 2. 加载姿态模型 (如果提供了路径)
        self.pose_model = None
        if pose_model_path:
            # print(f"Loading Pose model: {pose_model_path}...")
            self.pose_model = YOLO(pose_model_path)
        else:
            # print("Pose model path not provided. Running in Detection-Only mode.")
            pass

    def detect(self, image, use_pose=False):
        """
        执行检测 (支持纯检测 或 检测+姿态)
        :param image: 图片路径(str) 或 cv2图像(numpy array)
        :param use_pose: 是否开启姿态估计 (需要初始化时加载了 pose_model)
        :return: list of dicts
        """
        # print(use_pose and "Running Detection + Pose Estimation..." or "Running Detection Only...")
        # 兼容性处理：支持传入路径 str 或 已加载的图像 numpy array
        if isinstance(image, str):
            # 如果是字符串，说明是路径，读取它
            img_path = image
            image = cv2.imread(img_path)
            if image is None:
                # print(f"Error: Unable to load image from path: {img_path}")
                return []
            
        # 获取图像尺寸，用于边界检查
        h_img, w_img = image.shape[:2]
        
        # --- 第一阶段：全图检测 (Detection) ---
        # classes=[0] 只检测人, conf=0.2 保证召回率,  , verbose=False关闭显示
        det_results = self.det_model(image, classes=[0], conf=0.2, verbose=False, device=self.device)
        
        detections = []
        
        # 临时存储用于 Batch Inference 的数据
        pose_candidates = [] # 存图片: [crop1, crop2, ...]
        pose_indices = []    # 存索引: [0, 2, 5...] 记录哪些 detection 需要填回 pose
        pose_offsets = []    # 存坐标偏移: [(crop_x1, crop_y1), ...]

        for r in det_results:
            boxes = r.boxes
            for box in boxes:
                # 1. 获取基础 BBox
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                conf = float(box.conf[0])
                # 先把基础信息存进去，keypoints 稍后回填
                detections.append({
                    'bbox': [x1, y1, x2, y2],
                    'conf': conf,
                    'keypoints': None 
                })

                # --- 第二阶段：姿态估计 (Pose Estimation) [可选] ---
                if use_pose and self.pose_model is not None:
                    # print("Performing pose estimation for detected person...")
                    # A. 计算 Padding (外扩 15%，防止肢体被切断)
                    w_box = x2 - x1
                    h_box = y2 - y1
                    pad_w = int(w_box * 0.15)
                    pad_h = int(h_box * 0.15)
                    
                    # B. 限制裁切坐标不超出图片范围
                    crop_x1 = max(0, x1 - pad_w)
                    crop_y1 = max(0, y1 - pad_h)
                    crop_x2 = min(w_img, x2 + pad_w)
                    crop_y2 = min(h_img, y2 + pad_h)
                    
                    # C. 裁切 (Crop)
                    person_crop = image[crop_y1:crop_y2, crop_x1:crop_x2]
                    
                    # D. 姿态推理 (Inference on Crop)，存入列表，等待批量处理
                    if person_crop.size > 0:
                        pose_candidates.append(person_crop)
                        pose_indices.append(len(detections) - 1) # 记录这是第几个 detection
                        pose_offsets.append((crop_x1, crop_y1))
                
        # --- 第三阶段：Pose Batch Inference (批量推理加速) ---
        if len(pose_candidates) > 0:
            # 这里的 pose_candidates 是一个 list of numpy arrays
            # YOLOv8 支持直接传入 list 进行 batch 处理，并利用 GPU 加速
            batch_results = self.pose_model(pose_candidates, conf=0.2, verbose=False, device=self.device)
            
            # --- 第四阶段：结果回填 ---
            for idx, result in enumerate(batch_results):
                # 找到当前结果对应的 detection 索引
                target_det_idx = pose_indices[idx]
                offset_x, offset_y = pose_offsets[idx]
                
                # 提取关键点并还原坐标
                if result.keypoints is not None and result.keypoints.data.shape[1] > 0:
                    kpts_local = result.keypoints.data[0].cpu().numpy()
                    
                    # 计算平均置信度 (仅用于调试打印，可选)
                    # valid_kpts = kpts_local[kpts_local[:, 2] > 0.5]
                    # avg_pose_conf = valid_kpts[:, 2].mean() if len(valid_kpts) > 0 else 0.0
                    
                    kpts_global = []
                    for kp in kpts_local:
                        # 局部坐标 -> 全局坐标
                        gx = kp[0] + offset_x
                        gy = kp[1] + offset_y
                        v = kp[2]
                        kpts_global.append([gx, gy, v])
                    
                    # [修改] 回填到 detections 列表里
                    detections[target_det_idx]['keypoints'] = kpts_global
                    
        return detections
    