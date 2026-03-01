<template>
  <div class="image-modal" v-if="show" @click.self="$emit('close')">
    <img :src="src" class="modal-content" />
    <div class="modal-actions">
      <button class="modal-btn btn-download" @click="downloadImage">⬇️ 下载原图</button>
      <button class="modal-btn btn-close" @click="$emit('close')">❌ 关闭</button>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  show: Boolean,
  src: String,
  filename: String
});
const emit = defineEmits(['close']);

const downloadImage = () => {
  const link = document.createElement('a');
  link.href = props.src;
  link.download = props.filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};
</script>
