import { createApp } from 'vue'
import './style.css'
import App from './App.vue'

// [核心] 必须引入 Leaflet 的样式文件
import "leaflet/dist/leaflet.css";

createApp(App).mount('#app')
