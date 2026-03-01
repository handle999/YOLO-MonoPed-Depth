# YOLO-MonoPed-Depth

**[中文]** | [English](README_EN.md)

**YOLO-MonoPed-Depth** 是一个基于单目视觉的行人几何深度估计系统。它结合了 **Object Detection (YOLO-Det)** 与 **Pose Estimation (YOLO-Pose)**，通过人体骨架的生物力学特征（如躯干长度、肩宽）来解决传统 BBox 测距在**人体弯腰、遮挡、半身截断**等复杂场景下失效的问题。

本项目包含完整的 **FastAPI 后端**、**Vue3 可视化前端**，以及针对 **KITTI 3D 数据集** 的完整评测与验证工具链。

![系统展示](figs/system.png)
![系统展示-2](figs/system-2.png)

## 📖 目录 (Table of Contents)

* [1. 背景与算法设计](README#1-背景与算法设计)
* [2. 项目结构](README#2-项目结构)
* [3. 快速开始](README#3-快速开始)
* [4. KITTI 评测结果](README#4-kitti-评测结果)
* [5. 致谢](README#5-致谢)

---

## 1. 背景与算法设计

### 1.1 背景 (Background)

传统的单目测距（如 MonoLoco 早期思路）通常依赖检测框（Bounding Box）的高度，假设行人是直立的（如 1.7m）。然而在实际监控或自动驾驶场景中：

* **非刚体形变**：行人弯腰、骑行或蹲下时，BBox 高度剧烈变化，导致距离估算偏大。
* **遮挡与截断**：仅拍摄到上半身或侧身时，几何投影关系失效。

### 1.2 核心算法：智能骨架测距 (Smart Skeleton Ranging)

本项目引入 `PoseConverter` 模块，采用 **“多级级联 (Cascade Strategy)”** 策略，优先寻找人体最稳定的“刚体”部件进行测距：

1. **Level 1: 完整躯干 (Torso)** - *[最推荐]*
* 利用 `肩中心` 到 `胯中心` 的欧氏距离。
* **优势**：抗弯腰干扰能力最强，受侧身影响小。


2. **Level 2: 肩宽 (Shoulder Width)** - *[半身模式]*
* 当图像只有上半身（下半身截断）时自动启用。
* **优势**：解决监控视角下的半身测距难题。
* **校验**：引入“相对比例校验（Ratio Check）”，防止侧身导致肩宽投影过窄引起的误判。


3. **Level 3: 肢体回退 (Limbs Fallback)**
* 当躯干不可见时，尝试使用大腿或上臂。
* **校验**：强制进行“垂直度检查（Verticality Check）”，防止手臂指向相机造成的透视误差。



这一过程在 `src/pose_utils.py` 与 `src/geolocalizer.py` 中实现，并结合相机内参（Intrinsics）与外参（Extrinsics，尤其是 Pitch 俯仰角）进行严格的几何投影计算。

---

## 2. 项目结构

```text
root/                           # [根项目目录]
├── backend/                    # [后端] 基于 FastAPI + Ultralytics
│   ├── api/                    # API 路由与 Schema 定义
│   ├── data/                   # 数据存放区
│   │   └── KITTI.md            # KITTI 数据集详细说明
│   ├── models/                 # 模型权重存放 (Detect/Pose)
│   ├── src/                    # 核心算法源码
│   │   ├── detector.py         # YOLO 推理封装 (支持 Batch Inference 加速)
│   │   ├── geolocalizer.py     # 几何定位与坐标转换核心
│   │   ├── pose_utils.py       # [核心] 智能骨架长度提取策略
│   │   ├── utils.py            # [核心] 其他功能（如base64图片读取等）
│   │   └── visualizer.py       # 可视化绘图 (骨架图/雷达图)
│   ├── infer_loc.py            # 单图/视频推理演示脚本
│   ├── kitti_infer.py          # KITTI 数据集批量推理脚本 (含 Warmup & 计时)
│   ├── kitti_eval.py           # KITTI 评测指标计算 (ALE/ALP)
│   ├── main.py                 # 后端服务入口
│   └── requirements.txt
│
└── frontend/                   # [前端] Vue 3 + Vite
    ├── src/
    │   ├── components/
    │   ├── App.vue             # 主交互页面 (参数配置/地图展示)
    │   └── main.js
    └── vite.config.js

```

---

## 3. 快速开始

详细运行参数请参考：[RUN.md](RUN.md#1.run)

### 3.1 环境准备

请分别在两个终端中启动服务。

* **后端** (默认端口 8001): 需要 Python 环境与 CUDA 支持（推荐），环境配置参见 [Backend](backend/RUN-python.md#1.env)。
* **前端** (默认端口 5173): 需要 Node.js 环境，环境配置参见 [Frontend](frontend/RUN-vue.md#1.env)。

### 3.2 启动命令

**Terminal 1: 启动后端**

```shell
cd backend
# 安装依赖
pip install -r requirements.txt
# 启动 API 服务
python main.py

```

**Terminal 2: 启动前端**

```shell
cd frontend
# 安装依赖
npm install
# 开发模式运行
npm run dev

```

启动后，访问 `http://localhost:5173` 即可看到交互界面。支持上传图片、调整相机外参（Pitch/Height）、切换 **Flat/Mount** 模式并查看实时定位结果（卫星地图 + 俯视雷达）。

---

## 4. KITTI 评测结果

我们使用标准的 **KITTI 3D Object Detection Dataset** 对算法进行了严格验证。
详细的推理与评测流程请参阅：[backend/data/KITTI.md](backend/data/KITTI.md)

### 4.1 评测指标

* **ALE (m)**: 平均定位绝对误差 (Average Localization Error)。
* **ALP (< Xm)**: 定位精度 (Average Localization Precision)，误差在 X 米内的比例。
* **AP_R40**：平均精度（Average Precision），官方指标，使用40个插值。

### 4.2 性能数据

以下是使用 `yolo26x.pt` (Detect) + `yolo26x-pose.pt` (Pose) 在 KITTI 训练+验证集上的表现：

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

得益于 Pose 的 Batch Inference 优化，可在保持高精度（Easy 模式 ALE ≈ 1m）的同时，达到了实时的推理速度。

![推理结果](figs/kitti_eval_plot.png "KITTI统计结果")

在KITTI 3D目标检测 validation 上进行评估，使用官方AP_R40指标，针对Pedestrian类别，采用2D边界框（bbox）检测指标，对比结果如下：

| Methods                   | Easy  | Moderate  | Hard  |
| :------------------------ | :---: | :-------: | :---: |
| **MonoLoco (ICCV'19)**    | 61.82 | 54.72     | 49.06 |
| **MonOri (TNNLS'25)**     | 71.74 | 62.65     | 53.72 |
| **Ours**                  | 69.35 | 61.09     | 53.64 |

---

## 5. 致谢

本项目参考或使用了以下优秀的开源项目与资源：

* **YOLO (Ultralytics)**: [https://github.com/ultralytics/ultralytics](https://github.com/ultralytics/ultralytics) - SOTA 的检测与姿态模型。
* **MonoLoco**: [https://github.com/vita-epfl/monoloco](https://github.com/vita-epfl/monoloco) - 单目行人定位的先驱工作。
* **KITTI 3D Benchmark**: [https://www.cvlibs.net/datasets/kitti/](https://www.cvlibs.net/datasets/kitti/eval_object.php?obj_benchmark=3d) - 自动驾驶领域的黄金数据集。
* **Gemini**: [https://gemini.google.com](https://gemini.google.com) - 代码重构与算法逻辑优化的 AI 助手。

---
