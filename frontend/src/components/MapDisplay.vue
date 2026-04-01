<template>
  <div class="map-container">
    
    <button class="focus-camera-btn" @click="focusOnCamera" title="回到相机所在位置">
      🎯 聚焦
    </button>

    <l-map ref="mapRef" v-model:zoom="zoom" v-model:center="center" :use-global-leaflet="false" :max-zoom="25">
      
      <!-- zhdd系统，本地访问缓存作为底图？ -->
      <!-- <l-tile-layer 
        url = "http://192.168.0.105:9408/zhdd/mixed/{z}/{x}/{y}.jpg"
        layer-type="base" 
        name="Gaode Satellite" 
        :max-native-zoom="20" 
        :max-zoom="20">
      </l-tile-layer> -->
      <l-tile-layer 
        url="https://webst01.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}" 
        layer-type="base" 
        name="Google Hybrid" 
        :max-native-zoom="18" 
        :max-zoom="25">
      </l-tile-layer>

      <l-control-scale position="bottomright" :metric="true" :imperial="false"></l-control-scale>
      <l-control position="bottomright">
        <div class="zoom-indicator"><div>Level: {{ zoom.toFixed(1) }}</div></div>
      </l-control>

      <l-marker :lat-lng="getCameraLatLng()">
        <l-tooltip :options="{ permanent: true, direction: 'top' }">📷 相机位置</l-tooltip>
      </l-marker>

      <template v-for="target in apiResults" :key="target.target_id">
        <l-marker :lat-lng="[target.suspect_geo_location.lat, target.suspect_geo_location.lng]">
          <l-icon class-name="custom-target-icon">
            <div class="target-badge">{{ target.target_id.split('_')[1] }}</div>
          </l-icon>
          <l-popup>
            <div class="popup-content">
              <strong>ID: {{ target.target_id }}</strong><hr/>
              <div>距离: {{ target.computation_details.straight_distance.toFixed(2) }}m</div>
              <div>Lat: {{ target.suspect_geo_location.lat.toFixed(6) }}</div>
              <div>Lng: {{ target.suspect_geo_location.lng.toFixed(6) }}</div>
            </div>
          </l-popup>
        </l-marker>

        <l-polygon 
          :lat-lngs="formatPolygon(target.suspect_region_polygon)" 
          color="#00ff00" :weight="2" fill-color="#00ff00" :fill-opacity="0.3" 
        />
      </template>
    </l-map>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { LMap, LTileLayer, LMarker, LPolygon, LPopup, LIcon, LTooltip, LControlScale, LControl } from "@vue-leaflet/vue-leaflet";

const props = defineProps({
  cameraConfig: Object,
  apiResults: Array
});

// 动态提取经纬度的方法 (兼容 8110 嵌套格式 和 8111 扁平格式)
const getCameraLatLng = () => {
  if (!props.cameraConfig) return [0, 0];
  const lat = props.cameraConfig.extrinsics ? props.cameraConfig.extrinsics.lat : props.cameraConfig.latitude;
  const lng = props.cameraConfig.extrinsics ? props.cameraConfig.extrinsics.lng : props.cameraConfig.longitude;
  return [lat, lng];
};

const mapRef = ref(null);
const zoom = ref(18);

// [修改] 初始中心点不再写死，而是动态读取传入的配置坐标
const center = ref(getCameraLatLng()); 

// [新增] 聚焦相机的方法
const focusOnCamera = () => {
  center.value = getCameraLatLng(); // 将地图中心设为相机坐标
  zoom.value = 18;                  // 强制恢复默认的 18 缩放级别
};

const formatPolygon = (polyList) => polyList.map(p => [p.lat, p.lng]);

// 暴露给父组件自适应所有框的方法
const fitBounds = () => {
  if (!mapRef.value || props.apiResults.length === 0) return;
  const points = [getCameraLatLng()]; // 把相机坐标加进计算范围
  props.apiResults.forEach(t => {
    points.push([t.suspect_geo_location.lat, t.suspect_geo_location.lng]);
    t.suspect_region_polygon.forEach(p => points.push([p.lat, p.lng]));
  });
  mapRef.value.leafletObject.fitBounds(points, { padding: [50, 50], maxZoom: 21 });
};

defineExpose({ fitBounds });
</script>
