import requests
import json
import base64
import os


BASE_URL = "http://127.0.0.1:8111"
TEST_IMAGE_PATH = "D:/BIT_CV/Location/capture_pic/captures/10米/capture_002.jpg"
#TEST_IMAGE_PATH = "D:/DQZ_clothes_detection/clothing_detection_results/both/1.jpg"

TEST_DEVICE_IP = "172.168.2.11"

def image_to_base64(image_path):
    """读取本地图片并转为 Base64 字符串"""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"找不到测试图片，请检查路径是否正确: {image_path}")
    
    with open(image_path, "rb") as f:
        # 读取字节流 -> Base64 编码 -> 解码为普通字符串以便放入 JSON
        return base64.b64encode(f.read()).decode('utf-8')

def test_pull_fence_distance():
    url = f"{BASE_URL}/xjzhdd/alarmEvent/pull/fence_distance"   
    
    try:
        #base64_str = image_to_base64(TEST_IMAGE_PATH)
        payload = {
            #"imageData": base64_str,
            "image_h": 200,
            "image_w": 1080,
            "ip": TEST_DEVICE_IP,
            "bnd": {
                "x": 0.5,
                "y": 0.5,
                "width": 0.1,
                "height": 0.3
            }
        }

        response = requests.post(url, json=payload, timeout=15)
        
        # 打印返回结果
        print(f"\n[+] 状态码: {response.status_code}")
        try:
            print("[+] 返回结果:")
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        except ValueError:
            print("[!] 服务器返回的不是有效的 JSON 格式:")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print(f"[-] 请求失败: 无法连接到服务器 {BASE_URL}，请检查 IP、端口以及防火墙设置。")
    except Exception as e:
        print(f"[-] 测试发生异常: {e}")

if __name__ == "__main__":
    test_pull_fence_distance()