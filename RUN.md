# 1. Run

```shell
# 两个shell，分别执行前后端
## （1）后端（端口8001，一般不会冲突，可更改，但是可能可读性比较烂）
## 环境配置参见 backend/RUN-python.md
cd backend
python main.py

## （2）前端（端口5173，vue通用接口）
## 环境配置参见 frontend/RUN-vue.md
cd frontend
npm run dev
```

# 2. api

## 2.1. request

```json
// 请求参数 (Request Body Example):
{
    "req_id": "uuid-1234-5678", // [建议] string，请求追踪ID
    "timestamp": "2024-06-01T12:00:00Z", // [建议] string，请求时间戳，ISO 8601格式

    "camera_info": {
        "device_id": "cam_001", // [必填] string，设备唯一标识

         // 1. 地理位姿 (Extrinsics) - 相机位置、角度等外参
        "extrinsics": {
            "gps": { 
                "lat": 22.54321,  // [必填] float，纬度 (latitude)
                "lng": 114.05755, // [必填] float，经度 (longitude)
                "alt": 15.0       // [必填] float，高程 (altitude - Sea Level)
            }, 
            "height_above_ground": 3.5, // [必填] float，离地高度 (height) - 核心算法参数，不与“高程”混淆
            "pose": {
                "pitch": -15.5,   // [必填] float，俯仰角 (pitch) - 负值通常表示向下看
                "yaw": 120.0,     // [必填] float，偏航角 (yaw) - 0为正北，顺时针为正
                "roll": 0.0       // [必填] float，翻滚角 (roll) - 修正画面倾斜
            }
        },
        
        // 2. 光学属性 (Intrinsics) - 采用“硬件参数计算”，内参矩阵 = 物理焦距 * (图像宽度 / 传感器宽度)
        "intrinsics": {
            // [必填] 用于校验上传的图片是否被缩放，也是计算像素密度的分母，不与“实际传输图像分辨率”混淆
            "image_resolution": {
                "width": 1920,    // [必填] int，监控相机实际回传宽度
                "height": 1080    // [必填] int，监控相机实际回传高度
            },
            
            // [必填] 硬件规格
            "hardware_specs": {
                "focal_length_mm": 6.0,    // [必填] float，物理焦距，用于计算像素密度，得出内参矩阵
                "sensor_width_mm": 5.37    // [必填] float，传感器靶面宽度，用于计算像素密度，得出内参矩阵
            },
            
            // [可选] 畸变系数 (Distortion)
            "distortion_coeffs": [-0.1, 0.05, 0, 0, 0] // [可选] list[float]，[k1, k2, p1, p2, k3]
        }
    },

    "image_data": {
        "image_url": "http://example.com/image.jpg", // [可选] url，图像URL链接
        "base64": "/9j/4AAQSkZJRg...", // [可选] base64，包含嫌疑人的现场图像
    }, // [必填其一] 图像数据，可以是URL或Base64编码。且大小必须与上面的 image_resolution 一致（内部判断无需传参），否则后端报错

    "targets": [
        {
            "target_id": "person_01", // string，嫌疑人编码ID，每张图独立计数
            "bbox": { 
                "x": 100, "y": 200, "w": 50, "h": 120 
            }, // [必填] dict-float/int，本嫌疑人在图中的像素检测框。具体[x, y, w, h]还是[x_min, y_min, x_max, y_max]由双方事先约定
            "attributes": { 
                "type": "adult",
                "gender": "male / female"
            } // [可选] dict-string，如果前端有更高级的分类(比如小孩/成人，还有性别)，可以传参辅助算法修正身高假设
        },
    ] // list，多个targets.item
}
```

## 2.2. response

```shell
// 返回数据 (Response Body Example):
{
    "code": 200,
    "message": "Location estimated successfully",
    "data": {
        "req_id": "uuid-1234-5678", // [建议] string，请求追踪ID，用于确认，或并发场景对应
        "results": [
            {
                "target_id": "person_01", // 对应请求中的嫌疑人编码ID
                    "suspect_geo_location": { 
                        "lat": 22.54325, 
                        "lng": 114.05760,
                        "alt": 0.0 
                }, // [必填] 推算出的嫌疑人地理坐标
                "confidence": 0.95, // [必填] float，置信度 (0.0 - 1.0)
                "suspect_region_polygon": [
                    {"lat": 22.54320, "lng": 114.05758}, // 近点左
                    {"lat": 22.54320, "lng": 114.05762}, // 近点右
                    {"lat": 22.54330, "lng": 114.05765}, // 远点右
                    {"lat": 22.54330, "lng": 114.05755}  // 远点左
                ], // [必填] 嫌疑人所在误差区域的地理多边形顶点列表，用于前端地图可视化

                "computation_details": {
                    "calculated_depth": 15.3,   // 垂直深度 (Z) - 米
                    "straight_distance": 16.1,  // 直线距离 (Distance) - 米
                    "bearing_angle": 125.4      // 绝对地理方位角 (0-360)
                }, // [建议保留] 中间结果，调试用，如果经纬度不对给出更多信息。
            },
        ] // list，多个results.item
    }
}
```
