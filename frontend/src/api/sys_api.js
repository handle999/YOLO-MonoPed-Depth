import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8111'; 

// 接口二：人员检测
export const fetchDetection = async (imageUrl) => {
  const payload = {
    currentTime: new Date().toISOString().replace('T', ' ').substring(0, 19),
    imageUrl: imageUrl
  };
  const response = await axios.post(`${API_BASE_URL}/xjzhdd/alarmEvent/pull/detection`, payload);
  return response.data;
};

// 接口一：人员定位 (修改：新增 config 参数，替换写死的数值)
export const fetchLocalization = async (config, imageUrl, objectList) => {
  const payload = {
    currentTime: new Date().toISOString().replace('T', ' ').substring(0, 19),
    longitude: config.longitude,
    latitude: config.latitude,
    height: config.height,
    pitch: config.pitch,
    yaw: config.yaw,
    roll: config.roll,
    f: config.f,
    imageUrl: imageUrl,
    objectList: objectList 
  };
  const response = await axios.post(`${API_BASE_URL}/xjzhdd/alarmEvent/pull/local`, payload);
  return response.data;
};
