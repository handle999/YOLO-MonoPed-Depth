import numpy as np
import math
from geopy.distance import geodesic
from geopy.point import Point

class GeoLocalizer:
    def __init__(self, camera_config):
        """
        初始化定位器
        camera_config: 字典，包含 height, pitch, yaw, gps, intrinsics 等
        """
        self.config = camera_config
        self.earth_radius = 6371000  # 地球半径 (米)

    def pixel_to_location_flat(self, idx, conf, bbox, image_shape):
        """
        平地，cam_h绝对有效，不受pitch影响
        核心函数：像素框 -> 经纬度
        bbox: [x1, y1, x2, y2]
        image_shape: (height, width)
        """
        # 1. 解析相机参数
        cam_h = self.config['height']                       # 相机离地高度 (米)
        pitch = math.radians(self.config['pose']['pitch'])  # 俯仰角 (弧度)
        yaw = self.config['pose']['yaw']                    # 偏航角 (度)
        # roll = self.config['pose']['roll']                  # 如果算法以后需要修正倾斜，在这里读
        
        # 2. 解析内参 (支持 组合1: 物理参数流)
        f_mm = self.config['hardware']['focal_length_mm']
        sensor_w_mm = self.config['hardware']['sensor_width_mm']
        img_h, img_w = image_shape
        # [新增] 安全获取畸变系数 (可选参数，默认为空列表)
        dist_coeffs = self.config.get('distortion')
        if dist_coeffs is None:
            dist_coeffs = []
        
        # 计算像素焦距 fx
        # fx = f_mm * (img_w / sensor_w_mm)
        # 为了防止除以0，加个安全校验
        if sensor_w_mm <= 0: return None
        fx = f_mm * (img_w / sensor_w_mm)
        fy = fx # 假设像素是正方形

        cx, cy = img_w / 2, img_h / 2

        # 3. 获取目标接地点 (脚底中心)
        x1, y1, x2, y2 = bbox
        u = (x1 + x2) / 2
        v = y2  # 取脚底
        
        # 4. 计算垂直视角偏差 (Alpha & Beta)
        # alpha_v: 垂直方向偏离光轴的角度
        alpha_v = math.atan((v - cy) / fy)
        # alpha_h: 水平方向偏离光轴的角度
        angle_h_rad = math.atan((u - cx) / fx)
        angle_h_deg = math.degrees(angle_h_rad)

        # 5. 计算直线距离 (Depth)
        # 公式: D = H / tan(pitch + alpha)
        # 注意: 这里的 pitch 也就是相机下俯角。通常 pitch 是负值。
        # 实际夹角 = abs(pitch) + alpha (如果脚底在图像下方)
        # 简化模型：视线与地面的夹角 phi
        phi = -pitch + alpha_v # 假设 pitch 为负(向下), alpha 为正(图像下半部分)
        
        if phi <= 0.05: return None # 视线向上，无法算地平面距离

        ground_distance = cam_h / math.tan(phi)

        # 6. 统计法计算 "距离范围" (基于身高 1.6-1.8m)
        h_pixel = y2 - y1
        if h_pixel <= 0: h_pixel = 1
        
        # [修正1] 投影补偿: 人是竖直的，但相机是斜着看的。
        # 人在成像平面上的投影高度会缩水，大约缩水比例为 cos(phi)
        # 恢复真实投影高度: h_pixel_corrected = h_pixel / cos(phi)
        # 或者直接在公式里乘: D = (f * H * cos(phi)) / h
        projection_factor = math.cos(phi)

        # 原始光学估算 (Raw Optical Estimate)
        # 这就是你算出 16m 左右的那个值，通常因为内参不准而偏差很大
        opt_dist_min_raw = (fy * 1.6 * projection_factor) / h_pixel
        opt_dist_max_raw = (fy * 1.8 * projection_factor) / h_pixel
        
        # [修正2] 几何锚定 (Geometric Anchoring) - 关键工程Trick
        # 既然我们知道人肯定在 8.37m (由几何算出)，
        # 那么 16m 这个值肯定是错的（说明 focal_length 参数给大了，或者图片被裁切过）。
        # 我们只取 1.6-1.8m 这个"相对比例" (约12%的波动)，把它应用到 8.37m 上。
        
        # 计算光学估算的平均值
        opt_avg = (opt_dist_min_raw + opt_dist_max_raw) / 2
        
        # 计算偏差比例 (Scale Factor)
        # 例如: 几何算出来8m, 光学算出来16m, 比例就是 0.5
        if opt_avg > 0:
            scale_factor = ground_distance / opt_avg
        else:
            scale_factor = 1.0
            
        # 强制将范围拉回到几何距离附近，但保留身高的不确定性比例
        dist_min = opt_dist_min_raw * scale_factor
        dist_max = opt_dist_max_raw * scale_factor

        # 7. 计算目标的绝对地理方位角 (Bearing)
        target_bearing = (yaw + angle_h_deg) % 360

        # 8. 推算经纬度
        camera_gps = Point(self.config['gps']['lat'], self.config['gps']['lng'])
        target_gps = geodesic(meters=ground_distance).destination(point=camera_gps, bearing=target_bearing)

        # print(f"目标[{idx+1}]: 距离约 {ground_distance:.2f} 米, 置信度 {conf:.2f}, 距离范围 ({dist_min:.2f} ~ {dist_max:.2f}) 米, 方位角 {target_bearing:.1f}°")
        # 返回 main.py 和 Visualizer 所需的所有字段
        return {
            "target_id": idx+1,
            "lat": target_gps.latitude,
            "lng": target_gps.longitude,
            "distance": ground_distance,      # 用于 main.py 打印
            "dist_range": (dist_min, dist_max), # 光学法算出的"范围"
            "conf": conf,                     # [新增] 返回检测置信度，供 main.py 打印和前端展示
            "bearing": target_bearing,
            "relative_angle": angle_h_deg,    # [重要] 用于画雷达图 (相对于相机的左右偏差)
            "bbox": bbox                      # [重要] 用于画检测框
        }
    
    def pixel_to_location_mount(self, idx, conf, bbox, image_shape, keypoints=None):
        """
        山地版核心函数：光学测距 -> 推算经纬度 & 目标海拔
        [新增参数] keypoints: (可选) pose辅助，关键点列表，形状通常为 (17, 3) -> [x, y, conf]
        """
        # 1. 解析参数
        # 注意：在山地，cam_h (相对地面高度) 失去了意义，我们需要的是 相机绝对海拔 (Alt)
        cam_abs_alt = self.config['gps']['alt'] 
        pitch = math.radians(self.config['pose']['pitch'])  # 俯仰角 (弧度)
        yaw = self.config['pose']['yaw']                    # 偏航角 (度)
        # roll = self.config['pose']['roll']                  # 如果算法以后需要修正倾斜，在这里读
        
        f_mm = self.config['hardware']['focal_length_mm']
        sensor_w_mm = self.config['hardware']['sensor_width_mm']
        dist_coeffs = self.config.get('distortion', [])     # 安全获取畸变系数
        img_h, img_w = image_shape
        
        if sensor_w_mm <= 0: return None
        fx = f_mm * (img_w / sensor_w_mm)
        fy = fx 
        cx, cy = img_w / 2, img_h / 2

        x1, y1, x2, y2 = bbox
        u = (x1 + x2) / 2
        v = y2 

        # 2. 计算射线角度
        # alpha_v: 视线相对于相机光轴的垂直夹角
        alpha_v = math.atan((v - cy) / fy)
        # angle_h: 视线相对于相机光轴的水平夹角
        angle_h_rad = math.atan((u - cx) / fx)
        angle_h_deg = math.degrees(angle_h_rad)

        # phi: 视线相对于水平面的总俯仰角 (向下为正)
        # 假设 pitch 是 -15度 (向下)，alpha_v 是正数 (脚在图像下方)
        # 视线角度 = 绝对值(pitch) + alpha
        # 这里的符号需要根据你的 IMU 定义仔细校准。通常：
        # total_depression_angle = -pitch + alpha_v
        total_depression_angle = -pitch + alpha_v

        # 3. [核心改变] 光学测距 (Stadiametric Ranging)，智能测距策略 (Skeleton vs BBox)
        # 默认参数 (BBox 模式)
        ref_pixel_len = y2 - y1       # 像素高度
        if ref_pixel_len <= 0: ref_pixel_len = 1
        ref_physical_len = 1.7        # 物理身高 (假设站立)
        mode = "BBox"                 # 记录测距模式

        # 尝试使用骨骼测距 (Torso-based)
        if keypoints is not None and len(keypoints) >= 12:
            # COCO Keypoints: 
            # 5: 左肩, 6: 右肩, 11: 左胯, 12: 右胯
            # keypoints[i] = [x, y, conf]
            
            # 提取关键点
            kp_l_sh = keypoints[5]
            kp_r_sh = keypoints[6]
            kp_l_hip = keypoints[11]
            kp_r_hip = keypoints[12]
            
            # 检查置信度 (例如 > 0.5 才算可见)
            min_conf = 0.5
            if (kp_l_sh[2] > min_conf and kp_r_sh[2] > min_conf and 
                kp_l_hip[2] > min_conf and kp_r_hip[2] > min_conf):
                
                # 计算躯干中心点
                shoulder_center_y = (kp_l_sh[1] + kp_r_sh[1]) / 2
                hip_center_y = (kp_l_hip[1] + kp_r_hip[1]) / 2
                
                # 计算躯干像素长度 (垂直投影长度，更抗侧身干扰)
                torso_pixel_h = abs(hip_center_y - shoulder_center_y)
                
                if torso_pixel_h > 10: # 防止过小导致除零爆炸
                    ref_pixel_len = torso_pixel_h
                    ref_physical_len = 0.53 # 成年人平均躯干长度 (约 53cm)
                    mode = "Skeleton"
        
        # 投影修正 (通用的 Stadiametric Ranging 公式)
        # D_slant = (f * H_real * cos(total_angle)) / h_pixel
        proj_factor = math.cos(total_depression_angle)
        slant_distance = (fy * ref_physical_len * proj_factor) / ref_pixel_len

        # 4. 分解向量 (3D Ray Casting)
        # 水平投影距离 (用于算经纬度)
        horizontal_distance = slant_distance * math.cos(total_depression_angle)
        
        # 垂直落差 (用于算海拔)
        # drop_height = slant_distance * sin(angle)
        vertical_drop = slant_distance * math.sin(total_depression_angle)
        
        # 目标绝对海拔
        target_alt = cam_abs_alt - vertical_drop

        # 5. 计算范围 (基于身高 1.6-1.8)
        # 因为现在距离完全依赖身高假设，所以误差范围就是身高的比例范围
        dist_min = horizontal_distance * (1.6 / 1.7)
        dist_max = horizontal_distance * (1.8 / 1.7)

        # 6. 推算经纬度
        target_bearing = (yaw + angle_h_deg) % 360
        camera_gps = Point(self.config['gps']['lat'], self.config['gps']['lng'])
        target_gps = geodesic(meters=horizontal_distance).destination(point=camera_gps, bearing=target_bearing)

        # print(f"目标[{idx+1}]: 山地模式{mode}, 水平距离 {horizontal_distance:.2f}m, 置信度{conf:.2f}, "
            #   f"像素高度 {ref_pixel_len:.2f}, 直线距离 {slant_distance:.2f}m, 目标海拔 {target_alt:.2f}m (相机海拔 {cam_abs_alt:.2f}m)")

        return {
            "target_id": idx+1,
            "lat": target_gps.latitude,
            "lng": target_gps.longitude,
            "alt": target_alt,                      # [新增] 返回算出来的目标海拔
            "distance": horizontal_distance,        # 注意：这里返回的是水平投影距离，用于地图绘制
            "dist_range": (dist_min, dist_max),
            "conf": conf,                           # [新增] 返回检测置信度，供 main.py 打印和前端展示
            "bearing": target_bearing,
            "relative_angle": angle_h_deg,
            "bbox": bbox,
            "keypoints": keypoints,                 # [新增] 返回关键点数据，方便前端展示或调试
            "mode": mode                            # [新增] 返回测距模式，方便前端或日志展示
        }
    