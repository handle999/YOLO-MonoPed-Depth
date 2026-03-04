```text
frontend/                       # [前端] Vue 3 + Vite 项目
├── public/                     # 静态资源 (如图标 favicon 等)
├── src/
│   ├── api/                    # [网络请求层]
│   │   ├── localization.js     # 8001 端口：原生系统 API 请求封装
│   │   └── sys_api.js          # 8002 端口：指挥调度系统 (Sys) 接口测试封装
│   ├── assets/                 # 内部静态资产 (如本地图片、基础样式文件等)
│   ├── components/             # [UI 组件库] 彻底解耦的原子化/模块化组件
│   │   ├── HelloWorld.vue      # (Vue 默认示例组件，可删除)
│   │   ├── ImageModal.vue      # 悬浮组件：全屏大图查看与下载
│   │   ├── MapDisplay.vue      # 右侧主视图：Leaflet 地图渲染与目标多边形标记
│   │   ├── ModelSelect.vue     # 表单组件：YOLO 目标检测与姿态估计模型下拉选择
│   │   ├── NativeCameraInput.vue # 表单组件：8001 原生系统的复杂相机参数(深度嵌套)
│   │   ├── ResultGallery.vue   # 左侧展示卡片：AI检测/骨架/雷达视图展示
│   │   └── SysCameraInput.vue  # 表单组件：8002 Sys 系统的扁平化相机参数
│   ├── views/                  # [视图层] 页面级路由组件
│   │   ├── NativeView.vue      # 系统原本视图页面 (包含模型选择、图像上传与地图渲染)
│   │   └── SysView.vue         # 调度接口测试沙盒 (测试指挥调度系统 /pull/detection 和 /pull/local)
│   ├── App.vue                 # [核心骨架] 主入口外壳，仅负责 Header 渲染和 Tabs 视图切换
│   ├── main.js                 # 核心入口文件 (挂载 Vue 实例与 Leaflet 全局样式)
│   └── style.css               # 主题与全局样式定义
├── index.html                  # HTML 基础模板
├── package.json                # 前端依赖配置 (vue, axios, vue-leaflet 等)
└── vite.config.js              # Vite 构建与代理配置
```

# 1. env

## 1.1. check

如果没有安装 Node，Windows 建议去 [官网](https://nodejs.org) 下载 LTS 版本，注意勾选 `Add to PATH`

```shell
# 1. 检查 Node.js 和 npm
node -v
v22.14.0
npm -v
10.9.2

# 2.检查镜像源
npm config get registry
https://registry.npmjs.org/
# 可更换，也可不换（我没换）
npm config set registry https://registry.npmmirror.com
```

## 1.2. build

```shell
# 1. 创建项目脚手架
# npm: Node Package Manager，Node 的包管理工具，一切的起点。
# create: 这是一个 npm 的特殊指令（等同于 npm init）。它会去远程仓库拉取一个“生成器”。
# vite@latest: 我们指定的生成器工具是 Vite (发音类似 "veet")，@latest 表示使用最新版本。Vite 是现在 Vue 的御用构建工具。
# frontend: 这是你想要创建的文件夹名称。执行后，会在当前目录下生成一个名为 frontend 的文件夹。
# --: 这是一个分隔符。意思说：“后面的参数不是给 npm 用的，是传给 vite 这个工具用的”。
# --template vue: 告诉 Vite，我要创建一个 Vue 模板的项目（而不是 React 或其他）。
# 总结：这句话的意思是“用最新的 Vite 工具，帮我生成一个名为 frontend 的 Vue 项目文件夹”。
npm create vite@latest frontend -- --template vue

# 2. 进入目录
cd frontend

# 3. 安装基础依赖
# 读取 package.json，把所有需要的库从互联网下载下来，存放到一个自动生成的 node_modules 文件夹里
npm install

# 4. 安装我们项目需要的额外库
# axios: 一个专门用来发 HTTP 请求的库（类似于以前 jQuery 的 ajax）。我们要用它把图片发给 Python 后端。
# leaflet: 一个非常流行的开源地图核心库（JS版）。
# @vue-leaflet/vue-leaflet: 因为直接在 Vue 里操作 DOM 用 Leaflet 比较麻烦，这个库把 Leaflet 封装成了 Vue 的组件（比如 <l-map>, <l-marker>），让你能用 Vue 的方式写地图。
npm install axios leaflet @vue-leaflet/vue-leaflet

# 5. 启动开发服务器
npm run dev

# 当然要先去后端把main运行起来
```

# 2. dev

## 2.1. map

```shell
# 高德（火星坐标）
## 高德矢量底图
https://webrd04.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=7&x={x}&y={y}&z={z}
## 高德卫星影像
https://webst01.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}

## 百度地图（百度坐标）
#城市街道瓦片
http://online{s}.map.bdimg.com/onlinelabel/?qt=tile&x={x}&y={y}&z={z}
http://online{s}.map.bdimg.com/tile/?qt=vtile&x={x}&y={y}&z={z}&styles=pl&scaler=1&udt=
##道路和标记
http://online{s}.map.bdimg.com/tile/?qt=tile&x={x}&y={y}&z={z}&styles=sl
##卫星影像
https://maponline{s}.bdimg.com/starpic/?qt=satepc&u=x={x};y={y};z={z};v=009;type=sate&fm=46