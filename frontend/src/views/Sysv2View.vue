<template>
  <div class="content-wrapper" style="width: 100%; height: 100%;">
    <div class="sidebar">
      <Sysv2CameraInput :config="sysv2Config" />

      <div class="card upload-card">
        <div class="card-header">🖼️ 图像源 & 目标预览</div>
        
        <div class="input-grid" style="margin-bottom: 10px;">
          <div class="input-item" style="grid-column: span 2;">
            <label>图片来源选项</label>
            <select v-model="imageSourceType" class="mode-select">
              <option value="upload">📁 本地文件上传</option>
              <option value="url">🌐 网络 URL 地址</option>
            </select>
          </div>
        </div>

        <div v-if="imageSourceType === 'upload'">
          <input type="file" @change="handleFileUpload" accept="image/*" class="file-input" />
        </div>
        <div v-else class="input-item">
          <input v-model="imageUrl" type="text" placeholder="输入图片 HTTP 地址" @blur="loadImageFromUrl" />
        </div>

        <div style="margin-top: 10px; font-size: 0.85rem; color: #94a3b8;">
          当前检测到分辨率: {{ sysv2Config.image_w }} x {{ sysv2Config.image_h }}
        </div>

        <div v-if="previewSrc" class="image-preview-container">
          <img :src="previewSrc" alt="Source Preview" class="preview-img" />
          <div class="bbox-overlay" :style="bboxStyle">
            <span class="bbox-label">Target</span>
          </div>
        </div>

        <button 
          @click="submitAnalysis" 
          class="run-btn" 
          :class="{ 'btn-disabled': loading || !previewSrc }"
          :disabled="loading || !previewSrc"
          style="margin-top: 15px;"
        >
          {{ loading ? '🚀 测距计算中...' : '📍 开始电子围栏测距' }}
        </button>
      </div>

      <div class="card">
        <div class="card-header">📄 测距结果 (JSON)</div>
        <pre class="json-output">{{ jsonOutput }}</pre>
      </div>
    </div>

    <MapDisplay 
      ref="mapDisplayRef" 
      :cameraConfig="mapCameraConfig" 
      :apiResults="apiResults" 
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, nextTick } from 'vue';
import axios from 'axios';
import Sysv2CameraInput from '../components/Sysv2CameraInput.vue';
import MapDisplay from '../components/MapDisplay.vue';

// --- 全局状态 ---
const loading = ref(false);
const imageSourceType = ref('upload');
const currentImageBase64 = ref('');
const imageUrl = ref('');
const jsonOutput = ref('等待请求...');

const apiResults = ref([]);
const mapDisplayRef = ref(null);

// 为了让 MapDisplay 不报错，造一个假的相机中心点
const mapCameraConfig = reactive({
  extrinsics: { lat: 40.052, lng: 116.280 } 
});

// --- 8112 请求参数模型 ---
const sysv2Config = reactive({
  ip: '172.168.0.175',
  camera_type: 'bullet',
  terrain_mode: 'flat',
  image_w: 1920,
  image_h: 1080,
  bnd: { x: 1264, y: 462, width: 40, height: 89 },
  realtime_yaw: -8.0,
  realtime_pitch: -12.0,
  realtime_focal: 2.5
});

// --- 图片预览与 BBox 动态样式 ---
// 根据所选模式，动态决定预览的图片源
const previewSrc = computed(() => {
  return imageSourceType.value === 'upload' ? currentImageBase64.value : imageUrl.value;
});

// 核心计算：将绝对像素转换为百分比，完美适应左侧边栏的缩放
const bboxStyle = computed(() => {
  if (!sysv2Config.image_w || !sysv2Config.image_h) return { display: 'none' };
  
  const { x, y, width, height } = sysv2Config.bnd;
  
  // 防止越界导致的 CSS 渲染错误
  const safeX = Math.max(0, x);
  const safeY = Math.max(0, y);
  const safeW = Math.min(width, sysv2Config.image_w - safeX);
  const safeH = Math.min(height, sysv2Config.image_h - safeY);

  return {
    left: `${(safeX / sysv2Config.image_w) * 100}%`,
    top: `${(safeY / sysv2Config.image_h) * 100}%`,
    width: `${(safeW / sysv2Config.image_w) * 100}%`,
    height: `${(safeH / sysv2Config.image_h) * 100}%`,
  };
});

// --- 图片处理逻辑 ---
const extractImageSize = (src) => {
  const img = new Image();
  img.onload = () => {
    sysv2Config.image_w = img.naturalWidth;
    sysv2Config.image_h = img.naturalHeight;
  };
  img.src = src;
};

const handleFileUpload = (event) => {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (e) => {
    currentImageBase64.value = e.target.result;
    extractImageSize(e.target.result);
  };
  reader.readAsDataURL(file);
};

const loadImageFromUrl = () => {
  if (imageUrl.value) {
    extractImageSize(imageUrl.value);
  }
};

// --- 核心业务逻辑 ---
const submitAnalysis = async () => {
  loading.value = true;
  jsonOutput.value = "请求中...";
  apiResults.value = []; 

  const payload = {
    ip: sysv2Config.ip,
    image_w: sysv2Config.image_w,
    image_h: sysv2Config.image_h,
    bnd: sysv2Config.bnd,
    terrain_mode: sysv2Config.terrain_mode,
    camera_type: sysv2Config.camera_type
  };

  if (sysv2Config.camera_type === 'ptz') {
    payload.realtime_yaw = sysv2Config.realtime_yaw;
    payload.realtime_pitch = sysv2Config.realtime_pitch;
    payload.realtime_focal = sysv2Config.realtime_focal;
  }

  if (imageSourceType.value === 'upload' && currentImageBase64.value) {
    payload.imageData = currentImageBase64.value;
  } else if (imageSourceType.value === 'url' && imageUrl.value) {
    // URL 模式如果后端以后支持的话可以扩展
  }

  try {
    const response = await axios.post('http://127.0.0.1:8112/xjzhdd/alarmEvent/pull/fence_distance', payload);
    const resData = response.data;
    jsonOutput.value = JSON.stringify(resData, null, 2);
    
    if (resData.code === 200 && resData.data) {
      const data = resData.data;
      
      // 1.[修复] 显示相机位置，不再伪造，直接使用后端传来的真实相机位置
      if (data.camera_lat && data.camera_lng) {
        mapCameraConfig.extrinsics.lat = data.camera_lat;
        mapCameraConfig.extrinsics.lng = data.camera_lng;
      } else {
        // 兼容容错：如果没有传回来，就随便给一个实际位置左下角的虚假位置
        mapCameraConfig.extrinsics.lat = data.person_lat - 0.0001;
        mapCameraConfig.extrinsics.lng = data.person_lng - 0.0001;
      }

      // 2. 构造给地图的数据，包含围栏坐标
      apiResults.value = [{
        target_id: 'person_01',
        suspect_geo_location: { lat: data.person_lat, lng: data.person_lng },
        computation_details: { 
          straight_distance: data.distance_to_fence || 0,
          cam_distance: data.distance_from_camera
        },
        suspect_region_polygon: [],
        // [修复为 Leaflet 规范] Python 返回的是 [lat, lng]，直接透传即可
        fence_line: data.fence_coords || [] 
      }];

      nextTick(() => {
        if (mapDisplayRef.value) mapDisplayRef.value.fitBounds();
      });
    }
  } catch (error) {
    console.error("请求失败:", error);
    jsonOutput.value = error.response ? JSON.stringify(error.response.data, null, 2) : error.message;
  } finally {
    loading.value = false;
  }
};
</script>
