import cv2
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import os


class RTSPPhotoApp:
    def __init__(self, rtsp_url):
        self.rtsp_url = rtsp_url
        self.cap = cv2.VideoCapture(rtsp_url)
        self.is_running = True
        self.current_frame = None

        # 创建GUI
        self.root = tk.Tk()
        self.root.title("RTSP Photo Capture")
        self.root.geometry("800x600")

        # 创建视频显示区域
        self.video_label = tk.Label(self.root)
        self.video_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 创建控制按钮
        button_frame = tk.Frame(self.root)
        button_frame.pack(fill=tk.X, padx=10, pady=5)

        self.capture_btn = ttk.Button(button_frame, text="拍照", command=self.capture_photo)
        self.capture_btn.pack(side=tk.LEFT, padx=5)

        self.exit_btn = ttk.Button(button_frame, text="退出", command=self.stop)
        self.exit_btn.pack(side=tk.LEFT, padx=5)

        # 状态标签
        self.status_var = tk.StringVar(value="准备就绪")
        status_bar = tk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        # 创建保存目录
        self.save_dir = "captures"
        os.makedirs(self.save_dir, exist_ok=True)

        # 启动视频更新线程
        self.update_video()

    def update_video(self):
        """持续更新视频帧"""
        if self.is_running:
            ret, frame = self.cap.read()
            if ret:
                # 转换为RGB并调整大小
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                # frame = cv2.resize(frame, (640, 480))
                self.current_frame = frame.copy()

                # 转换为PIL图像
                img = Image.fromarray(frame)
                imgtk = ImageTk.PhotoImage(image=img)

                # 更新GUI
                self.video_label.imgtk = imgtk
                self.video_label.configure(image=imgtk)

            # 10毫秒后再次调用
            self.root.after(10, self.update_video)

    def capture_photo(self):
        """拍照并保存"""
        if self.current_frame is not None:
            # 生成文件名
            filename = f"capture_{len(os.listdir(self.save_dir)) + 1:03d}.jpg"
            save_path = os.path.join(self.save_dir, filename)

            # 保存图像
            img = Image.fromarray(cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB))
            img.save(save_path)

            self.status_var.set(f"照片已保存至: {save_path}")

    def stop(self):
        """停止程序"""
        self.is_running = False
        self.cap.release()
        self.root.destroy()

    def run(self):
        """启动主循环"""
        self.root.mainloop()


if __name__ == "__main__":
    # 替换为你的RTSP URL
    rtsp_url = "rtsp://admin:abc12345@172.168.0.103:554/Streaming/Channels/101"

    app = RTSPPhotoApp(rtsp_url)
    app.run()



# 174