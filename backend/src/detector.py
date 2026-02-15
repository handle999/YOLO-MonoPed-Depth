import cv2
import numpy as np
from ultralytics import YOLO

class PersonDetector:
    def __init__(self, det_model_path='models/Detect/yolo26l.pt', pose_model_path=None):
        """
        初始化检测器
        :param det_model_path: 检测模型路径 (必填)
        :param pose_model_path: 姿态模型路径 (可选，传入则加载)
        """
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
        # --- [修复核心] 兼容性处理：支持传入路径 str ---
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
        det_results = self.det_model(image, classes=[0], conf=0.2, verbose=False)
        
        detections = []
        
        for r in det_results:
            boxes = r.boxes
            for box in boxes:
                # 1. 获取基础 BBox
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                conf = float(box.conf[0])
                keypoints = None # 默认为空

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
                    
                    # D. 姿态推理 (Inference on Crop)
                    if person_crop.size > 0:            # , verbose=False 关闭显示
                        pose_res = self.pose_model(person_crop, conf=0.2, verbose=False)
                        
                        # E. 提取关键点并还原坐标
                        if len(pose_res) > 0 and pose_res[0].keypoints is not None and len(pose_res[0].keypoints) > 0:
                            # 取 crop 中置信度最高的那个人
                            # shape: (17, 3) -> [x, y, visible]
                            kpts_local = pose_res[0].keypoints.data[0].cpu().numpy()
                            # [新增] 计算骨架平均置信度 (只算可见点)
                            valid_kpts = kpts_local[kpts_local[:, 2] > 0.5] # 筛选出可见点
                            if len(valid_kpts) > 0:
                                avg_pose_conf = valid_kpts[:, 2].mean()
                            else:
                                avg_pose_conf = 0.0
                            
                            kpts_global = []
                            for kp in kpts_local:
                                # 局部坐标 -> 全局坐标
                                gx = kp[0] + crop_x1
                                gy = kp[1] + crop_y1
                                v = kp[2]
                                kpts_global.append([gx, gy, v])
                            
                            keypoints = kpts_global
                
                # --- [修正] 打印要放在计算之后 ---
                if use_pose:
                    status = "✅ Skeleton Found" if keypoints else "❌ Skeleton Missed"
                    # print(f"   Target Box [{x1},{y1}]: {status}, Conf={avg_pose_conf:.2f}")
                    # print(f"   Keypoints: {keypoints}")

                # --- 封装结果 ---
                detections.append({
                    'bbox': [x1, y1, x2, y2],
                    'conf': conf,
                    'keypoints': keypoints # 如果没开 pose 或没检测到，这里是 None
                })
                    
        return detections
    