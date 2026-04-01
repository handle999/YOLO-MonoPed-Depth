from flask import Flask, send_from_directory
import os

app = Flask(__name__)

# 配置图片存储路径（需替换为实际有效路径）

IMAGE_FOLDER = 'D:/BIT_CV/Location/capture_pic/captures/10米'  # Windows路径示例
#IMAGE_FOLDER = r'C:\Users\dell\Desktop\图片'  # Windows路径示例
# IMAGE_FOLDER = '/home/user/images/10m'  # Linux/Mac路径示例

@app.route('/imageUrl/<filename>')
def serve_image(filename):
    """
    通过URL访问图片的路由函数
    示例：http://localhost:5782/imageUrl/capture_002.jpg
    """
    # 路径存在性校验
    if not os.path.exists(IMAGE_FOLDER):
        return f"错误：图片文件夹 {IMAGE_FOLDER} 不存在", 404
    
    # 构建完整文件路径
    file_path = os.path.join(IMAGE_FOLDER, filename)
    
    # 文件有效性校验
    if not os.path.isfile(file_path):
        return f"错误：文件 {filename} 不存在", 404
    
    # 返回图片文件
    return send_from_directory(IMAGE_FOLDER, filename)

if __name__ == '__main__':
    # 启动服务器（默认端口5000）
    app.run(host='0.0.0.0', port=5782)
