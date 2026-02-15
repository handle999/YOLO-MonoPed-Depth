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

# 0. method

```shell
Input Image
   |
   v
[YOLO Detect] ---> 全图推理，找框
   |
   +-> BBox 1 -> [Crop & Pad] -> [Pose Model] -> Keypoints -> [坐标还原]
   +-> BBox 2 -> [Crop & Pad] -> [Pose Model] -> Keypoints -> [坐标还原]
   ...
   |
   v
Merge Results (BBox + Keypoints)
   |
   v
[GeoLocalizer] (使用 Keypoints 测距，BBox 备用)
```


# 1. env

- [YOLO26](https://github.com/ultralytics/ultralytics)
    - [QuickStart](https://docs.ultralytics.com/quickstart/#conda-docker-image)
    - [Torch](https://pytorch.org/get-started/previous-versions/)

```shell
conda create -n YOLO python=3.8
conda activate YOLO
conda install pytorch==2.1.0 torchvision==0.16.0 torchaudio==2.1.0 pytorch-cuda=11.8 -c pytorch -c nvidia
# Install the ultralytics package using conda
conda install -c conda-forge ultralytics
# pkg for .exe
pip install pyinstaller
# pkgs for FastAPI and Vue3
conda install pydantic fastapi uvicorn python-multipart 
```

# 2. predict

```shell
python infer_loc.py --det_weight ./models/Detect/yolo26x.pt --source data/images/3.jpg --terrain flat

python infer_loc.py --det_weight ./models/Detect/yolo26l.pt --pose_weight ./models/Pose/yolo11l-pose.pt --source data/images/3.jpg --save_radar --terrain mount
```

