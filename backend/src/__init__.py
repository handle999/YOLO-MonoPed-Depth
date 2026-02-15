# 从当前包 (.) 的 detector 模块导入 PersonDetector 类
from .detector import PersonDetector

# 从当前包 (.) 的 geolocalizer 模块导入 GeoLocalizer 类
from .geolocalizer import GeoLocalizer

from .visualizer import Visualizer

# (可选) 定义版本号
__version__ = '0.1.0'

# (可选) 定义当别人使用 from src import * 时，只导出这些类
__all__ = ['PersonDetector', 'GeoLocalizer', 'Visualizer']
