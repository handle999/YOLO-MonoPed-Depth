# backend/test_main_sys_v2_0401.py
import requests
import json
import base64
import os
import time

BASE_URL = "http://127.0.0.1:8112"

def get_base64_from_file(file_path):
    """辅助函数：读取本地图片并转为 Base64"""
    if not os.path.exists(file_path):
        print(f"[ERROR] 找不到测试图片: {file_path}")
        return None
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

# [修改] 增加 camera_type 参数，默认为 bullet
def test_fence_distance(terrain_mode="flat", img_path=None, camera_type="bullet"):
    print(f"\n=== 测试电子围栏距离接口 | 模式: {terrain_mode.upper()} | 相机类型: {camera_type.upper()} ===")
    
    # 1. 基础 Payload
    payload = {
        "ip": "172.168.0.175",  # ⚠️ 确保这个 IP 在 CSV 中真实存在
        "image_h": 1080,
        "image_w": 1920,
        "bnd": {
            "x": 1264,           # 绝对像素坐标
            "y": 462,
            "width": 40,
            "height": 89
        },
        "terrain_mode": terrain_mode,
        "camera_type": camera_type  # [新增] 告诉后端这是枪机还是球机
    }
    
    # 2. 如果是山地模式，自动读取本地图片并附加到 Payload 中
    if terrain_mode == "mount":
        if not img_path:
            print("[ERROR] 山地模式测试需要提供本地图片路径！")
            return
            
        base64_data = get_base64_from_file(img_path)
        if not base64_data:
            return
            
        payload["imageData"] = base64_data
        print(f"[INFO] 已成功加载本地图片并转为 Base64，大小: {len(base64_data) // 1024} KB")

    headers = {"Content-Type": "application/json"}
    
    # 3. 发送请求
    try:
        print("[INFO] 正在发送请求，请稍候...")
        response = requests.post(f"{BASE_URL}/xjzhdd/alarmEvent/pull/fence_distance", json=payload, headers=headers)
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print(f"Response JSON:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        else:
            print(f"Error Response:\n{response.text}")
            
    except Exception as e:
        print(f"请求失败: {e}")

if __name__ == "__main__":
    LOCAL_TEST_IMAGE = "E:/School/2026/WeiTong/YOLO/capture_pic/captures/capture_286.jpg" 

    # 0. 预热服务器 (不计入性能统计)
    print("--- 正在预热服务器 ---")
    test_fence_distance(terrain_mode="flat", camera_type="bullet")

    # 测试用例 1：枪机 + 平地模式
    start_time = time.time()
    test_fence_distance(terrain_mode="flat", camera_type="bullet")
    print(f"用例1测试完成，耗时: {time.time() - start_time:.4f} 秒")

    # 测试用例 2：枪机 + 山地模式
    start_time = time.time()
    test_fence_distance(terrain_mode="mount", img_path=LOCAL_TEST_IMAGE, camera_type="bullet")
    print(f"用例2测试完成，耗时: {time.time() - start_time:.4f} 秒")

    # 测试用例 3：球机(PTZ) + 平地模式
    # 这里不需要传图片，主要观察后端是否成功调用了模拟的 /sub 接口并融合了 PTZ 姿态
    start_time = time.time()
    test_fence_distance(terrain_mode="flat", camera_type="ptz")
    print(f"用例3测试完成，耗时: {time.time() - start_time:.4f} 秒")
