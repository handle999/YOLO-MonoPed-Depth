# src/pose_utils.py
import numpy as np
import math

class PoseConverter:
    def __init__(self):
        # 人体标准解剖比例 (单位: 米)
        self.PHYSICAL_LENS = {
            'torso': 0.53,          # 躯干 (肩中心 -> 胯中心)
            'shoulder_width': 0.40, # 肩宽 (左肩 -> 右肩)
            'upper_arm': 0.30,      # 上臂 (肩 -> 肘)
            'upper_leg': 0.45,      # 大腿 (胯 -> 膝)
            'full_height': 1.70     
        }
        
    def _get_dist(self, kpts, i, j):
        return np.linalg.norm(kpts[i, :2] - kpts[j, :2])

    def _is_vertical(self, kpts, i, j, threshold_ratio=0.5):
        """判断肢体是否垂直 (防止手臂前伸)"""
        dy = abs(kpts[i, 1] - kpts[j, 1])
        length = self._get_dist(kpts, i, j)
        if length < 1e-3: return False
        return (dy / length) > threshold_ratio

    def _is_shoulder_valid(self, kpts, kp_confs, min_conf):
        """
        [核心] 判断肩宽是否可信 (排除侧身情况)
        """
        # 1. 基础置信度检查 (双肩必须都非常清晰)
        # 侧身时，远端肩膀通常会被遮挡，conf会低
        if kp_confs[5] < 0.7 or kp_confs[6] < 0.7: 
            return False

        shoulder_px = self._get_dist(kpts, 5, 6)
        
        # 2. 极小值过滤 (太窄了绝对是侧身或太远)
        if shoulder_px < 15: 
            return False

        # 3. [关键] 比例校验：肩宽 vs 上臂长
        # 如果手臂可见且垂直，我们可以用来校验侧身
        # 逻辑：正常人肩宽(0.4) > 上臂(0.3)。如果图像上肩宽 < 上臂，说明肩宽被透视压缩了(侧身)。
        
        # 左臂校验
        if kp_confs[7] > min_conf and self._is_vertical(kpts, 5, 7):
            arm_len = self._get_dist(kpts, 5, 7)
            if shoulder_px < arm_len * 0.9: # 0.9 是宽松系数
                return False # 侧身了，肩膀变窄了
        
        # 右臂校验
        if kp_confs[8] > min_conf and self._is_vertical(kpts, 6, 8):
            arm_len = self._get_dist(kpts, 6, 8)
            if shoulder_px < arm_len * 0.9:
                return False 

        # 4. [可选] 比例校验：肩宽 vs 头部 (如果有耳朵)
        # 耳朵(3,4)的间距通常是 0.15m 左右。肩宽是 0.4m。
        # 如果 肩宽 < 1.5倍耳距，说明侧身严重
        if kp_confs[3] > min_conf and kp_confs[4] > min_conf:
            ear_dist = self._get_dist(kpts, 3, 4)
            if shoulder_px < ear_dist * 2.0:
                return False

        return True

    def get_best_reference_length(self, keypoints, min_conf=0.5):
        """
        智能选择最佳测距参考段
        """
        kpts = np.array(keypoints)
        kp_confs = kpts[:, 2]
        
        # ========================================================
        # 1. 第一梯队：躯干 (Torso) - 最稳定 (侧身/正对均可)
        # ========================================================
        # 躯干长度(垂直方向)受侧身影响最小，受俯仰角影响最大(但可修正)
        high_conf = max(min_conf, 0.6) 
        
        # 1.1 双侧
        if np.all(kp_confs[[5, 6, 11, 12]] > high_conf):
            shoulder_center = (kpts[5, :2] + kpts[6, :2]) / 2
            hip_center = (kpts[11, :2] + kpts[12, :2]) / 2
            return np.linalg.norm(shoulder_center - hip_center), self.PHYSICAL_LENS['torso'], "Torso_Full"

        # 1.2 单侧 (完美解决侧身问题)
        if kp_confs[5] > high_conf and kp_confs[11] > high_conf:
            return self._get_dist(kpts, 5, 11), self.PHYSICAL_LENS['torso'], "Torso_Left"
        if kp_confs[6] > high_conf and kp_confs[12] > high_conf:
            return self._get_dist(kpts, 6, 12), self.PHYSICAL_LENS['torso'], "Torso_Right"

        # ========================================================
        # 2. 第二梯队：肩宽 (Shoulders) - 需校验朝向
        # ========================================================
        # 只有在无法使用躯干(例如只有半身照)，且确定正对时才使用
        if self._is_shoulder_valid(kpts, kp_confs, min_conf):
            return self._get_dist(kpts, 5, 6), self.PHYSICAL_LENS['shoulder_width'], "Shoulders"

        # ========================================================
        # 3. 第三梯队：大腿 (Upper Leg)
        # ========================================================
        # 必须是垂直站立
        if kp_confs[11] > min_conf and kp_confs[13] > min_conf:
             if self._is_vertical(kpts, 11, 13): 
                return self._get_dist(kpts, 11, 13), self.PHYSICAL_LENS['upper_leg'], "Leg_Left"
        if kp_confs[12] > min_conf and kp_confs[14] > min_conf:
             if self._is_vertical(kpts, 12, 14):
                return self._get_dist(kpts, 12, 14), self.PHYSICAL_LENS['upper_leg'], "Leg_Right"

        # ========================================================
        # 4. 第四梯队：上臂 (Upper Arm)
        # ========================================================
        # 必须垂直
        if kp_confs[5] > min_conf and kp_confs[7] > min_conf:
            if self._is_vertical(kpts, 5, 7, threshold_ratio=0.85): # 阈值更严，防止微弯
                return self._get_dist(kpts, 5, 7), self.PHYSICAL_LENS['upper_arm'], "Arm_Left"
                
        if kp_confs[6] > min_conf and kp_confs[8] > min_conf:
            if self._is_vertical(kpts, 6, 8, threshold_ratio=0.85):
                return self._get_dist(kpts, 6, 8), self.PHYSICAL_LENS['upper_arm'], "Arm_Right"

        return None, None, "None"
    