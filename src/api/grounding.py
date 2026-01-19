import os
import json
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from src.services.grounding_pipeline import GroundingPipeline

router = APIRouter(prefix="/grounding", tags=["grounding"])

# Initialize Pipeline Service
pipeline_service = GroundingPipeline()

class TestCaseConfig(BaseModel):
    name: str
    model: str = "qwen" # qwen, mai
    prompt: str
    system_prompt: Optional[str] = None
    image_path: str # filename in uploads/ or absolute path
    allowed_actions: List[str] = ["click", "drag", "type"]
    refinement: bool = False
    prompt_template: Optional[str] = None

class TestSuiteRequest(BaseModel):
    suite_name: str
    configs: List[TestCaseConfig]

@router.post("/execute")
async def execute_suite(request: TestSuiteRequest, background_tasks: BackgroundTasks):
    """
    Executes a test suite. For now we run it synchronously to return results immediately 
    for the MVP, but ideally this should be a background task with polling.
    Given the user wants to "see results", we'll run it and return the suite_id.
    """
    try:
        # Convert Pydantic models to dicts
        suite_config = request.dict()
        
        # We can run this in background if it takes too long
        # But for the UI to update, let's try synchronous for 1-2 configs, 
        # or return ID and let UI poll (simpler for now: return ID and results if fast enough)
        
        # Running synchronously for immediate feedback in this iteration
        suite_id = pipeline_service.execute_suite(suite_config)
        
        return {
            "suite_id": suite_id,
            "message": "Suite executed successfully",
            "results_url": f"/grounding/runs/{suite_id}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/runs")
def list_runs():
    """
    List all test suites executed.
    """
    runs_dir = "runs"
    if not os.path.exists(runs_dir):
        return []
    
    suites = []
    for suite_id in sorted(os.listdir(runs_dir), reverse=True):
        suite_path = os.path.join(runs_dir, suite_id)
        if os.path.isdir(suite_path):
            # Load summary if exists
            summary_path = os.path.join(suite_path, "summary.json")
            summary = []
            if os.path.exists(summary_path):
                with open(summary_path, "r") as f:
                    summary = json.load(f)
            
            suites.append({
                "suite_id": suite_id,
                "timestamp": suite_id.split("_")[0],
                "name": "_".join(suite_id.split("_")[2:]),
                "config_count": len(summary),
                "summary": summary
            })
    return suites

@router.get("/runs/{suite_id}")
def get_run_details(suite_id: str):
    """
    Get full details of a specific suite run.
    """
    suite_path = os.path.join("runs", suite_id)
    if not os.path.exists(suite_path):
        raise HTTPException(status_code=404, detail="Suite not found")
        
    summary_path = os.path.join(suite_path, "summary.json")
    if not os.path.exists(summary_path):
         return {"suite_id": suite_id, "configs": []}
         
    with open(summary_path, "r") as f:
        summary = json.load(f)
        
    return {"suite_id": suite_id, "configs": summary}

@router.get("/config-schema")
def get_config_schema():
    """
    Returns the allowed options for the UI builder.
    """
    return {
        "models": ["qwen", "mai"],
        "default_actions": ["click", "drag", "type", "scroll", "hover"],
        "default_prompt_template": """User instruction: {prompt}

Please decompose this task into a sequence of low-level UI actions.
If the task involves moving an item (drag and drop), you MUST provide the start coordinate (the item to move) and the end coordinate (the destination container).

Format your answer strictly as a JSON list of objects.

Example:
[
  {{"action": "drag", "start_bbox": [100, 200, 150, 250], "end_bbox": [400, 200, 500, 600], "description": "Drag Item A to Column B"}}
]

Now, provide the JSON for the user instruction."""
    }
