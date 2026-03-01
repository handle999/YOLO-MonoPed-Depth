<template>
  <div class="card result-card" v-if="demoImages.detection">
    <div class="card-header">📊 分析结果视图</div>
    
    <div class="img-box" @click="$emit('open-modal', demoImages.detection, 'AI_Detection_Result.jpg')">
      <span class="img-label">AI 检测视图 (点击放大)</span>
      <img :src="demoImages.detection" class="result-img" />
      <div class="click-hint">🔍 点击放大 / 下载</div>
    </div>
    
    <div class="img-box" style="margin-top: 15px;" @click="$emit('open-modal', demoImages.skeleton, 'Skeleton_Result.jpg')">
      <span class="img-label">骨架分析视图 (Skeleton)</span>
      <img :src="demoImages.skeleton" class="result-img" />
      <div class="click-hint">🔍 点击放大 / 下载</div>
    </div>

    <div class="img-box" style="margin-top: 15px;" @click="$emit('open-modal', demoImages.radar, 'Lidar_Map_Result.jpg')">
      <span class="img-label">俯视雷达视图 (点击放大)</span>
      <img :src="demoImages.radar" class="result-img" />
      <div class="click-hint">🔍 点击放大 / 下载</div>
    </div>
  </div>
</template>

<script setup>
defineProps({ demoImages: Object });
defineEmits(['open-modal']);
</script>
