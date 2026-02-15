from pydantic import BaseModel, Field
from typing import List, Optional, Any

# --- Request ---
class GpsInfo(BaseModel):
    lat: float
    lng: float
    alt: float

class PoseInfo(BaseModel):
    pitch: float
    yaw: float
    roll: float

class Extrinsics(BaseModel):
    gps: GpsInfo
    height_above_ground: float
    pose: PoseInfo

class Intrinsics(BaseModel):
    image_resolution: dict # {width: int, height: int}
    hardware_specs: dict   # {focal_length_mm: float, sensor_width_mm: float}
    distortion_coeffs: Optional[List[float]] = None

class CameraInfo(BaseModel):
    device_id: str
    extrinsics: Extrinsics
    intrinsics: Intrinsics

class ImageData(BaseModel):
    image_url: Optional[str] = None
    base64: Optional[str] = None

class Target(BaseModel):
    target_id: Optional[str] = None # 虽然你请求示例里有，但我们会重新编号，或者沿用
    bbox: dict # {x, y, w, h}

class LocalizationRequest(BaseModel):
    req_id: Optional[str] = "uuid-default"
    terrain: str = "mount"
    timestamp: Optional[str] = None
    camera_info: CameraInfo
    image_data: ImageData
    targets: List[Target]

# --- Response ---
class GeoPoint(BaseModel):
    lat: float
    lng: float
    alt: float

class CompDetails(BaseModel):
    calculated_depth: float
    straight_distance: float
    bearing_angle: float

class SuspectResult(BaseModel):
    target_id: str
    suspect_geo_location: GeoPoint
    confidence: float
    suspect_region_polygon: List[dict] # [{lat, lng}, ...]
    computation_details: CompDetails

class ApiResponseData(BaseModel):
    req_id: str
    results: List[SuspectResult]

class ApiResponse(BaseModel):
    code: int
    message: str
    data: ApiResponseData
    demo_images: Optional[dict] = None # 用于前端展示 Base64 图片
    