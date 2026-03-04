import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {             // Error: ENOSPC: System limit for number of file watchers reached,
    watch: {            // 解决：增加文件监听器数量，适用于Linux系统
      usePolling: true, // 开启轮询，绕过系统的 inotify 限制
      interval: 1000    // 可选：设置轮询间隔（毫秒），1000代表1秒检查一次，减少CPU消耗
    }
  }
})
