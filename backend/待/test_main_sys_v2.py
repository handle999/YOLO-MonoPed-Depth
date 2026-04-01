import requests
import json


BASE_URL = "http://127.0.0.1:8112"
#TEST_IMAGE_PATH = "D:/BIT_CV/Location/capture_pic/captures/10米/capture_002.jpg"
# TEST_IMAGE_PATH = "D:/BIT_CV/Location/capture_pic/captures/10米/capture_002.jpg"
TEST_IMAGE_PATH =  "E:/School/2026/WeiTong/Location修改新疆用/Location修改新疆用/capture_pic/captures/capture_286.jpg"

def test_pull_fence_distance():
    #print("\n--- [3] 测试围栏距离计算接口 (/xjzhdd/alarmEvent/pull/fence_distance) ---")
    
    url = f"{BASE_URL}/xjzhdd/alarmEvent/pull/disbyip"   
    test_ip = "172.168.0.175"
    payload = {
        "imageUrl": TEST_IMAGE_PATH,
        "ip": test_ip,
        "bnd": {
            "x": 0.5,
            "y": 0.5,
            "width": 0.1,
            "height": 0.3
        }
    }

    try:
        response = requests.post(url, json=payload, timeout=15)
        print(f"状态码: {response.status_code}")
        print("返回结果:", json.dumps(response.json(), indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"请求失败: {e}")


if __name__ == "__main__":
    test_pull_fence_distance()