import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from src.api.routes import router
from src.api.labeling import router as labeling_router

app = FastAPI(
    title="PixelSense API",
    description="Local Multimodal AI Assistant",
    version="0.1.0"
)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(router, prefix="/api/v1")
app.include_router(labeling_router, prefix="/api/v1")

@app.get("/")
def health_check():
    return {"status": "running", "service": "PixelSense"}

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
