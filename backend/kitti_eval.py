# kitti_eval.py
import os
import json
import argparse
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from tqdm import tqdm

# ==========================================
# Module 1: Core Math & Metrics (基础核心算法)
# ==========================================

def compute_iou(box1, box2):
    x1, y1 = max(box1[0], box2[0]), max(box1[1], box2[1])
    x2, y2 = min(box1[2], box2[2]), min(box1[3], box2[3])
    
    inter_area = max(0, x2 - x1) * max(0, y2 - y1)
    box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
    box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
    
    union_area = box1_area + box2_area - inter_area + 1e-6
    return inter_area / union_area

def calculate_ap_11point(precisions, recalls):
    ap = 0.
    for t in np.arange(0., 1.1, 0.1):
        p = np.max(precisions[recalls >= t]) if np.sum(recalls >= t) > 0 else 0
        ap += p / 11.
    return ap

def calculate_ap_40point(precisions, recalls):
    ap = 0.
    for t in np.arange(1./40., 1.0 + 1./40., 1./40.):
        p = np.max(precisions[recalls >= t]) if np.sum(recalls >= t) > 0 else 0
        ap += p / 40.
    return ap

# ==========================================
# Module 2: Data Processing (数据解析与加载)
# ==========================================

def get_kitti_difficulty(height, occlusion, truncation):
    diffs = []
    if height >= 40 and occlusion == 0 and truncation <= 0.15: diffs.append('Easy')
    if height >= 25 and occlusion <= 1 and truncation <= 0.30: diffs.append('Moderate')
    if height >= 25 and occlusion <= 2 and truncation <= 0.50: diffs.append('Hard')
    return diffs

def load_data(result_dir, label_dir, target_cls='Pedestrian'):
    predictions, ground_truths = {}, {}
    time_stats = {'total': [], 'det': [], 'pose': []}
    dataset_info = {'Easy': 0, 'Moderate': 0, 'Hard': 0, 'All': 0}
    
    pred_files = sorted([f for f in os.listdir(result_dir) if f.endswith('.json')])
    print(f"Loading data from {len(pred_files)} files...")
    
    for f_name in tqdm(pred_files):
        file_id = f_name.split('.')[0]
        
        # Load Preds
        with open(os.path.join(result_dir, f_name), 'r') as f:
            data = json.load(f)
            
        ts = data.get('time_stats', {})
        time_stats['total'].append(ts.get('total_ms', 0))
        time_stats['det'].append(ts.get('det_ms', 0))
        time_stats['pose'].append(ts.get('pose_ms', 0))
        predictions[file_id] = sorted(data['objects'], key=lambda x: x['conf'], reverse=True)
        
        # Load GTs
        label_path = os.path.join(label_dir, f"{file_id}.txt")
        gt_objs = []
        if os.path.exists(label_path):
            with open(label_path, 'r') as f:
                for line in f.readlines():
                    parts = line.strip().split()
                    if parts[0] == target_cls: 
                        bbox = [float(parts[4]), float(parts[5]), float(parts[6]), float(parts[7])]
                        h_px = bbox[3] - bbox[1]
                        diffs = get_kitti_difficulty(h_px, int(parts[2]), float(parts[1]))
                        
                        gt_objs.append({
                            'bbox': bbox, 'depth': float(parts[13]),
                            'occlusion': int(parts[2]), 'truncation': float(parts[1]),
                            'height_px': h_px, 'diffs': diffs, 'matched': False 
                        })
                        
                        dataset_info['All'] += 1
                        for d in diffs: dataset_info[d] += 1
                            
        ground_truths[file_id] = gt_objs
        
    return predictions, ground_truths, time_stats, dataset_info

# ==========================================
# Module 3: Evaluator Engine (评测计算引擎)
# ==========================================

def eval_depth_metrics(predictions, ground_truths, iou_thresh):
    stats = {k: {'errs': [], 'count': 0} for k in ['Easy', 'Moderate', 'Hard', 'All']}
    
    for file_id, preds in predictions.items():
        gts = ground_truths.get(file_id, [])
        if not gts: continue
        current_gts = [g.copy() for g in gts]
        
        for gt in current_gts:
            best_iou, best_pred = 0, None
            for pred in preds:
                iou = compute_iou(gt['bbox'], pred['bbox'])
                if iou > iou_thresh and iou > best_iou:
                    best_iou, best_pred = iou, pred
            
            if best_pred:
                err = abs(best_pred['depth_pred'] - gt['depth'])
                stats['All']['errs'].append(err)
                stats['All']['count'] += 1
                for diff in gt['diffs']:
                    stats[diff]['errs'].append(err)
                    stats[diff]['count'] += 1
                    
    return stats

def eval_detection_ap(predictions, ground_truths, difficulty_mode, iou_thresh):
    all_detections, n_gts, gt_state = [], 0, {} 
    
    # Init GT States
    for file_id, gts in ground_truths.items():
        gt_state[file_id] = []
        for gt in gts:
            is_valid_class = difficulty_mode in gt['diffs']
            if is_valid_class: n_gts += 1
            gt_state[file_id].append({'matched': False, 'bbox': gt['bbox'], 'ignore': not is_valid_class})

    # Collect and Sort Detections
    for file_id, preds in predictions.items():
        for p in preds:
            all_detections.append({'conf': p['conf'], 'file_id': file_id, 'bbox': p['bbox']})
    all_detections.sort(key=lambda x: x['conf'], reverse=True)
    
    # Calculate TP / FP
    tp, fp = np.zeros(len(all_detections)), np.zeros(len(all_detections))
    for i, det in enumerate(all_detections):
        best_iou, best_gt_idx = 0, -1
        candidates = gt_state.get(det['file_id'], [])
        
        for idx, gt in enumerate(candidates):
            iou = compute_iou(det['bbox'], gt['bbox'])
            if iou > best_iou:
                best_iou, best_gt_idx = iou, idx
                
        if best_iou >= iou_thresh:
            gt = candidates[best_gt_idx]
            if not gt['ignore']:
                if not gt['matched']: tp[i], gt['matched'] = 1, True
                else: fp[i] = 1 
        else:
            fp[i] = 1 
            
    # Calculate PR Curve & AP
    tp_sum, fp_sum = np.cumsum(tp), np.cumsum(fp)
    recalls = tp_sum / float(n_gts + 1e-6)
    precisions = tp_sum / np.maximum(tp_sum + fp_sum, 1e-6)
    
    return calculate_ap_11point(precisions, recalls) * 100, calculate_ap_40point(precisions, recalls) * 100

# ==========================================
# Module 4: Reporter & Plotter (排版展示与画图)
# ==========================================

def print_dataset_info(ds_info, num_files):
    print("\n" + "="*50)
    print(" KITTI DATASET INFO (Ground Truth)")
    print("-" * 50)
    print(f" Total Target Files : {num_files}")
    print(f" Total Pedestrians  : {ds_info['All']}")
    print(f"  - Easy            : {ds_info['Easy']}")
    print(f"  - Moderate        : {ds_info['Moderate']}")
    print(f"  - Hard            : {ds_info['Hard']}")
    print("=" * 50)

def print_evaluation_report(depth_stats, ap_stats, times, iou_thresh):
    print("\n" + "="*110)
    print(f" EVALUATION REPORT (Pedestrian, IoU={iou_thresh})")
    print("-" * 110)
    headers = ["Difficulty", "Count", "AP_R11", "AP_R40", "ALE Mean", "ALE Min", "ALE Max", "ALE Std", "ALP <0.5m", "ALP <1m", "ALP <2m"]
    print(f"{headers[0]:<12} | {headers[1]:<7} | {headers[2]:<8} | {headers[3]:<8} | {headers[4]:<10} | {headers[5]:<8} | {headers[6]:<8} | {headers[7]:<8} | {headers[8]:<9} | {headers[9]:<7} | {headers[10]:<7}")
    print("-" * 110)
    
    for mode in ['Easy', 'Moderate', 'Hard', 'All']:
        d_stat = depth_stats[mode]
        if d_stat['count'] == 0:
            print(f"{mode:<12} | {0:<7} | {'N/A':<8} | {'N/A':<8} | ...")
            continue
            
        errs = np.array(d_stat['errs'])
        ale_mean, ale_min, ale_max, ale_std = np.mean(errs), np.min(errs), np.max(errs), np.std(errs)
        alp_05, alp_10, alp_20 = np.mean(errs <= 0.5)*100, np.mean(errs <= 1.0)*100, np.mean(errs <= 2.0)*100
        
        ap11 = f"{ap_stats[mode]['R11']:.2f}" if mode in ap_stats else "-"
        ap40 = f"{ap_stats[mode]['R40']:.2f}" if mode in ap_stats else "-"
        
        print(f"{mode:<12} | {d_stat['count']:<7} | {ap11:<8} | {ap40:<8} | {ale_mean:<10.3f} | {ale_min:<8.3f} | {ale_max:<8.3f} | {ale_std:<8.3f} | {alp_05:<8.1f}% | {alp_10:<6.1f}% | {alp_20:<6.1f}%")

    print("-" * 110)
    
    # Print Time Stats
    print(f"Time Statistics (per image):")
    for key, name in zip(['det', 'pose', 'total'], ['Det ', 'Pose', 'Infr']):
        t_arr = np.array(times[key])
        print(f"  {name}  : Mean={np.mean(t_arr):.1f}ms, Min={np.min(t_arr):.1f}ms, Max={np.max(t_arr):.1f}ms, Std={np.std(t_arr):.1f}ms")
    print("=" * 110)

def generate_evaluation_plots(preds, gts, depth_stats, times, iou_thresh, save_path='kitti_eval_plot.png'):
    print("Generating comprehensive plots...")
    fig = plt.figure(figsize=(18, 10))
    gs = gridspec.GridSpec(2, 6)

    # Prepare Scatter Data
    all_gt, all_pred = [], []
    for fid, p_list in preds.items():
        if fid in gts:
            for g in gts[fid]:
                best_p, best_iou = None, 0
                for p in p_list:
                    iou = compute_iou(g['bbox'], p['bbox'])
                    if iou > iou_thresh and iou > best_iou: best_iou, best_p = iou, p
                if best_p:
                    all_gt.append(g['depth'])
                    all_pred.append(best_p['depth_pred'])

    # 1. Depth Correlation
    ax1 = plt.subplot(gs[0, 0:3])
    ax1.scatter(all_gt, all_pred, alpha=0.3, s=5, c='blue', label='Predictions')
    ax1.plot([0, 80], [0, 80], 'r--', label='Ideal')
    ax1.set(xlabel='GT Depth (m)', ylabel='Pred Depth (m)', title=f'Depth Correlation (N={len(all_gt)})', xlim=(0,80), ylim=(0,80))
    ax1.grid(True, linestyle='--', alpha=0.6); ax1.legend()

    # 2. Error Distribution
    ax2 = plt.subplot(gs[0, 3:6])
    errs = [e for e in depth_stats['All']['errs'] if e < 10]
    if errs: ax2.hist(errs, bins=50, color='orange', alpha=0.7, edgecolor='black')
    ax2.set(xlabel='Absolute Error (m)', ylabel='Count', title=f'Error Distribution (Count={len(errs)})')
    ax2.grid(axis='y', linestyle='--', alpha=0.6)

    # Time Distributions
    x_indices = np.arange(len(times['det']))
    plot_configs = [
        (gs[1, 0:2], times['det'], 'green', 'Detection Time'),
        (gs[1, 2:4], times['pose'], 'purple', 'Pose Estimation Time'),
        (gs[1, 4:6], times['total'], 'brown', 'Total Inference Time')
    ]
    
    for grid_pos, time_data, color, title in plot_configs:
        ax = plt.subplot(grid_pos)
        mean_t = np.mean(time_data)
        ax.scatter(x_indices, time_data, alpha=0.5, s=3, c=color)
        ax.axhline(mean_t, color='red', linestyle='--', linewidth=2, label=f'Mean: {mean_t:.1f}ms')
        ax.set(xlabel='Image Index', ylabel='Time (ms)', title=title)
        ax.grid(True, linestyle='--', alpha=0.6); ax.legend()

    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    print(f"✅ Comprehensive charts saved to {save_path}")

# ==========================================
# Module 5: Main Pipeline (调度主程序)
# ==========================================

def parse_args():
    parser = argparse.ArgumentParser(description="KITTI Evaluation Script")
    parser.add_argument('--kitti_root', type=str, default='data/kitti', help='KITTI Root Dir')
    parser.add_argument('--result_dir', type=str, default='data/kitti_rsts/json', help='Predictions JSON Dir')
    parser.add_argument('--iou_thresh', type=float, default=0.5, help='IoU Threshold')
    return parser.parse_args()

def find_label_dir(kitti_root):
    for p in [os.path.join(kitti_root, 'data_object_label_2', 'training', 'label_2'),
              os.path.join(kitti_root, 'training', 'label_2')]:
        if os.path.exists(p): return p
    return None

def main():
    args = parse_args()
    
    # Setup
    valid_label_dir = find_label_dir(args.kitti_root)
    if not valid_label_dir:
        print(f"Error: Label directory not found in {args.kitti_root}")
        return

    # Step 1: Load Data
    preds, gts, times, ds_info = load_data(args.result_dir, valid_label_dir)
    if not preds: return

    # Step 2: Print Dataset Overview
    print_dataset_info(ds_info, len(preds))

    # Step 3: Core Evaluation
    depth_stats = eval_depth_metrics(preds, gts, args.iou_thresh)
    ap_stats = {}
    for mode in ['Easy', 'Moderate', 'Hard']:
        ap11, ap40 = eval_detection_ap(preds, gts, mode, args.iou_thresh)
        ap_stats[mode] = {'R11': ap11, 'R40': ap40}

    # Step 4: Report and Visualize
    print_evaluation_report(depth_stats, ap_stats, times, args.iou_thresh)
    generate_evaluation_plots(preds, gts, depth_stats, times, args.iou_thresh)

if __name__ == "__main__":
    main()
    