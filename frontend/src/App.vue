<template>
  <div class="app-container">
    <header class="header">
      <h2>单目视觉定位系统 (Monocular Localization)</h2>
    </header>

    <div class="content-wrapper">
      <div class="sidebar">
        <ConfigForm 
          :modelConfig="modelConfig" 
          :cameraConfig="cameraConfig" 
          :loading="loading" 
          :hasImage="!!currentImageBase64"
          @file-selected="handleFileUpload"
          @submit="submitAnalysis"
        />
        <ResultGallery 
          :demoImages="demoImages" 
          @open-modal="openModal" 
        />
      </div>

      <MapDisplay 
        ref="mapDisplayRef" 
        :cameraConfig="cameraConfig" 
        :apiResults="apiResults" 
      />
    </div>

    <ImageModal 
      :show="showModal" 
      :src="modalImageSrc" 
      :filename="modalImageName" 
      @close="showModal = false" 
    />
  </div>
</template>

<script setup>
import { ref, reactive, nextTick } from 'vue';
import { analyzeLocalizationAPI } from './api/localization.js';

// 引入子组件
import ConfigForm from './components/ConfigForm.vue';
import ResultGallery from './components/ResultGallery.vue';
import MapDisplay from './components/MapDisplay.vue';
import ImageModal from './components/ImageModal.vue';

// --- 全局状态 ---
const loading = ref(false);
const currentImageBase64 = ref(null);
const apiResults = ref([]);
const demoImages = reactive({ detection: '', skeleton: '', radar: '' });

// --- 组件引用 ---
const mapDisplayRef = ref(null);

// --- 弹窗状态 ---
const showModal = ref(false);
const modalImageSrc = ref('');
const modalImageName = ref('');

// --- 核心配置对象 (被双向绑定传递给 ConfigForm) ---
const modelConfig = reactive({ detModel: 'yolo26l', poseModel: 'yolo26l-pose' });
const cameraConfig = reactive({
  deviceId: "cam_001", terrain: "mount",
  extrinsics: { lat: 22.54321, lng: 114.05755, alt: 15.0, height: 3.5, pitch: -15.0, yaw: 0.0, roll: 0.0 },
  resolution: { width: 1920, height: 1080 },
  intrinsics: { focal_length: 6.0, sensor_width: 5.37 },
  distortion: { k1: -0.1, k2: 0.05, p1: 0, p2: 0, k3: 0 }
});

// --- 事件处理方法 ---
const handleFileUpload = (event) => {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (e) => currentImageBase64.value = e.target.result;
  reader.readAsDataURL(file);
};

const openModal = (src, filename) => {
  modalImageSrc.value = src;
  modalImageName.value = filename;
  showModal.value = true;
};

// --- 核心业务逻辑 ---
const submitAnalysis = async () => {
  loading.value = true;
  apiResults.value = []; 

  try {
    const data = await analyzeLocalizationAPI(cameraConfig, modelConfig, currentImageBase64.value);
    
    if (data.code === 200) {
      apiResults.value = data.data.results;
      demoImages.detection = data.demo_images.detection_image;
      demoImages.skeleton = data.demo_images.skeleton_image; 
      demoImages.radar = data.demo_images.radar_image;
      
      // 触发子组件的自适应边界方法
      nextTick(() => {
        if (mapDisplayRef.value) mapDisplayRef.value.fitBounds();
      });
    }
  } catch (error) {
    console.error("请求失败:", error);
    let errorMsg = "请求失败！请检查后端状态。";
    if (error.response?.data) {
      const detail = error.response.data.detail || error.response.data.message;
      if (detail) errorMsg = `后端拒绝了请求 (状态码 ${error.response.status}):\n${JSON.stringify(detail, null, 2)}`;
    } else {
       errorMsg = error.message || errorMsg;
    }
    alert(errorMsg);
  } finally {
    loading.value = false;
  }
};
</script>
