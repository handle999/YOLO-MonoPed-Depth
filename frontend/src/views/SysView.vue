<template>
  <div class="content-wrapper sys-view" style="width: 100%; height: 100%;">
    <div class="sidebar">
      
      <div class="card config-card">
        <div class="card-header">🔌 接口测试执行器</div>
        <div class="input-item" style="margin-bottom: 10px;">
          <label>目标图片 URL (imageUrl)</label>
          <input v-model="testImageUrl" type="text" placeholder="http://..." />
        </div>

        <button 
          @click="runDetection" 
          class="run-btn" 
          style="background-color: #8b5cf6;"
          :disabled="loading"
        >
          {{ loading ? '请求中...' : '1. 调用人员检测 (/pull/detection)' }}
        </button>
      </div>

      <SysCameraInput 
        :sysConfig="sysConfig" 
      />

      <div class="card config-card">
        <button 
          @click="runLocalization" 
          class="run-btn" 
          style="background-color: #10b981; margin-top: 5px;"
          :disabled="loading || detectionObjects.length === 0"
        >
          {{ loading ? '请求中...' : '2. 调用人员定位 (/pull/local)' }}
        </button>
        <p class="sys-hint" v-if="detectionObjects.length === 0">
          * 提示：需要先成功调用接口 1 拿到目标框，才能调用接口 2。
        </p>
      </div>
      
    </div>

    <div class="map-container json-panel">
      <div class="json-header">后端 JSON 响应报文格式验证</div>
      <pre class="json-display">{{ jsonOutput || '// 点击左侧按钮发起测试...' }}</pre>
    </div>

  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';
import { fetchDetection, fetchLocalization } from '../api/sys_api.js';
import SysCameraInput from '../components/SysCameraInput.vue';

// 基础状态
const testImageUrl = ref('https://28572339.s21i.faiusr.com/4/ABUIABAEGAAg5uKakgYosYCYmQcwuAg49wQ!800x800.png'); // 默认图片
const loading = ref(false);
const jsonOutput = ref('');
const detectionObjects = ref([]); // 保存接口1拿到的框，给接口2用

// [新增] 用于绑定表单输入的 8111 接口专用的响应式配置
// 这里的默认值直接取自你提供的 Word 文档示例
const sysConfig = reactive({
  longitude: 80.23456789,
  latitude: 20.23456789,
  height: 6.30,
  pitch: -0.012,
  yaw: 0.0,
  roll: 0.0,
  f: 4.0
});

const runDetection = async () => {
  if (!testImageUrl.value) return alert("请输入图片URL");
  loading.value = true;
  jsonOutput.value = "请求 /pull/detection 中...\n请确保 8111 端口的服务已启动。";
  
  try {
    const data = await fetchDetection(testImageUrl.value);
    jsonOutput.value = JSON.stringify(data, null, 2);
    // 保存检测结果的 objectList
    if (data.code === 200) {
      detectionObjects.value = data.objectList || [];
    }
  } catch (error) {
    jsonOutput.value = "请求失败:\n" + (error.response?.data ? JSON.stringify(error.response.data, null, 2) : error.message);
  } finally {
    loading.value = false;
  }
};

const runLocalization = async () => {
  loading.value = true;
  jsonOutput.value = "请求 /pull/local 中...\n正在根据输入的相机参数计算经纬度...";
  
  try {
    // [修改] 将界面的 sysConfig 参数传入 API
    const data = await fetchLocalization(sysConfig, testImageUrl.value, detectionObjects.value);
    jsonOutput.value = JSON.stringify(data, null, 2);
  } catch (error) {
    jsonOutput.value = "请求失败:\n" + (error.response?.data ? JSON.stringify(error.response.data, null, 2) : error.message);
  } finally {
    loading.value = false;
  }
};
</script>
