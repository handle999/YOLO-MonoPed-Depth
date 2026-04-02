// frontend/src/api/sysv2_api.js
import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8112'; 

/**
 * 接口三：电子围栏测距 (8112)
 * @param {Object} config - sysv2Config 表单配置对象
 * @param {String} imageSourceType - 'upload' 或 'url'
 * @param {String} imageBase64 - 本地上传的 base64 数据
 * @param {String} imageUrl - 远程图片 url
 */
export const fetchFenceDistance = async (config, imageSourceType, imageBase64, imageUrl) => {
  const payload = {
    ip: config.ip,
    image_w: config.image_w,
    image_h: config.image_h,
    bnd: config.bnd,
    terrain_mode: config.terrain_mode,
    camera_type: config.camera_type
  };

  // 动态球机参数附加
  if (config.camera_type === 'ptz') {
    payload.realtime_yaw = config.realtime_yaw;
    payload.realtime_pitch = config.realtime_pitch;
    payload.realtime_focal = config.realtime_focal;
  }

  // 图片数据附加
  if (imageSourceType === 'upload' && imageBase64) {
    payload.imageData = imageBase64;
  } else if (imageSourceType === 'url' && imageUrl) {
    // 预留给后端未来支持 url 模式
    // payload.imageUrl = imageUrl; 
  }

  const response = await axios.post(`${API_BASE_URL}/xjzhdd/alarmEvent/pull/fence_distance`, payload);
  return response.data; // 直接返回 axios 的 data 层
};
