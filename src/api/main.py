from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from src.api.routes import router
from src.api.grounding import router as grounding_router

app = FastAPI(title="PixelSense API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount uploads directory to serve video files
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Mount runs directory to serve test results
RUNS_DIR = "runs"
if not os.path.exists(RUNS_DIR):
    os.makedirs(RUNS_DIR)
app.mount("/runs", StaticFiles(directory=RUNS_DIR), name="runs")

# Include routes
app.include_router(router)
app.include_router(grounding_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
