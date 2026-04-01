import requests
import base64
import time
import os

def get_real_base64(image_path: str) -> str:
    """读取真实的本地图片，转换为完整的 Base64 编码"""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"[-] 找不到指定的图片: {image_path}。请填写正确的路径！")
    
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def save_base64_to_image(base64_data: str, output_filename: str):
    """将后端返回的 Base64 字符串还原并保存为物理图片"""
    if not base64_data:
        return
    
    # 有些 base64 字符串可能带有 data:image/jpeg;base64, 前缀，需要剔除
    if "," in base64_data:
        base64_data = base64_data.split(",")[1]
        
    img_bytes = base64.b64decode(base64_data)
    with open(output_filename, "wb") as f:
        f.write(img_bytes)
    print(f"[+] 结果图片已保存: {output_filename}")

def run_suspect_localization(image_path: str, fence_coords: list = None, gps_coords: dict = None):
    """构造完整数据并调用后端接口"""
    url = "http://127.0.0.1:8110/api/v1/perception/suspect_localization"

    try:
        real_base64_str = get_real_base64(image_path)
    except Exception as e:
        print(e)
        return

    # 组装请求 Payload (完全对齐前端结构，但使用了完整的 base64)
    payload = {
        "req_id": f"req_{int(time.time() * 1000)}",
        "terrain": "mount",
        "det_model": "yolo26l",
        "pose_model": "yolo26l-pose",
        "camera_info": {
            "device_id": "cam_001",
            "extrinsics": {
                #40.049478, 116.273055
                "gps": gps_coords,
                "height_above_ground": 3.5,
                "pose": {"pitch": -15, "yaw": 0, "roll": 0}
            },
            "intrinsics": {
                "image_resolution": {"width": 1920, "height": 1080},
                "hardware_specs": {"focal_length_mm": 6, "sensor_width_mm": 5.37},
                "distortion_coeffs": [-0.1, 0.05, 0, 0, 0]
            }
        },
        "image_data": {
            "base64": real_base64_str
        },
        "targets": []
    }

    if fence_coords is not None:
        payload["fence_coords"] = fence_coords
    response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})

    if response.status_code == 200:
        print("[+] 请求成功！(Status 200)")
        res_json = response.json()


        data = res_json.get("data", {})
        results = data.get("results", [])

        print(f"\n--- 推理结果摘要 ---")
        print("data:",data)
        for idx, suspect in enumerate(results):
            computation_details = suspect.get('computation_details', {})
            geo = suspect.get('suspect_geo_location', {})
            target_info = {
                "person_lat":geo.get('lat'),
                "person_lng": geo.get('lng'),
                "distance_to_fence":computation_details.get('distance_to_fence')
            }
            return target_info
        print(f"\n[+] 全部流程执行完毕！")

    elif response.status_code == 422:
        print("[-] Pydantic 数据校验失败 (Status 422):")
        print(response.json())
    else:
        print(f"[-] 请求失败! Status Code: {response.status_code}")
        print(f"[-] 错误详情: {response.text}")


if __name__ == "__main__":
    # 图片路径
    TEST_IMAGE_PATH = "D:/BIT_CV/Location/capture_pic/captures/10米/capture_002.jpg"

    #摄像头经纬度
    GPS_COORDS = {"lat": 40.049478, "lng": 116.273055, "alt": 15}
    #{'person_lat': 40.04964246915671, 'person_lng': 116.27306495106372, 'distance_to_fence': 23.05}
    #围栏经纬度
    FENCE_COORDS = [
        (40.049478, 116.273055),
        (40.050859, 116.280843)
    ]

    if 'FENCE_COORDS' in locals() and FENCE_COORDS:
       target_info = run_suspect_localization(TEST_IMAGE_PATH, fence_coords = FENCE_COORDS, gps_coords=GPS_COORDS)
    else:
       target_info = run_suspect_localization(TEST_IMAGE_PATH, gps_coords=GPS_COORDS)
    print(target_info)
