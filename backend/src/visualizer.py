# src/visualizer.py
import cv2
import numpy as np
import math

class Visualizer:
    def __init__(self):
        # 雷达图配置
        self.radar_size = 600       # 雷达图画布大小 600x600
        self.radar_center = (300, 550) # 相机在雷达图上的位置 (底部居中)
        self.scale = 10             # 比例尺: 1米 = 10像素 (这意味着能画出约50米远的人)
        self.bg_color = (20, 20, 20) # 背景色 (深灰)
        self.text_color = (0, 255, 0)

        # --- 骨架配置 (COCO 17 Keypoints) ---
        self.skeleton_links = [
            (5, 7), (7, 9), (6, 8), (8, 10),      # 左右臂
            (11, 13), (13, 15), (12, 14), (14, 16), # 左右腿
            (5, 6), (11, 12), (5, 11), (6, 12)    # 躯干
        ]
        self.kpt_color = (0, 255, 255)  # 黄色点
        self.limb_color = (255, 0, 255) # 紫色线s
    
    def draw_detections(self, image, results):
        """
        在原图上画框和距离信息
        image: 原始图片 (cv2格式)
        results: 包含 'bbox', 'distance' 的结果列表
        """
        annotated_img = image.copy()
        
        for res in results:
            # 解析数据
            if 'bbox' not in res: continue
            tid = res.get('target_id', 'Unknown') # 获取ID，如果没有则用 'Unknown'
            x1, y1, x2, y2 = map(int, res['bbox'])
            dist = res['distance']
            conf = res.get('conf', 0)
            
            # 1. 画框 (绿色)
            cv2.rectangle(annotated_img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # 2. 写文字 (id + 距离 + 置信度)
            # label = f"{dist:.1f}"
            label = f"{tid}: {dist:.1f}m ({conf:.2f})"
            # 文字背景条 (为了看得更清楚)
            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
            cv2.rectangle(annotated_img, (x1, y1 - 20), (x1 + w, y1), (0, 255, 0), -1)
            cv2.putText(annotated_img, label, (x1, y1 - 5), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
            
        return annotated_img

    def draw_skeleton(self, image, results):
        """
        骨架结果：先调用 draw_detections 画框，再叠加 Pose 骨架
        """
        # 1. 先获取带框的图 (复用上面的函数)
        annotated_img = self.draw_detections(image, results)
        
        # 2. 叠加骨架
        for res in results:
            kpts = res.get('keypoints')
            # 如果没有骨架数据，跳过
            if kpts is None or len(kpts) == 0:
                # print(f"Warning: 目标 {res.get('target_id', 'Unknown')} 没有骨架数据，无法画骨架")
                continue
                
            # A. 画连线 (Limbs)
            for i, j in self.skeleton_links:
                if i >= len(kpts) or j >= len(kpts): continue
                kp1, kp2 = kpts[i], kpts[j]
                
                # 检查可见性
                if kp1[2] > 0.5 and kp2[2] > 0.5:
                    pt1 = (int(kp1[0]), int(kp1[1]))
                    pt2 = (int(kp2[0]), int(kp2[1]))
                    cv2.line(annotated_img, pt1, pt2, self.limb_color, 2)
            
            # B. 画关键点 (Points)
            for kp in kpts:
                x, y, conf = int(kp[0]), int(kp[1]), kp[2]
                if conf > 0.5:
                    cv2.circle(annotated_img, (x, y), 3, self.kpt_color, -1)
                    
        return annotated_img
    
    def draw_radar_map(self, results, max_dist=100):
        """
        绘制俯视雷达图
        results: 包含 'distance', 'bearing', 'cam_yaw' 的结果
        max_dist: 雷达图最大显示距离 (用于画圈)
        """
        # 1. 创建黑色画布
        radar_img = np.full((self.radar_size, self.radar_size, 3), self.bg_color, dtype=np.uint8)
        # 创建一个 Overlay 层用于画半透明图形
        overlay = radar_img.copy()
        cx, cy = self.radar_center
        
        # 2. 画距离刻度圈 (5m, 10m, 15m...)
        for d in range(5, max_dist + 1, 5):
            radius = int(d * self.scale)
            cv2.circle(radar_img, (cx, cy), radius, (50, 50, 50), 1)
            cv2.putText(radar_img, f"{d}m", (cx + 5, cy - radius + 5), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1)

        # 3. 画相机位置 (红色三角形)
        pts = np.array([[cx, cy], [cx-10, cy+15], [cx+10, cy+15]], np.int32)
        cv2.fillPoly(radar_img, [pts], (0, 0, 255)) # 红色代表相机

        # 4. 画扇形可视区域 (FOV) - 假设 FOV 120度
        # 这里为了简单，画两条线表示左右边界
        fov = 90
        length = 800
        angle_left = math.radians(90 + fov/2)
        angle_right = math.radians(90 - fov/2)
        
        x_l = int(cx + length * math.cos(angle_left))
        y_l = int(cy - length * math.sin(angle_left))
        x_r = int(cx + length * math.cos(angle_right))
        y_r = int(cy - length * math.sin(angle_right))
        
        cv2.line(radar_img, (cx, cy), (x_l, y_l), (50, 50, 50), 1) # 左边界
        cv2.line(radar_img, (cx, cy), (x_r, y_r), (50, 50, 50), 1) # 右边界

        # 5. 画目标点及范围
        for res in results:
            dist = res.get('distance', 0)
            tid = res.get('target_id', 'Unknown')
            # 我们需要的是相对于相机的角度，而不是地理 bearing
            # 在 geolocalizer 中我们计算过 alpha_h (像素偏移角)
            # 为了方便，这里我们假设传入的结果里包含 'relative_angle' (度)
            # 如果没有，可以通过 (bearing - cam_yaw) 计算
            
            rel_angle_deg = res.get('relative_angle', 0) 

            # 获取范围，如果没有则默认就是 dist
            d_min, d_max = res.get('dist_range', (dist, dist))
            
            # 转换为画布坐标
            # 数学坐标系：0度向右，90度向上。
            # 我们的视角：相机朝前是90度。
            # 如果 rel_angle 是负数(偏左)，则角度是 90 + abs(angle)
            # 如果 rel_angle 是正数(偏右)，则角度是 90 - angle
            # 注意：这里的 rel_angle 来源于像素偏差，左边通常是 x 小，角度算出来负
            
            # 为了让显示更像雷达，我们给角度也加一点宽度 (例如 +/- 3度)
            angle_half_width = 3.0 
            
            # 计算基础绘图角度 (90度 - 相对角度)
            # 数学坐标系中，90度是正上方。如果目标偏左(rel_angle < 0)，则角度应 > 90
            base_draw_angle = 90 - rel_angle_deg
            
            # 梯形的四个角点：[近左, 近右, 远右, 远左]
            # 这样顺序是为了组成一个闭合多边形
            poly_pts = []
            
            # 定义四个关键点 (距离, 角度偏移)
            # 1. 近端 (d_min)
            corners = [
                (d_min, base_draw_angle + angle_half_width), # 近左
                (d_min, base_draw_angle - angle_half_width), # 近右
                (d_max, base_draw_angle - angle_half_width), # 远右
                (d_max, base_draw_angle + angle_half_width)  # 远左
            ]
            
            for d, ang in corners:
                rad = math.radians(ang)
                r = d * self.scale
                # 极坐标转笛卡尔坐标
                px = int(cx + r * math.cos(rad))
                py = int(cy - r * math.sin(rad))
                poly_pts.append([px, py])
            
            poly_pts = np.array([poly_pts], np.int32)
            
            # A. 在 overlay 层画半透明绿色块 (表示不确定范围)
            cv2.fillPoly(overlay, poly_pts, (0, 100, 0)) 
            
            # B. 在原图层画亮绿色边框
            cv2.polylines(radar_img, poly_pts, True, (0, 180, 0), 1)

            # --- 绘制中心点 (几何计算的最准点) ---
            center_rad = math.radians(base_draw_angle)
            r_center = dist * self.scale
            cx_pt = int(cx + r_center * math.cos(center_rad))
            cy_pt = int(cy - r_center * math.sin(center_rad))
            
            # 画一条线连过去
            cv2.line(radar_img, (cx, cy), (cx_pt, cy_pt), (100, 100, 100), 1)
            # 画白色实心点
            cv2.circle(radar_img, (cx_pt, cy_pt), 4, (255, 255, 255), -1)
            
            # 标id / 距离文字
            label = f"{tid}"
            cv2.putText(radar_img, label, (cx_pt + 8, cy_pt), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # 6. 融合图层 (实现半透明效果)
        alpha = 0.4 # 透明度 40%
        cv2.addWeighted(overlay, alpha, radar_img, 1 - alpha, 0, radar_img)

        return radar_img
    