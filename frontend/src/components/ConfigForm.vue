<template>
  <div class="card config-card">
    <div class="card-header">🤖 AI 模型配置</div>
    <div class="input-grid">
      <div class="input-item">
        <label>目标检测模型 (Detection)</label>
        <select v-model="modelConfig.detModel" class="mode-select">
          <optgroup label="YOLOv26 系列">
            <option value="yolo26n">YOLOv26 Nano</option>
            <option value="yolo26s">YOLOv26 Small</option>
            <option value="yolo26m">YOLOv26 Medium</option>
            <option value="yolo26l">YOLOv26 Large</option>
            <option value="yolo26x">YOLOv26 XLarge</option>
          </optgroup>
          <optgroup label="YOLOv12 系列">
            <option value="yolo12l">YOLOv12 Large</option>
            <option value="yolo12x">YOLOv12 XLarge</option>
          </optgroup>
          <optgroup label="YOLOv11 系列">
            <option value="yolo11n">YOLOv11 Nano</option>
            <option value="yolo11s">YOLOv11 Small</option>
            <option value="yolo11m">YOLOv11 Medium</option>
            <option value="yolo11l">YOLOv11 Large</option>
            <option value="yolo11x">YOLOv11 XLarge</option>
          </optgroup>
          <optgroup label="自定义/微调模型">
            <option value="fine_tuned_model">Fine Tuned Model</option>
          </optgroup>
        </select>
      </div>
      <div class="input-item">
        <label>姿态估计模型 (Pose)</label>
        <select v-model="modelConfig.poseModel" class="mode-select">
          <optgroup label="YOLOv26-Pose 系列">
            <option value="yolo26n-pose">YOLOv26 Nano Pose</option>
            <option value="yolo26s-pose">YOLOv26 Small Pose</option>
            <option value="yolo26m-pose">YOLOv26 Medium Pose</option>
            <option value="yolo26l-pose">YOLOv26 Large Pose</option>
            <option value="yolo26x-pose">YOLOv26 XLarge Pose</option>
          </optgroup>
          <optgroup label="YOLOv11-Pose 系列">
            <option value="yolo11n-pose">YOLOv11 Nano Pose</option>
            <option value="yolo11s-pose">YOLOv11 Small Pose</option>
            <option value="yolo11m-pose">YOLOv11 Medium Pose</option>
            <option value="yolo11l-pose">YOLOv11 Large Pose</option>
            <option value="yolo11x-pose">YOLOv11 XLarge Pose</option>
          </optgroup>
        </select>
      </div>
    </div>
  </div>

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
      <div class="input-item"><label>纬度 (Lat)</label><input v-model.number="cameraConfig.extrinsics.lat" type="number" step="0.00001"></div>
      <div class="input-item"><label>经度 (Lng)</label><input v-model.number="cameraConfig.extrinsics.lng" type="number" step="0.00001"></div>
      <div class="input-item"><label>海拔 (Alt - m)</label><input v-model.number="cameraConfig.extrinsics.alt" type="number" step="0.1"></div>
      <div class="input-item"><label>离地高度 (m)</label><input v-model.number="cameraConfig.extrinsics.height" type="number" step="0.1"></div>
    </div>
    
    <div class="input-grid">
      <div class="input-item"><label>俯仰角 (Pitch)</label><input v-model.number="cameraConfig.extrinsics.pitch" type="number" step="1"></div>
      <div class="input-item"><label>偏航角 (Yaw)</label><input v-model.number="cameraConfig.extrinsics.yaw" type="number" step="1"></div>
      <div class="input-item"><label>翻滚角 (Roll)</label><input v-model.number="cameraConfig.extrinsics.roll" type="number" step="1"></div>
    </div>

    <span class="group-title" style="margin-top: 15px;">2. 相机内参 (Intrinsics)</span>
    <div class="input-grid">
      <div class="input-item"><label>图像宽 (px)</label><input v-model.number="cameraConfig.resolution.width" type="number" step="1"></div>
      <div class="input-item"><label>图像高 (px)</label><input v-model.number="cameraConfig.resolution.height" type="number" step="1"></div>
    </div>

    <div class="input-grid">
      <div class="input-item"><label>物理焦距 (mm)</label><input v-model.number="cameraConfig.intrinsics.focal_length" type="number" step="0.1"></div>
      <div class="input-item"><label>传感器宽 (mm)</label><input v-model.number="cameraConfig.intrinsics.sensor_width" type="number" step="0.01"></div>
    </div>
    <div class="input-item">
      <label>畸变系数 (Distortion: k1, k2, p1, p2, k3)</label>
      <div style="display: flex; gap: 5px;">
        <input v-model.number="cameraConfig.distortion.k1" type="number" step="0.01" placeholder="k1">
        <input v-model.number="cameraConfig.distortion.k2" type="number" step="0.01" placeholder="k2">
        <input v-model.number="cameraConfig.distortion.p1" type="number" step="0.01" placeholder="p1">
        <input v-model.number="cameraConfig.distortion.p2" type="number" step="0.01" placeholder="p2">
        <input v-model.number="cameraConfig.distortion.k3" type="number" step="0.01" placeholder="k3">
      </div>
    </div>
  </div>

  <div class="card upload-card">
    <div class="card-header">🖼️ 图像源</div>
    <input type="file" @change="$emit('file-selected', $event)" accept="image/*" class="file-input" />
    <button 
      @click="$emit('submit')" 
      class="run-btn" 
      :class="{ 'btn-disabled': !hasImage || loading }"
      :disabled="!hasImage || loading"
    >
      {{ loading ? '🚀 计算中...' : '开始定位分析' }}
    </button>
  </div>
</template>

<script setup>
defineProps({
  modelConfig: Object,
  cameraConfig: Object,
  loading: Boolean,
  hasImage: Boolean
});
defineEmits(['file-selected', 'submit']);
</script>
