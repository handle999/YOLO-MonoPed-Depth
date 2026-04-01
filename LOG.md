
# 0401修改记录

1. 修改`backend/main_sys_v2.py`
    1. 纠正'get_distance_professional'的错误转换逻辑
    1. 补充'/xjzhdd/alarmEvent/sub'的模拟，球机传参
    1. 完善'/xjzhdd/alarmEvent/pull/fence_distance'，实现'process_bullet_localization'和'process_ptz_localization'，同时区分'flat'和'mount'模式
1. 修改`frontend/src/App.vue`和`frontend/src/style.css`，增加8112展示页面
1. 增加`frontend/src/views/Sysv2View.vue`，8112可视化子页面，自定义模式和参数，上传图片/url，可视化框，可视化俯视结果，展示json返回值
1. 修改`frontend/src/components/MapDisplay.vue`，8112右侧自适应墙体展示（红色虚线）
1. 增加`frontend/src/components/Sysv2CameraInput.vue`，8112左侧输入相关组件
