# YOLO-MonoPed-Depth

Implement monocular pedestrian geometric depth estimation using `yolo-det` + `yolo-pose`

# 1. Sturcture

```
root/                           # [根项目目录]
├── backend/                    # [后端] 现有的 Python 项目
│   ├── api/
│   │   ├── __init__.py
│   │   └── schemas.py          # Pydantic 模型
│   ├── config/
│   ├── data/
│   │   ├── images/
│   │   └── output/
│   ├── models/
│   │   └── Detectino/
│   │       └── yolov8n.pt
│   ├── src/
│   │   ├── __init__.py
│   │   ├── detector.py
│   │   ├── geolocalizer.py
│   │   ├── visualizer.py
│   │   └── utils.py            # [已移动] 原 api/utils.py
│   ├── infer_loc.py            # 模型效果验证
│   ├── kitti_eval.py           # 对KITTI 3D
│   ├── kitti_infer.py          # 对KITTI 3D推理
│   ├── main.py                 # FastAPI 入口
│   └── requirements.txt
│
└── frontend/                   # [前端] Vue 3 + Vite 项目
    ├── public/
    ├── src/
    │   ├── assets/
    │   ├── components/
    │   ├── App.vue             # [核心] 主页面逻辑
    │   └── main.js             # 入口文件
    ├── index.html
    ├── package.json
    └── vite.config.js
```

# 2. Run Demo

See in [RUN](RUN.md#1.run)

两个shell，分别执行前后端

1. 后端（端口8001，一般不会冲突，可更改，但是可能可读性比较烂），环境配置参见 [Backend](backend/RUN-python.md#1.env)
1. 前端（端口5173，vue通用接口），环境配置参见 [Frontend](frontend/RUN-vue.md#1.env)

```shell
cd backend
python main.py

cd frontend
npm run dev
```

# 3. Metric on KITTI

[KITTI] Dataset see in [markdown](backend/data/KITTI.md), including [download](backend/data/KITTI.md#1-info), [structure](backend/data/KITTI.md#11-structure), [infer](backend/data/KITTI.md#2-infer--eval), [results](backend/data/KITTI.md#3-kitti-rsts)

```shell
================================================================================
Difficulty      | Count    | ALE (m)    | ALP (<0.5m)  | ALP (<1m)  | ALP (<2m)
--------------------------------------------------------------------------------
Easy            | 2049     | 0.993      | 40.7        % | 67.4      % | 87.9      %
Moderate        | 2700     | 1.085      | 38.4        % | 65.2      % | 85.8      %
Hard            | 2888     | 1.138      | 37.5        % | 63.7      % | 84.5      %
All             | 2954     | 1.131      | 37.7        % | 63.9      % | 84.6      %
--------------------------------------------------------------------------------
Time Statistics (Mean):
  Det : 18.6 ms
  Pose: 15.3 ms
  Post: 0.1 ms
  Infr: 34.1 ms (Total per Image)
Average Inference Time: 34.1 ms/img
================================================================================
```

# Acknowledgment

- [YOLO](https://github.com/ultralytics/ultralytics)
- [MonoLoco](https://github.com/vita-epfl/monoloco)
- [KITTI 3D](https://www.cvlibs.net/datasets/kitti/eval_object.php?obj_benchmark=3d)
- [Gemini](https://gemini.google.com)