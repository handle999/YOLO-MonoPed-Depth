<template>
  <div class="card config-card">
    <div class="card-header">📷 调度系统专用参数 (8002)</div>

    <span class="group-title">1. 地理位置与高度 (Location)</span>
    <div class="input-grid">
      <div class="input-item"><label>经度 (longitude)</label><input v-model.number="sysConfig.longitude" type="number" step="0.00001"></div>
      <div class="input-item"><label>纬度 (latitude)</label><input v-model.number="sysConfig.latitude" type="number" step="0.00001"></div>
      <div class="input-item"><label>高度 (height - m)</label><input v-model.number="sysConfig.height" type="number" step="0.1"></div>
    </div>
    
    <span class="group-title">2. 相机姿态 (Pose - 弧度单位 Radian)</span>
    <div class="input-grid">
      <div class="input-item"><label>俯仰角 (pitch)</label><input v-model.number="sysConfig.pitch" type="number" step="0.01"></div>
      <div class="input-item"><label>偏航角 (yaw)</label><input v-model.number="sysConfig.yaw" type="number" step="0.01"></div>
      <div class="input-item"><label>翻滚角 (roll)</label><input v-model.number="sysConfig.roll" type="number" step="0.01"></div>
    </div>

    <span class="group-title" style="margin-top: 15px;">3. 焦距参数 (Focal)</span>
    <div class="input-item">
      <label>焦距 (f)</label>
      <input v-model.number="sysConfig.f" type="number" step="0.001">
    </div>

  </div>
</template>

<script setup>
defineProps({
  sysConfig: Object
});
</script>
