import os
import shutil
import cv2
import json
import asyncio
from fastapi import APIRouter, UploadFile, File, WebSocket, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional

from src.analysis.pipeline import VideoAnalyzer
from src.config import Config
from src.prompts import DEFAULT_SYSTEM_PROMPT, DEFAULT_USER_PROMPT
from src.services.assistant import PromptAssistant

router = APIRouter()

UPLOAD_DIR = "uploads"

# Global state for simplicity in this dev phase
current_config = {
    "system_prompt": DEFAULT_SYSTEM_PROMPT,
    "user_prompt": DEFAULT_USER_PROMPT,
    "detail": "medium"
}

# Singleton analyzer (lazy load)
_analyzer = None

def get_analyzer():
    global _analyzer
    if _analyzer is None:
        _analyzer = VideoAnalyzer()
    return _analyzer

class AssistantConfig(BaseModel):
    provider: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None

class ConfigUpdate(BaseModel):
    system_prompt: Optional[str] = None
    user_prompt: Optional[str] = None
    detail: Optional[str] = None
    model_name: Optional[str] = None
    assistant: Optional[AssistantConfig] = None

class RefineRequest(BaseModel):
    prompt: str
    type: str = "system" # 'system' or 'user'

import logging
from typing import List

# ... (imports)

# Global connection manager for system logs
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()

# Global event loop reference
main_loop = None

# Custom Log Handler to broadcast logs
class WebSocketLogHandler(logging.Handler):
    def emit(self, record):
        pass

# Simplified approach: We will just push to a global queue and a background task will broadcast
import asyncio
log_queue = asyncio.Queue()

async def log_broadcaster():
    while True:
        message = await log_queue.get()
        await manager.broadcast(message)
        log_queue.task_done()

# Hook into logging
class QueueHandler(logging.Handler):
    def emit(self, record):
        global main_loop
        try:
            msg = self.format(record)
            if main_loop and not main_loop.is_closed():
                main_loop.call_soon_threadsafe(log_queue.put_nowait, msg)
        except Exception:
            self.handleError(record)

# Add handler to root logger
queue_handler = QueueHandler()
queue_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logging.getLogger().addHandler(queue_handler)
logging.getLogger().setLevel(logging.INFO)

# Make sure to start the broadcaster on startup
@router.on_event("startup")
async def startup_event():
    global main_loop
    main_loop = asyncio.get_running_loop()
    asyncio.create_task(log_broadcaster())

@router.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text() # Keep connection alive
    except:
        manager.disconnect(websocket)

@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):
# ... (rest of code)
    file_location = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return {"filename": file.filename, "url": f"/uploads/{file.filename}"}

@router.get("/video/{filename}/frame")
async def get_video_frame(filename: str, timestamp: float = 0.0):
    video_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video not found")
        
    cap = cv2.VideoCapture(video_path)
    # Calculate frame number
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_no = int(timestamp * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
    
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        raise HTTPException(status_code=500, detail="Could not read frame")
        
    # Encode to jpg
    ret, buffer = cv2.imencode('.jpg', frame)
    if not ret:
        raise HTTPException(status_code=500, detail="Could not encode frame")
        
    # Save temp file to serve (or stream bytes directly)
    # Streaming bytes is better but FileResponse is easier for now with temp file
    temp_frame = f"temp_frame_{filename}_{timestamp}.jpg"
    with open(temp_frame, "wb") as f:
        f.write(buffer)
        
    return FileResponse(temp_frame)

@router.get("/config")
def get_config():
    return {
        **current_config,
        "model_name": Config.MODEL_NAME,
        "available_models": Config.AVAILABLE_MODELS,
        "assistant": Config.ASSISTANT_CONFIG
    }

@router.post("/config")
def update_config(config: ConfigUpdate):
    global current_config
    if config.system_prompt:
        current_config["system_prompt"] = config.system_prompt
    if config.user_prompt:
        current_config["user_prompt"] = config.user_prompt
    if config.detail:
        current_config["detail"] = config.detail
    
    # Handle model update
    if hasattr(config, 'model_name') and config.model_name:
        Config.MODEL_NAME = config.model_name
        # Reload model if changed
        get_analyzer().reload_model(Config.MODEL_NAME)
        
    # Handle assistant update
    if config.assistant:
        if config.assistant.provider:
            Config.ASSISTANT_CONFIG["provider"] = config.assistant.provider
        if config.assistant.api_key:
            Config.ASSISTANT_CONFIG["api_key"] = config.assistant.api_key
        if config.assistant.base_url:
            Config.ASSISTANT_CONFIG["base_url"] = config.assistant.base_url
        if config.assistant.model:
            Config.ASSISTANT_CONFIG["model"] = config.assistant.model
        
    return get_config()

@router.post("/tools/refine-prompt")
async def refine_prompt(request: RefineRequest):
    try:
        assistant = PromptAssistant()
        refined = await assistant.refine_prompt(request.prompt, request.type)
        return {"refined_prompt": refined}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/ws/analyze")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    try:
        data = await websocket.receive_json()
        filename = data.get("filename")
        roi = data.get("roi") # {x, y, w, h} or None
        
        video_path = os.path.join(UPLOAD_DIR, filename)
        
        if not os.path.exists(video_path):
            await websocket.send_json({"type": "error", "message": "Video not found"})
            await websocket.close()
            return

        analyzer = get_analyzer()
        
        # Define callback to push to websocket
        # Note: WebSocket send is async, but analyzer is sync. 
        # We need a way to bridge this. 
        # For this prototype, we'll use a queue or just run analyzer in a thread 
        # and use an event loop safe way to send messages.
        # OR simpler: We just make the callback run_coroutine_threadsafe if we were async,
        # but here we are inside an async handler calling a sync function.
        # We can use fastapi's background tasks or run_in_executor.
        
        # Let's use a simple queue approach or direct send if we can.
        # Since analyze_video is blocking, we should run it in an executor.
        
        loop = asyncio.get_event_loop()
        
        def progress_callback(event):
            # This runs in the thread, so we need to schedule sending to WS on the loop
            asyncio.run_coroutine_threadsafe(websocket.send_json(event), loop)

        roi_tuple = None
        if roi:
            roi_tuple = (int(roi['x']), int(roi['y']), int(roi['w']), int(roi['h']))

        await websocket.send_json({"type": "status", "message": "Starting analysis..."})

        # Run analysis in a separate thread to not block the event loop
        result, segments = await loop.run_in_executor(
            None, 
            lambda: analyzer.analyze_video(
                video_path, 
                detail=current_config["detail"], 
                roi=roi_tuple,
                system_prompt=current_config["system_prompt"],
                user_prompt=current_config["user_prompt"],
                progress_callback=progress_callback
            )
        )
        
        await websocket.send_json({"type": "complete", "result": json.loads(result)})
        
    except Exception as e:
        print(f"Error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass
    finally:
        await websocket.close()
