```text
frontend/                       # [前端] Vue 3 + Vite 项目
├── public/                     # 静态资源 (如图标)
├── src/
│   ├── api/                    # [新增] 网络请求层
│   │   └── localization.js     # 封装统一的 Axios 请求逻辑，解耦业务
│   ├── assets/                 # 内部静态资产
│   ├── components/             # [新增] 拆分后的独立 UI 组件库
│   │   ├── ConfigForm.vue      # 左侧侧边栏：参数配置表单与图像上传
│   │   ├── ResultGallery.vue   # 左侧侧边栏：AI检测/骨架/雷达视图展示
│   │   ├── MapDisplay.vue      # 右侧主视图：Leaflet 地图渲染与目标标记
│   │   └── ImageModal.vue      # 悬浮组件：全屏大图查看与下载
│   ├── App.vue                 # [核心] 主页面容器 (仅负责状态管理与组件调度)
│   ├── main.js                 # 核心入口文件 (挂载 Vue 实例与 Leaflet 样式)
│   └── style.css               # [新增] 科技暗黑风主题全局样式
├── index.html                  # HTML 模板
├── package.json                # 前端依赖配置 (axios, leaflet 等)
└── vite.config.js              # Vite 构建配置
```

# 1. env

## 1.1. check
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

