<template>
  <div class="app-container">
    <header class="header">
      <div class="header-content">
        <h2>单目视觉定位系统 (Monocular Localization)</h2>
        
        <div class="mode-tabs">
          <button 
            :class="['tab-btn', { active: currentTab === 'native' }]"
            @click="currentTab = 'native'"
          >
            🖥️ 系统原生视图 (8110)
          </button>
          <button 
            :class="['tab-btn', { active: currentTab === 'sys' }]"
            @click="currentTab = 'sys'"
          >
            🔌 调度接口测试 (8111)
          </button>
        </div>
      </div>
    </header>

    <KeepAlive>
      <NativeView v-if="currentTab === 'native'" />
      <SysView v-else />
    </KeepAlive>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import NativeView from './views/NativeView.vue';
import SysView from './views/SysView.vue';

// 默认显示 8111 视图
const currentTab = ref('sys'); 
</script>
