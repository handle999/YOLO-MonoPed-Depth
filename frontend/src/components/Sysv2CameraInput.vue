<template>
  <div class="card config-card">
    <div class="card-header">⚙️ 围栏测距参数 (8111)</div>
    
    <span class="group-title">1. 设备与模式 (Device & Mode)</span>
    <div class="input-grid">
      <div class="input-item" style="grid-column: span 2;">
        <label>设备 IP (需存在于 CSV 中)</label>
        <input v-model="config.ip" type="text" placeholder="例如: 172.168.0.175">
      </div>
      <div class="input-item">
        <label>相机类型 (Camera Type)</label>
        <select v-model="config.camera_type" class="mode-select">
          <option value="bullet">固定枪机 (Bullet)</option>
          <option value="ptz">动态球机 (PTZ)</option>
        </select>
      </div>
      <div class="input-item">
        <label>地形模式 (Terrain)</label>
        <select v-model="config.terrain_mode" class="mode-select">
          <option value="flat">平地 (Flat)</option>
          <option value="mount">山地 (Mount)</option>
        </select>
      </div>
    </div>

    <div v-if="config.camera_type === 'ptz'" class="ptz-section" style="margin-top: 10px; padding: 10px; background: rgba(59, 130, 246, 0.1); border-radius: 8px; border: 1px dashed #3b82f6;">
      <span class="group-title" style="color: #60a5fa; margin-top: 0;">🎯 球机实时参数 (PTZ)</span>
      <div class="input-grid">
        <div class="input-item"><label>Pan (偏航偏移°)</label><input v-model.number="config.realtime_yaw" type="number" step="0.1"></div>
        <div class="input-item"><label>Tilt (俯仰偏移°)</label><input v-model.number="config.realtime_pitch" type="number" step="0.1"></div>
        <div class="input-item"><label>Zoom (变倍数)</label><input v-model.number="config.realtime_focal" type="number" step="0.1"></div>
      </div>
    </div>

    <span class="group-title" style="margin-top: 15px;">2. 目标像素框 (BndBox)</span>
    <div class="input-grid">
      <div class="input-item"><label>X (左上角)</label><input v-model.number="config.bnd.x" type="number" step="1"></div>
      <div class="input-item"><label>Y (左上角)</label><input v-model.number="config.bnd.y" type="number" step="1"></div>
      <div class="input-item"><label>宽度 (Width)</label><input v-model.number="config.bnd.width" type="number" step="1"></div>
      <div class="input-item"><label>高度 (Height)</label><input v-model.number="config.bnd.height" type="number" step="1"></div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  config: Object
});
</script>
