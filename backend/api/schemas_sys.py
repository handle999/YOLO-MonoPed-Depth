# backend/api/schemas_sys.py
from pydantic import BaseModel, Field
from typing import List, Optional

# ==========================================
# 共享/通用数据结构
# ==========================================
class BndBox(BaseModel):
    x: float
    y: float
    width: float
    height: float

# ==========================================
# 接口一：人员定位接口 (Request / Response)
# ==========================================
class LocalObjectIn(BaseModel):
    objectCategory: str
    objectCode: str
    bndbox: BndBox

class LocalRequest(BaseModel):
    currentTime: str
    longitude: float
    latitude: float
    height: float
    pitch: float
    yaw: float
    roll: float
    f: float
    imageUrl: str
    objectList: List[LocalObjectIn]

class LocalObjectOut(BaseModel):
    objectCode: str
    objectCategory: str
    longitude: float
    latitude: float

class LocalResponse(BaseModel):
    code: int = 200
    msg: str = "success"
    imageUrl: str
    currentTime: str
    objectList: List[LocalObjectOut]

# ==========================================
# 接口二：人员检测接口 (Request / Response)
# ==========================================
class DetectRequest(BaseModel):
    currentTime: str
    imageUrl: str

class DetectObjectOut(BaseModel):
    objectCode: str
    objectCategory: str
    bndbox: BndBox

class DetectResponse(BaseModel):
    code: int = 200
    msg: str = "success"
    currentTime: str
    imageUrl: str
    objectList: List[DetectObjectOut]
    