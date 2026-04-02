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
            :class="['tab-btn', { active: currentTab === 'sysv2' }]"
            @click="currentTab = 'sysv2'"
          >
            🎯 电子围栏测距 (8111)
          </button>
          
          <button 
            :class="['tab-btn', { active: currentTab === 'sys' }]"
            @click="currentTab = 'sys'"
          >
            🔌 调度接口测试 (8112)
          </button>
        </div>
      </div>
    </header>

    <KeepAlive>
      <NativeView v-if="currentTab === 'native'" />
      <SysView v-else-if="currentTab === 'sys'" />
      <Sysv2View v-else />
    </KeepAlive>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import NativeView from './views/NativeView.vue';
import SysView from './views/SysView.vue';
import Sysv2View from './views/Sysv2View.vue';

// 默认显示 8112 视图
const currentTab = ref('sysv2'); 
</script>
