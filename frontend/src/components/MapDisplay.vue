<template>
  <div class="map-container">
    <l-map ref="mapRef" v-model:zoom="zoom" :center="center" :use-global-leaflet="false" :max-zoom="25">
      <l-tile-layer url="http://mt0.google.com/vt/lyrs=y&hl=en&x={x}&y={y}&z={z}" layer-type="base" name="Google Hybrid" :max-native-zoom="20" :max-zoom="25"></l-tile-layer>
      <l-control-scale position="bottomright" :metric="true" :imperial="false"></l-control-scale>
      <l-control position="bottomright">
        <div class="zoom-indicator"><div>Level: {{ zoom.toFixed(1) }}</div></div>
      </l-control>

      <l-marker :lat-lng="[cameraConfig.extrinsics.lat, cameraConfig.extrinsics.lng]">
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
import { ref } from 'vue';
import { LMap, LTileLayer, LMarker, LPolygon, LPopup, LIcon, LTooltip, LControlScale, LControl } from "@vue-leaflet/vue-leaflet";

const props = defineProps({
  cameraConfig: Object,
  apiResults: Array
});

const mapRef = ref(null);
const zoom = ref(18);
const center = ref([22.54321, 114.05755]); // 初始默认中心

const formatPolygon = (polyList) => polyList.map(p => [p.lat, p.lng]);

// 暴露给父组件的方法
const fitBounds = () => {
  if (!mapRef.value || props.apiResults.length === 0) return;
  const points = [[props.cameraConfig.extrinsics.lat, props.cameraConfig.extrinsics.lng]];
  props.apiResults.forEach(t => {
    points.push([t.suspect_geo_location.lat, t.suspect_geo_location.lng]);
    t.suspect_region_polygon.forEach(p => points.push([p.lat, p.lng]));
  });
  mapRef.value.leafletObject.fitBounds(points, { padding: [50, 50], maxZoom: 21 });
};

defineExpose({ fitBounds });
</script>
