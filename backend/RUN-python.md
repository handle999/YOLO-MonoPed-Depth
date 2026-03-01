```text
backend/
├── api/
│   ├── __init__.py
│   └── schemas.py            # [输出] 结果图和日志
├── config/
<!-- │   └── camera_params.yaml    # [配置文件] 存放相机经纬度、安装高度、内参等 -->
├── data/
│   ├── images/               # [输入] 待检测图片
│   └── output/               # [输出] 结果图和日志
├── models/
│   └── Detectino
|       └── yolov8n.pt        # [模型] 官方权重
├── src/
│   ├── __init__.py
│   ├── detector.py           # [核心] 封装 YOLOv8 推理逻辑
│   ├── geolocalizer.py       # [核心] 封装 像素坐标 -> 地理坐标 的数学公式
│   └── visualizer.py         # [辅助] 画图工具
│   └── utils     .py         # [辅助] base64图像读取、距离转gps
├── infer_loc.py              # [入口] 模型效果验证
├── main.py                   # [入口] 主程序，串联整个流程
└── requirements.txt          # 依赖包
```

# 0. method

```text
Input Image
   |
   v
[YOLO Detect] ---> 全图推理，找框
   |
   +-> BBox 1 -> [Crop & Pad] -> [Pose Model] -> Keypoints -> [coordinates]
   +-> BBox 2 -> [Crop & Pad] -> [Pose Model] -> Keypoints -> [coordinates]
   ...
   |
   v
Merge Results (BBox + Keypoints)
   |
   v
[GeoLocalizer] (Use Keypoints first, BBox last)
```


# 1. env

- [YOLO26](https://github.com/ultralytics/ultralytics)
    - [QuickStart](https://docs.ultralytics.com/quickstart/#conda-docker-image)
    - [Torch](https://pytorch.org/get-started/previous-versions/)

```shell
# if want to use >= yolo26 (i.e., ultralytics>=8.4.0), use python>=3.10
conda create -n yolo python=3.10 -y
conda activate yolo
# warning: torch 2.1 and 2.2 match numpy 1.x, while current numpy 2.x will be auto installed
# so first lock numpy=1.26.4
conda install numpy=1.26.4 -y
conda install pytorch==2.1.0 torchvision==0.16.0 torchaudio==2.1.0 pytorch-cuda=11.8 -c pytorch -c nvidia
# Install the ultralytics package using conda
# if python=3.8, installs 8.3.43, while not support yolo26
# python=3.10 installs 8.4.14 in 2026/2/26
conda install -c conda-forge ultralytics
# if pkg for .exe, but not used
# pip install pyinstaller
# pkgs for geo-utils and vis
conda install geopy tqdm
# pkgs for FastAPI and Vue3: conda install pydantic fastapi uvicorn python-multipart
# suggest to use flask
conda install pydantic flask flask-cors python-multipart
```

# 2. predict

```shell
python infer_loc.py --det_weight ./models/Detect/yolo26x.pt --source data/images/3.jpg --terrain flat

python infer_loc.py --det_weight ./models/Detect/yolo26l.pt --pose_weight ./models/Pose/yolo11l-pose.pt --source data/images/3.jpg --save_radar --terrain mount
```

# 3. kitti infer

See in [KITTI](data/KITTI.md)

```shell
python kitti_eval.py
```

Results on KITTI `training (train + val)` dataset, using `yolo26x + yolo26x-pose`.

```text
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
