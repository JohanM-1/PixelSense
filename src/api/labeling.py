import os
import shutil
import uuid
import base64
import json
import logging
import asyncio
from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from openai import AsyncOpenAI

from src.config import Config
from src.utils.video_processing import extract_frames

router = APIRouter(prefix="/labeling", tags=["labeling"])
logger = logging.getLogger(__name__)

UPLOAD_DIR = "uploads"
LABELING_JOBS_DIR = os.path.join(UPLOAD_DIR, "labeling_jobs")

# Ensure jobs directory exists
os.makedirs(LABELING_JOBS_DIR, exist_ok=True)

# --- Pydantic Models ---

class InitRequest(BaseModel):
    filename: str
    num_frames: int = 100

class InitResponse(BaseModel):
    job_id: str
    frames: List[str]  # List of relative URLs to frames

class BoundingBox(BaseModel):
    x: float
    y: float
    w: float
    h: float
    label: str

class LabelEntry(BaseModel):
    frame: str
    boxes: List[BoundingBox] = []

class PredictRequest(BaseModel):
    job_id: str
    examples: List[LabelEntry]
    targets: List[str] # List of frame filenames to predict

class PredictResponse(BaseModel):
    predictions: List[LabelEntry]

class SaveRequest(BaseModel):
    job_id: str
    labels: List[LabelEntry]
    dataset_name: Optional[str] = None

# --- Helpers ---

def get_job_dir(job_id: str) -> str:
    return os.path.join(LABELING_JOBS_DIR, job_id)

def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def get_ai_client():
    config = Config.ASSISTANT_CONFIG
    return AsyncOpenAI(
        api_key=config.get("api_key"),
        base_url=config.get("base_url")
    )

# --- Endpoints ---

@router.post("/init", response_model=InitResponse)
async def init_labeling(request: InitRequest):
    video_path = os.path.join(UPLOAD_DIR, request.filename)
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video not found")

    job_id = str(uuid.uuid4())
    job_dir = get_job_dir(job_id)
    
    try:
        frames = extract_frames(video_path, job_dir, request.num_frames)
    except Exception as e:
        logger.error(f"Frame extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Frame extraction failed: {str(e)}")

    # Return URLs accessible via static mount
    # Assuming /uploads is mounted to UPLOAD_DIR
    frame_urls = [f"/uploads/labeling_jobs/{job_id}/{f}" for f in frames]
    
    return InitResponse(job_id=job_id, frames=frame_urls)

@router.post("/predict", response_model=PredictResponse)
async def predict_labels(request: PredictRequest):
    job_dir = get_job_dir(request.job_id)
    if not os.path.exists(job_dir):
        raise HTTPException(status_code=404, detail="Job not found")

    client = get_ai_client()
    model = Config.ASSISTANT_CONFIG.get("model", "gemini-2.0-flash")

    # Construct messages for Few-Shot Learning
    messages = [
        {
            "role": "system", 
            "content": """You are an expert vision assistant. Your task is to detect and label objects in images based on provided examples.
Output ONLY a JSON list of bounding boxes for the target image. 
Format: [{"label": "class_name", "x": 0, "y": 0, "w": 0, "h": 0}, ...]
Coordinates (x, y, w, h) should be normalized to 0-1000 scale.
If no objects are found, output []."""
        }
    ]

    # Add examples (User: Image -> Assistant: Label)
    for example in request.examples:
        frame_path = os.path.join(job_dir, os.path.basename(example.frame))
        if not os.path.exists(frame_path):
            continue # Skip missing files
            
        base64_image = encode_image(frame_path)
        
        # Convert boxes to simple list of dicts for prompt
        boxes_json = json.dumps([b.dict() for b in example.boxes])
        
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": "Detect objects in this image:"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]
        })
        messages.append({
            "role": "assistant",
            "content": boxes_json
        })

    # Prepare predictions
    predictions = []
    
    semaphore = asyncio.Semaphore(5) # Limit concurrency to avoid rate limits
    
    async def predict_single(target_filename):
        async with semaphore:
            target_path = os.path.join(job_dir, os.path.basename(target_filename))
            if not os.path.exists(target_path):
                return None
            
            base64_target = encode_image(target_path)
            
            # Copy messages and add the target
            current_messages = list(messages)
            current_messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": "Detect objects in this image:"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_target}"}}
                ]
            })
            
            try:
                response = await client.chat.completions.create(
                    model=model,
                    messages=current_messages,
                    max_tokens=1000,
                    response_format={"type": "json_object"}
                )
                content = response.choices[0].message.content.strip()
                logger.info(f"AI Response for {target_filename}: {content}")
                
                # Clean markdown code blocks if present
                try:
                    # Some models might wrap list in a key
                    parsed = json.loads(content)
                    
                    raw_boxes = []
                    if isinstance(parsed, dict):
                        if "boxes" in parsed and isinstance(parsed["boxes"], list):
                            raw_boxes = parsed["boxes"]
                        else:
                            # Fallback: look for any list
                            for v in parsed.values():
                                if isinstance(v, list):
                                    raw_boxes = v
                                    break
                    elif isinstance(parsed, list):
                        raw_boxes = parsed
                    
                    boxes = [BoundingBox(**b) for b in raw_boxes]
                except:
                    logger.warning(f"Failed to parse prediction for {target_filename}: {content}")
                    boxes = []
                    
                return LabelEntry(frame=target_filename, boxes=boxes)
            except Exception as e:
                logger.error(f"Error predicting {target_filename}: {e}")
                return LabelEntry(frame=target_filename, boxes=[])

    # Run in parallel with semaphore
    tasks = [predict_single(target) for target in request.targets]
    results = await asyncio.gather(*tasks)
    
    predictions = [r for r in results if r is not None]
    
    return PredictResponse(predictions=predictions)

@router.post("/save")
async def save_dataset(request: SaveRequest):
    job_dir = get_job_dir(request.job_id)
    if not os.path.exists(job_dir):
        raise HTTPException(status_code=404, detail="Job not found")
    
    dataset_name = request.dataset_name or f"dataset_{request.job_id}"
    output_file = os.path.join(job_dir, f"{dataset_name}.json")
    
    data = {
        "job_id": request.job_id,
        "labels": [entry.dict() for entry in request.labels]
    }
    
    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)
        
    return {"status": "saved", "path": output_file}
