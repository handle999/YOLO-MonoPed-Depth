# kitti_eval.py
import os
import json
import argparse
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from tqdm import tqdm

NUM_SEPARATOR = 80 # 表格分隔线长度

def get_kitti_difficulty(height, occlusion, truncation):
    """
    根据 KITTI 官方定义判断难度
    Occlusion: 0=可见, 1=部分, 2=严重, 3=未知
    """
    diffs = []
    # Easy
    if height >= 40 and occlusion == 0 and truncation <= 0.15:
        diffs.append('Easy')
    # Moderate
    if height >= 25 and occlusion <= 1 and truncation <= 0.30:
        diffs.append('Moderate')
    # Hard
    if height >= 25 and occlusion <= 2 and truncation <= 0.50:
        diffs.append('Hard')
    return diffs

def compute_iou(box1, box2):
    """计算 IoU"""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area1 = (box1[2]-box1[0]) * (box1[3]-box1[1])
    area2 = (box2[2]-box2[0]) * (box2[3]-box2[1])
    return inter / (area1 + area2 - inter + 1e-6)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--kitti_root', default='data/kitti')
    parser.add_argument('--result_dir', default='data/kitti_rsts/data', help='inference生成的json目录')
    args = parser.parse_args()

    label_dir = os.path.join(args.kitti_root, 'data_object_label_2', 'training', 'label_2')
    
    # 统计容器
    stats = {
        'Easy': {'errs': [], 'rel_errs': [], 'count': 0},
        'Moderate': {'errs': [], 'rel_errs': [], 'count': 0},
        'Hard': {'errs': [], 'rel_errs': [], 'count': 0},
        'All': {'errs': [], 'rel_errs': [], 'count': 0}
    }
    
    time_stats = {
        'total': [],
        'det': [],
        'pose': []
    }
    all_gt_depths = []
    all_pred_depths = []

    pred_files = sorted([f for f in os.listdir(args.result_dir) if f.endswith('.json')])
    print(f"Evaluating {len(pred_files)} files...")

    for f_name in tqdm(pred_files):
        file_id = f_name.split('.')[0]
        
        # 1. 加载预测
        with open(os.path.join(args.result_dir, f_name), 'r') as f:
            pred_data = json.load(f)
        
        ts = pred_data['time_stats']
        time_stats['total'].append(ts['total_ms'])
        time_stats['det'].append(ts.get('det_ms', 0))   # 使用 .get 防止旧 json 报错
        time_stats['pose'].append(ts.get('pose_ms', 0))

        preds = pred_data['objects']

        # 2. 加载 GT
        label_path = os.path.join(label_dir, f"{file_id}.txt")
        if not os.path.exists(label_path): continue
        
        gts = []
        with open(label_path, 'r') as f:
            for line in f.readlines():
                parts = line.strip().split()
                if parts[0] == 'Pedestrian':
                    # 解析 GT 属性
                    trunc = float(parts[1])
                    occl = int(parts[2])
                    bbox = [float(parts[4]), float(parts[5]), float(parts[6]), float(parts[7])]
                    h_pixel = bbox[3] - bbox[1]
                    depth = float(parts[13])
                    
                    gts.append({
                        'bbox': bbox,
                        'depth': depth,
                        'diffs': get_kitti_difficulty(h_pixel, occl, trunc)
                    })
        
        # print(f"File {file_id}: Found {len(preds)} preds and {len(gts)} GTs") # [Debug 1]

        # 3. 匹配 (简单贪婪匹配)
        # 对于每个 GT，找到 IoU 最大的 Pred
        for gt in gts:
            best_iou = 0
            best_pred = None
            
            for pred in preds:
                iou = compute_iou(gt['bbox'], pred['bbox'])
                # print(f"   GT: {gt['bbox']} vs Pred: {pred['bbox']} => IoU: {iou:.4f}") # [Debug 2]

                if iou > 0.5 and iou > best_iou:
                    best_iou = iou
                    best_pred = pred
            
            # 只有匹配成功的才算误差
            if best_pred:
                abs_err = abs(best_pred['depth_pred'] - gt['depth'])
                rel_err = abs_err / gt['depth']
                
                # 记录所有数据用于画图
                all_gt_depths.append(gt['depth'])
                all_pred_depths.append(best_pred['depth_pred'])

                # 按难度分桶统计
                for diff in gt['diffs']:
                    stats[diff]['errs'].append(abs_err)
                    stats[diff]['rel_errs'].append(rel_err)
                    stats[diff]['count'] += 1
                
                # 总桶
                stats['All']['errs'].append(abs_err)
                stats['All']['rel_errs'].append(rel_err)
                stats['All']['count'] += 1
            else:
                # print(f"   Matching Failed for GT: {gt['bbox']}") # [Debug 3]
                pass

    # --- 4. 生成报告 (对标 MonoLoco 指标) ---
    print("\n" + "="*NUM_SEPARATOR)
    print(f"{'Difficulty':<15} | {'Count':<8} | {'ALE (m)':<10} | {'ALP (<0.5m)':<12} | {'ALP (<1m)':<10} | {'ALP (<2m)':<10}")
    print("-" * NUM_SEPARATOR)
    
    rows = []
    # 按照 MonoLoco 的习惯，通常也会看 All
    for mode in ['Easy', 'Moderate', 'Hard', 'All']:
        data = stats[mode]
        if len(data['errs']) == 0:
            print(f"{mode:<15} | 0")
            continue
            
        # ALE: 平均绝对误差 (Average Localization Error)
        ale = np.mean(data['errs'])
        
        # ALP: 定位精度 (Average Localization Precision) - 绝对阈值
        # 1. ALP < 0.5m
        alp_05m = np.mean(np.array(data['errs']) <= 0.5) * 100
        # 2. ALP < 1.0m
        alp_1m = np.mean(np.array(data['errs']) <= 1.0) * 100
        # 3. ALP < 2.0m
        alp_2m = np.mean(np.array(data['errs']) <= 2.0) * 100
        
        print(f"{mode:<15} | {data['count']:<8} | {ale:<10.3f} | {alp_05m:<12.1f}% | {alp_1m:<10.1f}% | {alp_2m:<10.1f}%")
        
        rows.append([mode, data['count'], ale, alp_05m, alp_1m, alp_2m])

    print("-" * NUM_SEPARATOR)
    
    avg_total = np.mean(time_stats['total'])
    avg_det = np.mean(time_stats['det'])
    avg_pose = np.mean(time_stats['pose'])
    
    print(f"Time Statistics (Mean):")
    print(f"  Det : {avg_det:.1f} ms")
    print(f"  Pose: {avg_pose:.1f} ms")
    print(f"  Infr: {avg_total:.1f} ms (Total per Image)")
    print(f"Average Inference Time: {np.mean(time_stats['total']):.1f} ms/img")
    print("=" * NUM_SEPARATOR)

    # --- 5. 画图分析 ---
    plt.figure(figsize=(14, 6))
    
    # 图1: GT vs Pred 散点图
    plt.subplot(1, 2, 1)
    plt.scatter(all_gt_depths, all_pred_depths, alpha=0.3, s=5, c='blue')
    plt.plot([0, 80], [0, 80], 'r--', label='Ideal')
    plt.xlabel('Ground Truth Depth (m)')
    plt.ylabel('Predicted Depth (m)')
    plt.title('Depth Correlation')
    plt.grid(True)
    plt.xlim(0, 80)
    plt.ylim(0, 80)

    # 图2: 绝对误差分布直方图 (All)
    plt.subplot(1, 2, 2)
    errs = stats['All']['errs']
    # 过滤掉极端值画图更好看
    filtered_errs = [e for e in errs if e < 10]
    plt.hist(filtered_errs, bins=50, color='orange', alpha=0.7, edgecolor='black')
    plt.xlabel('Absolute Error (m)')
    plt.ylabel('Count')
    plt.title('Error Distribution (<10m)')
    
    plt.savefig('kitti_evaluation_report.png')
    print("Chart saved to kitti_evaluation_report.png")

if __name__ == "__main__":
    main()
