import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8110'; 

export const analyzeLocalizationAPI = async (cameraConfig, modelConfig, imageBase64) => {
  // 提取纯 Base64 字符串
  const cleanBase64 = imageBase64.includes(',') 
    ? imageBase64.split(',')[1] 
    : imageBase64;

  const payload = {
    req_id: `req_${Date.now()}`,
    terrain: cameraConfig.terrain,
    det_model: modelConfig.detModel,
    pose_model: modelConfig.poseModel,
    camera_info: {
      device_id: cameraConfig.deviceId,
      extrinsics: {
        gps: { lat: cameraConfig.extrinsics.lat, lng: cameraConfig.extrinsics.lng, alt: cameraConfig.extrinsics.alt },
        height_above_ground: cameraConfig.extrinsics.height,
        pose: { pitch: cameraConfig.extrinsics.pitch, yaw: cameraConfig.extrinsics.yaw, roll: cameraConfig.extrinsics.roll }
      },
      intrinsics: {
        image_resolution: { width: cameraConfig.resolution.width, height: cameraConfig.resolution.height },
        hardware_specs: { focal_length_mm: cameraConfig.intrinsics.focal_length, sensor_width_mm: cameraConfig.intrinsics.sensor_width },
        distortion_coeffs: [
          cameraConfig.distortion.k1, cameraConfig.distortion.k2, cameraConfig.distortion.p1, 
          cameraConfig.distortion.p2, cameraConfig.distortion.k3
        ]
      }
    },
    image_data: { base64: cleanBase64 },
    targets: [] 
  };

  const response = await axios.post(`${API_BASE_URL}/api/v1/perception/suspect_localization`, payload);
  return response.data;
};
