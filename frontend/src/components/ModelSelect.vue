<template>
  <div class="card config-card">
    <div class="card-header">🤖 模型配置</div>
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
          <optgroup label="YOLOv11 系列">
            <option value="yolo11n">YOLOv11 Nano</option>
            <option value="yolo11s">YOLOv11 Small</option>
            <option value="yolo11m">YOLOv11 Medium</option>
            <option value="yolo11l">YOLOv11 Large</option>
            <option value="yolo11x">YOLOv11 XLarge</option>
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
</template>

<script setup>
// 使用双向绑定的 modelValue (或者直接传对象引用)
defineProps({
  modelConfig: Object
});
</script>
