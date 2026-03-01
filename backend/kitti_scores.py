import os
import numpy as np

# result_dir = "data/yolo_rsts"  # 改成你的目录
# result_dir = "data/monoloco_rsts"  # 改成你的目录
result_dir = "data/yolo26x_rsts"  # 改成你的目录

files = {
    "2D Detection": "stats_pedestrian_detection.txt",
    "BEV Detection": "stats_pedestrian_detection_ground.txt",
    "3D Detection": "stats_pedestrian_detection_3d.txt"
}

print(f"{'Metric':<20} | {'Easy':<8} | {'Moderate':<8} | {'Hard':<8}")
print("-" * 56)

for metric, filename in files.items():
    filepath = os.path.join(result_dir, filename)
    if not os.path.exists(filepath): continue
    
    # data 的 shape 是 (3, 41)
    data = np.loadtxt(filepath)
    if data.size == 0: continue

    # KITTI R40 官方公式: 忽略 index 0，取后面 40 个点的平均值
    # data[:, 1:] 截取了 index 1 到 40
    ap_scores = np.mean(data[:, 1:], axis=1) * 100
    
    e = f"{ap_scores[0]:.2f}%"
    m = f"{ap_scores[1]:.2f}%"
    h = f"{ap_scores[2]:.2f}%"
    
    print(f"{metric:<20} | {e:<8} | {m:<8} | {h:<8}")
print("-" * 56)
