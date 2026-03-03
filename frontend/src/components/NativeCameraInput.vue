<template>
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
      <div class="input-item"><label>经度 (Lng)</label><input v-model.number="cameraConfig.extrinsics.lng" type="number" step="0.00001"></div>
      <div class="input-item"><label>纬度 (Lat)</label><input v-model.number="cameraConfig.extrinsics.lat" type="number" step="0.00001"></div>
      <div class="input-item"><label>海拔 (Alt - m)</label><input v-model.number="cameraConfig.extrinsics.alt" type="number" step="0.1"></div>
      <div class="input-item"><label>离地高度 (m)</label><input v-model.number="cameraConfig.extrinsics.height" type="number" step="0.1"></div>
    </div>
    <div class="input-grid">
      <div class="input-item"><label>俯仰角 (Pitch)</label><input v-model.number="cameraConfig.extrinsics.pitch" type="number" step="0.01"></div>
      <div class="input-item"><label>偏航角 (Yaw)</label><input v-model.number="cameraConfig.extrinsics.yaw" type="number" step="0.01"></div>
      <div class="input-item"><label>翻滚角 (Roll)</label><input v-model.number="cameraConfig.extrinsics.roll" type="number" step="0.01"></div>
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
</template>

<script setup>
defineProps({
  cameraConfig: Object
});
</script>
