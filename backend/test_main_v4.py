import requests
import base64
import time
import pandas as pd
import os
import datetime
import uuid
import datetime

def get_real_base64(image_path: str) -> str:
    """读取真实的本地图片，转换为完整的 Base64 编码"""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"[-] 找不到指定的图片: {image_path}。请填写正确的路径！")
    
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def parse_line_to_fence_coords(line_str):
    """
    专门解析你 CSV 中的 line 字段
    """
    if pd.isna(line_str) or not str(line_str).strip():
        return None
        
    fence_coords = []
    line_str = str(line_str).strip()
    
    points = line_str.split(';')
    for pt in points:
        if pt.strip():
            try:
                lng_str, lat_str = pt.split(',')
                fence_coords.append((float(lat_str.strip()), float(lng_str.strip())))
            except ValueError:
                print(f"[-] 警告：坐标点解析失败，跳过异常数据: '{pt}'")
                
    return fence_coords if fence_coords else None


def run_suspect_localization(image_path: str, gps_coords: dict, elevation: float, pitch: float, direction: float, dev_id: str,fence_coords: list = None):
    """构造完整数据并调用后端接口"""
    url = "http://127.0.0.1:8110/api/v1/perception/suspect_localization"

    try:
        real_base64_str = get_real_base64(image_path)
    except Exception as e:
        print(e)
        return

    # 组装请求 Payload
    payload = {
        "req_id": f"req_{int(time.time() * 1000)}",
        "terrain": "mount",
        "det_model": "yolo26l",
        "pose_model": "yolo26l-pose",
        "camera_info": {
            "device_id":dev_id,
            "extrinsics": {
                "gps": gps_coords,                
                "height_above_ground": elevation, 
                "pose": {"pitch": pitch, "yaw": direction, "roll": 0} 
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
        
        for idx, suspect in enumerate(results):
            computation_details = suspect.get('computation_details', {})
            geo = suspect.get('suspect_geo_location', {})
            target_info = {
                "person_lat": geo.get('lat'),
                "person_lng": geo.get('lng'),
                "distance_to_fence": computation_details.get('distance_to_fence')
            }
            #print(f"\n[+] 全部流程执行完毕！")
            return target_info
            
        print("[-] 接口返回成功，但没有检测到目标 (results 为空)。")
        return None

    elif response.status_code == 422:
        print("[-] Pydantic 数据校验失败 (Status 422):")
        print(response.json())
    else:
        print(f"[-] 请求失败! Status Code: {response.status_code}")
        print(f"[-] 错误详情: {response.text}")



def generate_formatted_filename(absolute_path):
    # 1. 校验路径是否为有效文件
    if not os.path.isfile(absolute_path):
        raise FileNotFoundError(f"错误：文件不存在或不是有效文件 '{absolute_path}'")
    
    # 2. 提取原文件的后缀名 (例如从 .../capture_002.jpg 中提取出 .jpg)
    _, ext = os.path.splitext(absolute_path)
    if not ext:
        ext = ".jpg"  # 如果原文件没有后缀，给一个默认后缀
        
    # 3. 生成时间戳：年月日时分秒 (YYYYMMDDHHMMSS)
    time_str = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    
    # 4. 生成唯一编号 (此处使用 uuid 的前 6 位，足以避免同一秒内的命名冲突)
    unique_id = uuid.uuid4().hex[:6]
    
    # 5. 拼接新文件名并返回
    new_filename = f"{time_str}_{unique_id}{ext}"
    
    return new_filename

if __name__ == "__main__":
    # ==================== 基础配置区 ====================
    TEST_IMAGE_PATH = "D:/BIT_CV/Location/capture_pic/captures/10米/capture_002.jpg"
    CSV_FILE_PATH = "tb_device_202603130925.csv"
    TARGET_DEV_ADDR = "172.168.2.35"

    try:
        df = pd.read_csv(CSV_FILE_PATH, encoding='gbk')
    except Exception as e:
        print(f"[-] 读取 CSV 文件失败，请检查文件名和路径！错误: {e}")
        exit()

    device_row = df[df['dev_addr'] == TARGET_DEV_ADDR]
    
    if device_row.empty:
        print(f"[-] 在 CSV 中找不到设备地址(dev_addr): {TARGET_DEV_ADDR} 的数据，请检查！")
        exit()

    device_data = device_row.iloc[0]

    extracted_dev_id = str(device_data['dev_id'])

    lat = float(device_data['latitude'])
    lng = float(device_data['longitude'])
    elevation = float(device_data['elevation'])
    pitch = float(device_data['pitch'])
    direction = float(device_data['direction'])
    gps_coords = {"lat": lat, "lng": lng, "alt": elevation}
    fence_coords = parse_line_to_fence_coords(device_data['line'])

    target_info = run_suspect_localization(
        image_path=TEST_IMAGE_PATH,
        gps_coords=gps_coords,
        elevation=elevation,
        pitch=pitch,
        direction=direction,
        dev_id = extracted_dev_id,
        fence_coords=fence_coords
    )

    if target_info is not None:
        target_info['dev_id'] = extracted_dev_id
    else:
        target_info = {"dev_id": extracted_dev_id, "message": "接口请求成功，但未检测到目标"}
    new_name = generate_formatted_filename(TEST_IMAGE_PATH)
    target_info['imageUrl'] =  new_name
    target_info['eventTime'] = datetime.datetime.now()
    print(target_info)
