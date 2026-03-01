# 1. info

[KITTI 3D](https://www.cvlibs.net/datasets/kitti/eval_object.php?obj_benchmark=3d)

Download zips
- [Download left color images of object data set (12 GB)](https://s3.eu-central-1.amazonaws.com/avg-kitti/data_object_image_2.zip)
- [Download camera calibration matrices of object data set (16 MB)](https://s3.eu-central-1.amazonaws.com/avg-kitti/data_object_calib.zip)
- [Download training labels of object data set (5 MB)](https://s3.eu-central-1.amazonaws.com/avg-kitti/data_object_label_2.zip)

## 1.1. structure

```text
backend/data/kitti/
├── data_object_calib/
├── data_object_image_2/
│     ├── training/
│           ├── 000000.png
│           ├── 000001.png
│           └── ...
│     ├── testing/
├── testing/
├── data_object_label_2/
```

## 1.2. label info

| 序号 | 字段名         | 数据类型   | 示例         | 单位  | 说明         |
| -- | ----------- | ------ | ---------- | --- | ---------- |
| 1  | type        | string | Pedestrian | -   | 类别，'Car', 'Van', 'Pedestrian', 'Cyclist'。         |
| 2  | truncated   | float  | 0.00       | 0–1 | 截断比例，0.0 = 完全在图内，1.0 = 完全在图外。       |
| 3  | occluded    | int    | 0          | 0–3 | 遮挡等级，0=完全可见, 1=部分遮挡, 2=严重遮挡, 3=几乎看不见。       |
| 4  | alpha       | float  | -0.20      | rad | 观察角。范围 [−π,π]，描述物体朝向与相机视角的夹角。        |
| 5  | bbox_left   | float  | 712.40     | px  | 2D框左 x 坐标       |
| 6  | bbox_top    | float  | 143.00     | px  | 2D框上 y 坐标       |
| 7  | bbox_right  | float  | 810.73     | px  | 2D框右 x 坐标       |
| 8  | bbox_bottom | float  | 307.92     | px  | 2D框下 y 坐标       |
| 9  | height      | float  | 1.89       | m   | 3D高度 (米)       |
| 10 | width       | float  | 0.48       | m   | 3D宽度 (米)       |
| 11 | length      | float  | 1.20       | m   | 3D长度 (米)       |
| 12 | x           | float  | 1.84       | m   | 相机坐标系x (米)。(正右方)     |
| 13 | y           | float  | 1.47       | m   | 相机坐标系y (米)。(正下方，对应高度)     |
| 14 | z           | float  | 8.41       | m   | 相机坐标系z (米)。(正前方，真值深度) |
| 15 | rotation_y  | float  | 1.57       | rad | 绕Y轴旋转 (物体朝向)      |

## 1.3. calib info

| 字段             | 维度  | 说明       |
| -------------- | --- | -------- |
| P0–P3          | 3×4 | 投影矩阵。左目灰度，右目灰度，左目彩色，右目彩色     |
| R0_rect        | 3×3 | 旋转矩阵 (用于激光雷达对齐，单目暂不用)     |
| Tr_velo_to_cam | 3×4 | 激光→相机变换 (单目暂不用)  |
| Tr_imu_to_velo | 3×4 | IMU→激光变换 (单目暂不用) |

| 位置     | 矩阵元素     | 含义       | 物理说明             | 像素高度测距是否有用 |
| ------ | -------- | -------- | ---------------- | ---------- |
| 1  | a1 = fx  | 水平焦距     | 单位为像素，控制水平方向投影缩放 | ❌ 不直接使用    |
| 2  | a2       | 0        | 理想情况下为0（无倾斜）     | ❌ 无用       |
| 3  | a3 = cx  | 主点x坐标    | 图像中心点横坐标（像素）     | ❌ 不需要      |
| 4  | a4 = tx  | 平移参数     | 与双目基线有关          | ❌ 不需要      |
| 5  | a5       | 0        | 理想情况下为0          | ❌ 无用       |
| 6  | a6 = fy  | 垂直焦距     | 单位为像素，控制垂直方向缩放   | ✅ **必须使用** |
| 7  | a7 = cy  | 主点y坐标    | 图像中心点纵坐标         | ❌ 不需要      |
| 8  | a8 = ty  | 平移参数     | 与立体矫正有关          | ❌ 不需要      |
| 9  | a9       | 0        | 投影矩阵标准项          | ❌ 无用       |
| 10 | a10      | 0        | 投影矩阵标准项          | ❌ 无用       |
| 11 | a11 = 1  | 齐次坐标归一化项 | 保证z方向正确投影        | ❌ 不需要      |
| 12 | a12 = tz | 平移参数     | 与外参有关            | ❌ 不需要      |



# 2. infer & eval

## 2.1. change dir

```shell
cd backend
```

## 2.2. infer dir

```shell
python kitti_infer.py --limit 10

python kitti_eval.py
```

# 3. KITTI rsts

## 3.1. KITTI info

```text
==================================================
 KITTI DATASET INFO (Ground Truth)
--------------------------------------------------
 Total Target Files : 7481
 Total Pedestrians  : 4487
  - Easy            : 2310
  - Moderate        : 3569
  - Hard            : 4276
==================================================
```

## 3.2. my eval

### 3.2.1. yolo26l + yolo11l-pose

```shell
(yolo) E:\School\2026\WeiTong\YOLO\backend>python kitti_infer.py --output_dir data/yolo26l11l_rsts --det_model ./models/Detect/yolo26l.pt --pose_model ./models/Pose/yolo11l-pose.pt                                           
🚀 Loading models on device: 0...
🔥 Warming up GPU...
✅ Warmup complete. Starting benchmark...
Start Inference on 7481 images...
100%|█████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 7481/7481 [08:04<00:00, 15.44it/s] 

Inference Complete! Results saved to data/yolo26l11l_rsts

(yolo) E:\School\2026\WeiTong\YOLO\backend>python kitti_eval.py --result_dir data/yolo26l11l_rsts/json
Loading data from 7481 files...
100%|████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 7481/7481 [01:13<00:00, 101.14it/s]

==============================================================================================================
 EVALUATION REPORT (Pedestrian, IoU=0.5)
--------------------------------------------------------------------------------------------------------------
Difficulty   | Count   | AP_R11   | AP_R40   | ALE Mean   | ALE Min  | ALE Max  | ALE Std  | ALP <0.5m | ALP <1m | ALP <2m
--------------------------------------------------------------------------------------------------------------
Easy         | 2129    | 64.89    | 65.14    | 1.028      | 0.001    | 13.561   | 1.210    | 39.9    % | 66.1  % | 86.9  %
Moderate     | 2892    | 56.66    | 57.14    | 1.221      | 0.000    | 21.724   | 1.559    | 36.7    % | 62.3  % | 83.1  %
Hard         | 3091    | 49.89    | 49.94    | 1.269      | 0.000    | 21.724   | 1.602    | 35.7    % | 61.0  % | 81.9  %
All          | 3165    | -        | -        | 1.270      | 0.000    | 21.724   | 1.622    | 36.1    % | 61.4  % | 82.0  %
--------------------------------------------------------------------------------------------------------------
Time Statistics (per image):
  Det   : Mean=20.0ms, Min=13.9ms, Max=49.8ms, Std=5.8ms
  Pose  : Mean=17.6ms, Min=0.0ms, Max=414.7ms, Std=42.7ms
  Infr  : Mean=37.7ms, Min=13.9ms, Max=449.3ms, Std=43.6ms
==============================================================================================================
```


### 3.2.2. yolo26l + yolo26l-pose

```shell
(yolo) E:\School\2026\WeiTong\YOLO\backend>python kitti_infer.py --output_dir data/yolo26l_rsts --det_model ./models/Detect/yolo26l.pt --pose_model ./models/Pose/yolo26l-pose.pt
🚀 Loading models on device: 0...
🔥 Warming up GPU...
✅ Warmup complete. Starting benchmark...
Start Inference on 7481 images...
100%|█████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 7481/7481 [08:26<00:00, 14.76it/s] 

Inference Complete! Results saved to data/yolo26l_rsts/json

(yolo) E:\School\2026\WeiTong\YOLO\backend>python kitti_eval.py --result_dir data/yolo26l_rsts/json
Loading data from 7481 files...
100%|████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 7481/7481 [01:08<00:00, 108.99it/s]

==============================================================================================================
 EVALUATION REPORT (Pedestrian, IoU=0.5)
--------------------------------------------------------------------------------------------------------------
Difficulty   | Count   | AP_R11   | AP_R40   | ALE Mean   | ALE Min  | ALE Max  | ALE Std  | ALP <0.5m | ALP <1m | ALP <2m
--------------------------------------------------------------------------------------------------------------
Easy         | 2129    | 64.89    | 65.14    | 1.000      | 0.001    | 17.669   | 1.189    | 40.9    % | 67.4  % | 87.4  %
Moderate     | 2892    | 56.66    | 57.14    | 1.184      | 0.001    | 18.529   | 1.505    | 37.5    % | 63.5  % | 83.8  %
Hard         | 3091    | 49.89    | 49.94    | 1.230      | 0.001    | 18.529   | 1.549    | 36.8    % | 62.3  % | 82.7  %
All          | 3165    | -        | -        | 1.230      | 0.001    | 18.529   | 1.569    | 37.1    % | 62.8  % | 82.8  %
--------------------------------------------------------------------------------------------------------------
Time Statistics (per image):
  Det   : Mean=21.3ms, Min=13.9ms, Max=45.5ms, Std=5.8ms
  Pose  : Mean=18.0ms, Min=0.0ms, Max=435.5ms, Std=43.3ms
  Infr  : Mean=39.4ms, Min=13.9ms, Max=473.2ms, Std=44.2ms
==============================================================================================================
```

### 3.2.3. yolo26x + yolo26x-pose

```shell
(yolo) E:\School\2026\WeiTong\YOLO\backend>python kitti_infer.py --output_dir data/yolo26x_rsts --det_model ./models/Detect/yolo26x.pt --pose_model ./models/Pose/yolo26x-pose.pt
🚀 Loading models on device: 0...
🔥 Warming up GPU...
✅ Warmup complete. Starting benchmark...
Start Inference on 7481 images...
100%|█████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 7481/7481 [10:39<00:00, 11.70it/s]

Inference Complete! Results saved to data/yolo26x_rsts

(yolo) E:\School\2026\WeiTong\YOLO\backend>python kitti_eval.py --result_dir data/yolo26x_rsts/json                                                            
Loading data from 7481 files...
100%|████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 7481/7481 [00:46<00:00, 162.36it/s]

==============================================================================================================
 EVALUATION REPORT (Pedestrian, IoU=0.5)
--------------------------------------------------------------------------------------------------------------
Difficulty   | Count   | AP_R11   | AP_R40   | ALE Mean   | ALE Min  | ALE Max  | ALE Std  | ALP <0.5m | ALP <1m | ALP <2m
--------------------------------------------------------------------------------------------------------------
Easy         | 2151    | 67.66    | 66.61    | 1.137      | 0.000    | 12.487   | 1.290    | 37.1    % | 63.3  % | 83.8  %
Moderate     | 2938    | 57.14    | 57.91    | 1.331      | 0.000    | 13.918   | 1.633    | 34.8    % | 59.5  % | 80.1  %
Hard         | 3142    | 50.38    | 50.56    | 1.381      | 0.000    | 13.918   | 1.692    | 34.2    % | 58.5  % | 79.0  %
All          | 3229    | -        | -        | 1.394      | 0.000    | 31.578   | 1.797    | 34.3    % | 58.7  % | 79.1  %
--------------------------------------------------------------------------------------------------------------
Time Statistics (per image):
  Det   : Mean=20.0ms, Min=13.3ms, Max=79.9ms, Std=5.4ms
  Pose  : Mean=37.3ms, Min=0.0ms, Max=9366.1ms, Std=200.2ms
  Infr  : Mean=57.5ms, Min=13.3ms, Max=9386.3ms, Std=200.5ms
==============================================================================================================
```

### 3.2.4. yolo11l + yolo11l-pose

```shell
(yolo) E:\School\2026\WeiTong\YOLO\backend>python kitti_infer.py --output_dir data/yolo11l_rsts --det_model ./models/Detect/yolo11l.pt --pose_model ./models/Pose/yolo11l-pose.pt
🚀 Loading models on device: 0...
🔥 Warming up GPU...
✅ Warmup complete. Starting benchmark...
Start Inference on 7481 images...
100%|█████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 7481/7481 [08:22<00:00, 14.88it/s] 

Inference Complete! Results saved to data/yolo11l_rsts

(yolo) E:\School\2026\WeiTong\YOLO\backend>python kitti_eval.py --result_dir data/yolo11l_rsts/json                                                            
Loading data from 7481 files...
100%|█████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 7481/7481 [01:15<00:00, 99.02it/s]

==============================================================================================================
 EVALUATION REPORT (Pedestrian, IoU=0.5)
--------------------------------------------------------------------------------------------------------------
Difficulty   | Count   | AP_R11   | AP_R40   | ALE Mean   | ALE Min  | ALE Max  | ALE Std  | ALP <0.5m | ALP <1m | ALP <2m
--------------------------------------------------------------------------------------------------------------
Easy         | 2115    | 67.69    | 66.86    | 1.086      | 0.000    | 39.616   | 1.522    | 39.0    % | 65.7  % | 86.0  %
Moderate     | 2844    | 57.63    | 57.21    | 1.227      | 0.000    | 39.616   | 1.667    | 36.1    % | 62.2  % | 82.8  %
Hard         | 3031    | 50.88    | 49.77    | 1.267      | 0.000    | 39.616   | 1.702    | 35.5    % | 61.1  % | 81.9  %
All          | 3100    | -        | -        | 1.270      | 0.000    | 39.616   | 1.786    | 35.9    % | 61.5  % | 82.0  %
--------------------------------------------------------------------------------------------------------------
Time Statistics (per image):
  Det   : Mean=21.9ms, Min=14.8ms, Max=65.7ms, Std=6.3ms
  Pose  : Mean=17.7ms, Min=0.0ms, Max=707.6ms, Std=42.8ms
  Infr  : Mean=39.6ms, Min=14.8ms, Max=743.1ms, Std=44.1ms
==============================================================================================================
```

## 3.3. official eval

只去当前运行目录下的 data/object/label_2 找真值
只去 results/<你的实验名>/data 找预测结果

./evaluate_object yolo

### 3.3.1. table

| Methods                   | Easy  | Moderate  | Hard  |
| :------------------------ | :---: | :-------: | :---: |
| **MonoLoco (ICCV'19)**    | 61.82 | 54.72     | 49.06 |
| **MonOri (TNNLS'25)**     | 71.74 | 62.65     | 53.72 |
| **yolo26x + yolo26x-pose**| 69.35 | 61.09     | 53.64 |
