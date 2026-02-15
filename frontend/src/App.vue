<template>
  <div class="app-container">
    <header class="header">
      <h2>单目视觉定位系统 (Monocular Localization)</h2>
    </header>

    <div class="content-wrapper">
      <div class="sidebar">
        
        <div class="card config-card">
          <div class="card-header">📷 相机参数配置</div>
          
          <span class="group-title">0. 基础信息 (Basic)</span>
          <div class="input-grid">
            <div class="input-item" style="grid-column: span 2;">
              <label>设备ID (Device ID)</label>
              <input v-model="cameraConfig.deviceId" type="text">
            </div>
            <div class="input-item">
              <label>检测模式 (Terrain)</label>
              <select v-model="cameraConfig.terrain" class="mode-select">
                <option value="flat">平地 (flat)</option>
                <option value="mount">山地 (mount)</option>
              </select>
            </div>
          </div>

          <span class="group-title">1. 相机外参 (Extrinsics)</span>
          <div class="input-grid">
            <div class="input-item">
              <label>纬度 (Lat)</label>
              <input v-model.number="cameraConfig.extrinsics.lat" type="number" step="0.00001">
            </div>
            <div class="input-item">
              <label>经度 (Lng)</label>
              <input v-model.number="cameraConfig.extrinsics.lng" type="number" step="0.00001">
            </div>
            <div class="input-item">
              <label>海拔 (Alt - m)</label>
              <input v-model.number="cameraConfig.extrinsics.alt" type="number" step="0.1">
            </div>
            <div class="input-item">
              <label>离地高度 (m)</label>
              <input v-model.number="cameraConfig.extrinsics.height" type="number" step="0.1">
            </div>
          </div>
          
          <div class="input-grid">
            <div class="input-item">
              <label>俯仰角 (Pitch)</label>
              <input v-model.number="cameraConfig.extrinsics.pitch" type="number" step="1">
            </div>
            <div class="input-item">
              <label>偏航角 (Yaw)</label>
              <input v-model.number="cameraConfig.extrinsics.yaw" type="number" step="1">
            </div>
            <div class="input-item">
              <label>翻滚角 (Roll)</label>
              <input v-model.number="cameraConfig.extrinsics.roll" type="number" step="1">
            </div>
          </div>

          <span class="group-title" style="margin-top: 15px;">2. 相机内参 (Intrinsics)</span>
          <div class="input-grid">
            <div class="input-item">
              <label>图像宽 (px)</label>
              <input v-model.number="cameraConfig.resolution.width" type="number" step="1">
            </div>
            <div class="input-item">
              <label>图像高 (px)</label>
              <input v-model.number="cameraConfig.resolution.height" type="number" step="1">
            </div>
          </div>

          <div class="input-grid">
            <div class="input-item">
              <label>物理焦距 (mm)</label>
              <input v-model.number="cameraConfig.intrinsics.focal_length" type="number" step="0.1">
            </div>
            <div class="input-item">
              <label>传感器宽 (mm)</label>
              <input v-model.number="cameraConfig.intrinsics.sensor_width" type="number" step="0.01">
            </div>
          </div>
          <div class="input-item">
            <label>畸变系数 (Distortion: k1, k2, p1, p2, k3)</label>
            <div style="display: flex; gap: 5px;">
              <input v-model.number="cameraConfig.distortion.k1" type="number" step="0.01" placeholder="k1" title="k1">
              <input v-model.number="cameraConfig.distortion.k2" type="number" step="0.01" placeholder="k2" title="k2">
              <input v-model.number="cameraConfig.distortion.p1" type="number" step="0.01" placeholder="p1" title="p1">
              <input v-model.number="cameraConfig.distortion.p2" type="number" step="0.01" placeholder="p2" title="p2">
              <input v-model.number="cameraConfig.distortion.k3" type="number" step="0.01" placeholder="k3" title="k3">
            </div>
          </div>
        </div>

        <div class="card upload-card">
          <div class="card-header">🖼️ 图像源</div>
          <input type="file" @change="handleFileUpload" accept="image/*" class="file-input" />
          <button 
            @click="submitAnalysis" 
            class="run-btn" 
            :class="{ 'btn-disabled': !currentImageBase64 || loading }"
            :disabled="!currentImageBase64 || loading"
          >
            {{ loading ? '🚀 计算中...' : '开始定位分析' }}
          </button>
        </div>

        <div class="card result-card" v-if="demoImages.detection">
          <div class="card-header">📊 分析结果视图</div>
          
          <div class="img-box" @click="openModal(demoImages.detection, 'AI_Detection_Result.jpg')">
            <span class="img-label">AI 检测视图 (点击放大)</span>
            <img :src="demoImages.detection" class="result-img" />
            <div class="click-hint">🔍 点击放大 / 下载</div>
          </div>
          
          <div class="img-box" style="margin-top: 15px;" @click="openModal(demoImages.skeleton, 'Skeleton_Result.jpg')">
            <span class="img-label">骨架分析视图 (Skeleton)</span>
            <img :src="demoImages.skeleton" class="result-img" />
            <div class="click-hint">🔍 点击放大 / 下载</div>
          </div>

          <div class="img-box" style="margin-top: 15px;" @click="openModal(demoImages.radar, 'Lidar_Map_Result.jpg')">
            <span class="img-label">俯视雷达视图 (点击放大)</span>
            <img :src="demoImages.radar" class="result-img" />
            <div class="click-hint">🔍 点击放大 / 下载</div>
          </div>
        </div>

      </div>

      <div class="map-container">
        
        <l-map 
          ref="mapRef" 
          v-model:zoom="zoom" 
          :center="center" 
          :use-global-leaflet="false" 
          :max-zoom="25"
        >
          
          <l-tile-layer
            url="http://mt0.google.com/vt/lyrs=y&hl=en&x={x}&y={y}&z={z}"
            layer-type="base"
            name="Google Hybrid"
            :max-native-zoom="20"
            :max-zoom="25"
          ></l-tile-layer>

          <l-control-scale position="bottomright" :metric="true" :imperial="false"></l-control-scale>

          <l-control position="bottomright">
            <div class="zoom-indicator">
              <div>Level: {{ zoom.toFixed(1) }}</div>
            </div>
          </l-control>

          <l-marker :lat-lng="[cameraConfig.extrinsics.lat, cameraConfig.extrinsics.lng]">
            <l-tooltip :options="{ permanent: true, direction: 'top' }">📷 相机位置</l-tooltip>
          </l-marker>

          <template v-for="target in apiResults" :key="target.target_id">
            <l-marker :lat-lng="[target.suspect_geo_location.lat, target.suspect_geo_location.lng]">
              <l-icon class-name="custom-target-icon">
                <div class="target-badge">{{ target.target_id.split('_')[1] }}</div>
              </l-icon>
              <l-popup>
                <div class="popup-content">
                  <strong>ID: {{ target.target_id }}</strong><hr/>
                  <div>距离: {{ target.computation_details.straight_distance.toFixed(2) }}m</div>
                  <div>Lat: {{ target.suspect_geo_location.lat.toFixed(6) }}</div>
                  <div>Lng: {{ target.suspect_geo_location.lng.toFixed(6) }}</div>
                </div>
              </l-popup>
            </l-marker>

            <l-polygon 
              :lat-lngs="formatPolygon(target.suspect_region_polygon)"
              color="#00ff00" :weight="2" fill-color="#00ff00" :fill-opacity="0.3"
            />
          </template>

        </l-map>
      </div>
    </div>

    <div class="image-modal" v-if="showModal" @click.self="closeModal">
      <img :src="modalImageSrc" class="modal-content" />
      <div class="modal-actions">
        <button class="modal-btn btn-download" @click="downloadCurrentImage">⬇️ 下载原图</button>
        <button class="modal-btn btn-close" @click="closeModal">❌ 关闭</button>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, reactive, nextTick } from 'vue';
import axios from 'axios';
// 引入地图组件
import { LMap, LTileLayer, LMarker, LPolygon, LPopup, LIcon, LTooltip, LControlScale, LControl } from "@vue-leaflet/vue-leaflet";
import "leaflet/dist/leaflet.css"; // 引入 leaflet 基础样式

// [关键] 引入分离后的 CSS 文件 (请确保 src/style.css 存在)
import './style.css';

// --- 状态变量 ---
const loading = ref(false);
const currentImageBase64 = ref(null);
const mapRef = ref(null); // 地图实例引用

// --- Modal 状态 ---
const showModal = ref(false);
const modalImageSrc = ref('');
const modalImageName = ref('download.jpg');

// --- 相机配置 (重构为嵌套结构，支持所有参数输入) ---
const cameraConfig = reactive({
  // 基础信息
  deviceId: "cam_001",
  terrain: "mount",
  
  // 外参
  extrinsics: {
    lat: 22.54321, 
    lng: 114.05755,
    alt: 15.0,
    height: 3.5,
    pitch: -15.0,
    yaw: 0.0,
    roll: 0.0
  },
  
  // 内参 - 分辨率
  resolution: {
    width: 1920,
    height: 1080
  },
  
  // 内参 - 硬件
  intrinsics: {
    focal_length: 6.0,
    sensor_width: 5.37
  },
  
  // 内参 - 畸变 (默认值)
  distortion: {
    k1: -0.1, k2: 0.05, p1: 0, p2: 0, k3: 0
  }
});

// 地图初始状态
const zoom = ref(18);
const center = ref([22.54321, 114.05755]);

// 后端返回的数据
const apiResults = ref([]);
const demoImages = reactive({ detection: '', skeleton: '', radar: '' });

// --- 方法定义 ---

// 1. 图片查看器相关方法
const openModal = (src, filename) => {
  if (!src) return;
  modalImageSrc.value = src;
  modalImageName.value = filename;
  showModal.value = true;
};

const closeModal = () => {
  showModal.value = false;
};

const downloadCurrentImage = () => {
  const link = document.createElement('a');
  link.href = modalImageSrc.value;
  link.download = modalImageName.value;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

// 2. 文件上传处理
const handleFileUpload = (event) => {
  const file = event.target.files[0];
  if (!file) return;
  
  // 转 Base64
  const reader = new FileReader();
  reader.onload = (e) => {
    currentImageBase64.value = e.target.result;
  };
  reader.readAsDataURL(file);
};

// 3. 辅助函数：把 API 的 polygon 转为 Leaflet 格式
const formatPolygon = (polyList) => {
  return polyList.map(p => [p.lat, p.lng]);
};

// 4. 核心：提交请求
const submitAnalysis = async () => {
  loading.value = true;
  apiResults.value = []; // 清空上次结果

  // 构造 JSON Payload
  // 由于 cameraConfig 结构已经重构，这里可以直接映射，或者显式赋值更清晰
  const payload = {
    req_id: `req_${Date.now()}`,
    terrain: cameraConfig.terrain,
    camera_info: {
      device_id: cameraConfig.deviceId,
      extrinsics: {
        gps: { 
          lat: cameraConfig.extrinsics.lat, 
          lng: cameraConfig.extrinsics.lng, 
          alt: cameraConfig.extrinsics.alt 
        },
        height_above_ground: cameraConfig.extrinsics.height,
        pose: { 
          pitch: cameraConfig.extrinsics.pitch, 
          yaw: cameraConfig.extrinsics.yaw, 
          roll: cameraConfig.extrinsics.roll 
        }
      },
      intrinsics: {
        image_resolution: { 
          width: cameraConfig.resolution.width, 
          height: cameraConfig.resolution.height 
        },
        hardware_specs: { 
          focal_length_mm: cameraConfig.intrinsics.focal_length, 
          sensor_width_mm: cameraConfig.intrinsics.sensor_width 
        },
        distortion_coeffs: [
          cameraConfig.distortion.k1,
          cameraConfig.distortion.k2,
          cameraConfig.distortion.p1,
          cameraConfig.distortion.p2,
          cameraConfig.distortion.k3
        ]  // 将对象转换为数组列表 [k1, k2, p1, p2, k3]
      }
    },
    image_data: {
      base64: currentImageBase64.value
    },
    targets: [] // 空数组表示让后端检测
  };

  try {
    // 发送请求到本地 FastAPI (注意端口 8001)
    const response = await axios.post('http://127.0.0.1:8001/api/v1/perception/suspect_localization', payload);
    
    const data = response.data;
    if (data.code === 200) {
      // 保存结果数据
      apiResults.value = data.data.results;
      // 显示返回的图片
      demoImages.detection = data.demo_images.detection_image;
      demoImages.skeleton = data.demo_images.skeleton_image; // 接收骨架图
      demoImages.radar = data.demo_images.radar_image;
      
      // 自动聚焦地图 (等待 DOM 更新后)
      nextTick(() => {
        fitBounds();
      });
    }
  } catch (error) {
    console.error("请求失败:", error);
    alert("请求失败！请检查：\n1. 后端(main.py)是否已启动？\n2. 端口是否为 8001？");
  } finally {
    loading.value = false;
  }
};

// 5. 自动缩放地图，使其包含所有点
const fitBounds = () => {
  if (!mapRef.value || apiResults.value.length === 0) return;
  
  // 收集所有坐标点 (注意数据源也变为了 cameraConfig.extrinsics)
  const points = [[cameraConfig.extrinsics.lat, cameraConfig.extrinsics.lng]]; 
  
  apiResults.value.forEach(t => {
    // 目标点
    points.push([t.suspect_geo_location.lat, t.suspect_geo_location.lng]);
    // 多边形顶点
    t.suspect_region_polygon.forEach(p => points.push([p.lat, p.lng]));
  });

  // 调用 Leaflet 原生方法 fitBounds
  const mapObject = mapRef.value.leafletObject;
  mapObject.fitBounds(points, { padding: [50, 50], maxZoom: 21 });
};
</script>
