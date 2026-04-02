
# 0401修改记录

1. 修改`backend/main_sys_v2.py`
    1. 纠正'get_distance_professional'的错误转换逻辑
    1. 加速'get_distance_professional'，全局实例化Transformer模块 + 全局Dict读取csv
    1. 补充'/xjzhdd/alarmEvent/sub'的模拟，球机传参
    1. 完善'/xjzhdd/alarmEvent/pull/fence_distance'，实现'process_bullet_localization'和'process_ptz_localization'，同时区分'flat'和'mount'模式
1. 修改`frontend/src/App.vue`和`frontend/src/style.css`，增加8112展示页面
1. 增加`frontend/src/views/Sysv2View.vue`，8112可视化子页面，自定义模式和参数，上传图片/url，可视化框，可视化俯视结果，展示json返回值
1. 修改`frontend/src/components/MapDisplay.vue`，8112右侧自适应墙体展示（红色虚线）
1. 增加`frontend/src/components/Sysv2CameraInput.vue`，8112左侧输入相关组件

## 张老师接口
```js
http://IP:81ll/xjzhdd/alarmEvent/pull/fence_distance
methods=["POST"]

本地测试：http://127.0.0.1:8111/xjzhdd/alarmEvent/pull/fence_distance

// 
{
    "image_h": 1920,
    "image_w": 1080,
    "ip": 192.167.1.101,
    "bnd": {
        'x': 562,
        'y': 369,
        'width': 53,
        'height': 86
    },
    "image": base64 / url
}

// response
{
    "code": 200,
    "data":
    {
        "dev_id": dev_id,
        "person_lat": person_lat,
        "person_lng": person_lng,
        "distance_to_fence": distance_to_fence
    }
}
```

## 目前实现接口
```js
{
    "image_h": 1920,
    "image_w": 1080,
    "ip": "192.167.1.101",
    "bnd": { 
        'x': 562, 
        'y': 369, 
        'width': 53, 
        'height': 86 },
    "camera_type": "bullet",
    "terrain_mode": "flat",
    "imageData": "base64_string_here..." // 注意：依据 Python 源码，字段名应为 imageData
}

// response
{
  "code": 200,
  "data": {
    "dev_id": "cam_001",                   // String: 从 CSV 查到的设备唯一标识 ID
    "person_lat": 40.05281234,             // Float: 算法推算出的目标绝对纬度
    "person_lng": 116.28015678,            // Float: 算法推算出的目标绝对经度
    "distance_to_fence": 1.04321,          // Float 或 null: 目标距离电子围栏的最短距离(米)。若 CSV 没配置围栏则为 null
    "terrain_mode": "flat",                // String: 本次回调使用的地形模式 ("flat" 或 "mount")
    
    // 以下 4 个字段主要是辅助前端地图可视化用的
    "camera_lat": 40.05190200,             // Float: 真实的摄像机纬度 (从 CSV 读取)
    "camera_lng": 116.28008900,            // Float: 真实的摄像机经度 (从 CSV 读取)
    "distance_from_camera": 15.24,         // Float: 目标距离相机的直线距离(米)
    "fence_coords": [                      // Array 或 null: 围栏的经纬度折线数组
      [40.051902, 116.280089], 
      [40.052784, 116.279886]
    ]
  }
}
```
