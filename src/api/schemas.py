from pydantic import BaseModel
from typing import Optional

class VisionRequest(BaseModel):
    prompt: str = "Describe what you see."
    
class VisionResponse(BaseModel):
    description: str
    
class CaptureRequest(BaseModel):
    prompt: str = "Describe what you see on the screen."
    monitor_index: int = 1
