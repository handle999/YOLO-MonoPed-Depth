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

        # 创建顶部按钮框架（固定在左上角）
        self.button_frame = tk.Frame(self.root, bg="gray10")
        self.button_frame.place(x=10, y=10, width=200, height=50)  # 固定在左上角

        # 创建控制按钮（在框架内左对齐）
        self.capture_btn = ttk.Button(self.button_frame, text="拍照", command=self.capture_photo)
        self.capture_btn.pack(side=tk.LEFT, padx=5, pady=5)

        self.exit_btn = ttk.Button(self.button_frame, text="退出", command=self.stop)
        self.exit_btn.pack(side=tk.LEFT, padx=5, pady=5)

        # 创建视频显示区域（占据剩余空间）
        self.video_frame = tk.Frame(self.root, bg="black")
        # self.video_frame.place(x=10, y=70, width=780, height=480)  # 位于按钮下方
        self.video_frame.place(x=10, y=70)
        self.video_label = tk.Label(self.video_frame)
        self.video_label.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # 状态标签
        self.status_var = tk.StringVar(value="准备就绪")
        status_bar = tk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, bg="gray20", fg="white")
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=0, pady=0)

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
    #rtsp_url = "rtsp://admin:abc12345@172.168.0.151:554/Streaming/Channels/101"
    rtsp_url = "rtsp://admin:abc12345@172.168.0.175:554/Streaming/Channels/101"
    app = RTSPPhotoApp(rtsp_url)
    app.run()
