import requests
import datetime
import uuid
import os

def test_image_api(base_url, target_filename):
    """
    请求接口并下载图片，按【年月日时分秒_唯一编号】格式重命名保存
    """
    url = f"{base_url}/imageUrl/{target_filename}"
    
    try:
        response = requests.get(url)
        
        # 接口返回 200 成功时才处理
        if response.status_code == 200:
            # 1. 生成时间戳：年月日时分秒 (YYYYMMDDHHMMSS)
            time_str = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            
            # 2. 生成唯一编号 (此处使用 uuid 的前 6 位，你也可以改为随机数或递增序号)
            unique_id = uuid.uuid4().hex[:6]
            
            # 3. 提取原文件后缀名 (如 .jpg)
            _, ext = os.path.splitext(target_filename)
            if not ext:
                ext = ".jpg" # 默认后缀
                
            # 4. 拼接新文件名：年月日时分秒_唯一编号.后缀
            new_filename = f"{time_str}_{unique_id}{ext}"
            
            # 5. 保存图片到当前运行目录
            with open(new_filename, 'wb') as f:
                f.write(response.content)
            
            # 只输出要求的格式
            print(new_filename)
            
    except Exception:
        # 按要求保持输出纯净，发生连接错误时静默或自行补充异常打印
        pass

def main():
    SERVER_URL = "http://127.0.0.1:5782"
    TEST_FILE_NAME = "capture_002.jpg"

    print(test_image_api(SERVER_URL, TEST_FILE_NAME))


if __name__ == '__main__':
    # 配置测试地址和测试文件名（确保服务端文件夹里有这个文件）
    SERVER_URL = "http://127.0.0.1:5782"
    TEST_FILE_NAME = "capture_002.jpg"

    test_image_api(SERVER_URL, TEST_FILE_NAME)