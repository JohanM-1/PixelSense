import uvicorn
from fastapi import FastAPI
from src.api.routes import router

app = FastAPI(
    title="PixelSense API",
    description="Local Multimodal AI Assistant",
    version="0.1.0"
)

app.include_router(router, prefix="/api/v1")

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
