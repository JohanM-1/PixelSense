import os
import json
import re
import yaml
import time
import logging
from typing import List, Dict, Any, Optional
from PIL import Image, ImageDraw
from datetime import datetime

from src.model.engine import VisionEngine
from src.config import Config

logger = logging.getLogger(__name__)

class GroundingPipeline:
    def __init__(self):
        self.engine = VisionEngine()
        self.runs_dir = "runs"
        if not os.path.exists(self.runs_dir):
            os.makedirs(self.runs_dir)

    def execute_suite(self, suite_config: Dict[str, Any]) -> str:
        """
        Executes a full test suite containing multiple configs.
        Returns the suite_id.
        """
        suite_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{suite_config.get('suite_name', 'suite').replace(' ', '_')}"
        suite_dir = os.path.join(self.runs_dir, suite_id)
        os.makedirs(suite_dir)
        
        # Save suite config
        with open(os.path.join(suite_dir, "suite_config.json"), "w") as f:
            json.dump(suite_config, f, indent=2)

        results = []
        
        for config in suite_config.get("configs", []):
            try:
                result = self.execute_step(config, suite_dir, suite_id)
                results.append(result)
            except Exception as e:
                logger.error(f"Error executing config {config.get('name')}: {e}")
                results.append({
                    "config_name": config.get("name"),
                    "status": "error",
                    "error": str(e)
                })

        # Update summary
        with open(os.path.join(suite_dir, "summary.json"), "w") as f:
            json.dump(results, f, indent=2)
            
        return suite_id

    def execute_step(self, config: Dict[str, Any], suite_dir: str, suite_id: str) -> Dict[str, Any]:
        """
        Executes a single test configuration step.
        """
        config_name = config.get("name", "unnamed").replace(" ", "_")
        run_dir = os.path.join(suite_dir, config_name)
        os.makedirs(run_dir)
        
        # 1. Load Model
        model_name = config.get("model", "qwen")
        hf_model_name = "LZXzju/Qwen2.5-VL-3B-UI-R1-E" # Default Qwen
        if model_name == "mai":
            hf_model_name = "Tongyi-MAI/MAI-UI-2B"
        elif model_name == "qwen":
            hf_model_name = "LZXzju/Qwen2.5-VL-3B-UI-R1-E"
        # Support full HF paths too
        if "/" in model_name:
            hf_model_name = model_name
            
        self.engine.load_model(hf_model_name)
        
        # 2. Prepare Inputs
        image_path = config.get("image_path")
        # Handle uploaded images path resolution
        if not os.path.isabs(image_path) and not os.path.exists(image_path):
             # Try uploads dir
             potential_path = os.path.join("uploads", image_path)
             if os.path.exists(potential_path):
                 image_path = potential_path
        
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
            
        image = Image.open(image_path)
        origin_width, origin_height = image.size
        
        prompt = config.get("prompt", "")
        system_prompt = config.get("system_prompt", "")
        
        # Construct Prompt Template
        # Uses the logic we defined in config.yaml but dynamic here
        prompt_template = config.get("prompt_template")
        if not prompt_template:
            # Default template similar to our successful test
            prompt_template = (
                f"User instruction: {prompt}\n"
                f"{system_prompt}\n"
                "Please decompose this task into a sequence of low-level UI actions.\n"
                "If the task involves moving an item (drag and drop), you MUST provide the start coordinate (the item to move) and the end coordinate (the destination container).\n"
                "Format your answer strictly as a JSON list of objects.\n"
                "Example:\n"
                "[{{\"action\": \"drag\", \"start_bbox\": [100, 200, 150, 250], \"end_bbox\": [400, 200, 500, 600], \"description\": \"Drag A to B\"}}]\n"
                "Now, provide the JSON for the user instruction."
            )
        else:
            prompt_template = prompt_template.format(prompt=prompt)
            
        # 3. LMM Inference
        # We need to wrap this in <image> for Qwen/MAI as per our test
        query = '<image>\n' + prompt_template
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": query}
                ]
            }
        ]
        
        logger.info(f"Running inference for {config_name} with {hf_model_name}...")
        raw_response = self.engine.analyze(messages)
        
        # 4. Parse Actions
        actions = self._parse_json_response(raw_response)
        
        # 5. Validation (Allowed Actions)
        allowed_actions = config.get("allowed_actions", [])
        if allowed_actions:
            filtered_actions = []
            for action in actions:
                act_type = action.get("action", "").lower()
                if act_type in [a.lower() for a in allowed_actions]:
                    filtered_actions.append(action)
                else:
                    logger.warning(f"Action '{act_type}' filtered out (not in allowed list)")
            actions = filtered_actions

        # 6. Refinement (Gemini) - Optional
        if config.get("refinement", False):
            actions = self._refine_with_gemini(actions, image, prompt)

        # 7. Visualization & Save
        result_image_path = os.path.join(run_dir, "result.png")
        self._visualize_actions(image.copy(), actions, result_image_path, origin_width, origin_height)
        
        # Save JSON
        with open(os.path.join(run_dir, "actions.json"), "w") as f:
            json.dump(actions, f, indent=2)
            
        # Save Logs/Raw Response
        with open(os.path.join(run_dir, "raw_response.txt"), "w") as f:
            f.write(raw_response)

        return {
            "config_name": config_name,
            "status": "success",
            "model": hf_model_name,
            "image_url": f"/runs/{suite_id}/{config_name}/result.png", # Relative URL for frontend
            "actions": actions,
            "raw_response": raw_response
        }

    def _parse_json_response(self, text: str) -> List[Dict]:
        try:
            # Find JSON array
            json_match = re.search(r'\[\s*\{.*\}\s*\]', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            return json.loads(text)
        except Exception:
            logger.warning("Failed to parse JSON, returning empty list")
            return []

    def _visualize_actions(self, image, actions, output_path, width, height):
        draw = ImageDraw.Draw(image)
        for i, step in enumerate(actions):
            bbox = step.get("bbox") or step.get("start_bbox")
            if bbox:
                # Normalize check (0-1000)
                if all(isinstance(c, (int, float)) and c <= 1000 for c in bbox):
                    x1 = int(bbox[0] / 1000 * width)
                    y1 = int(bbox[1] / 1000 * height)
                    x2 = int(bbox[2] / 1000 * width)
                    y2 = int(bbox[3] / 1000 * height)
                else:
                    x1, y1, x2, y2 = bbox # Assume absolute if > 1000 (though unlikely for Qwen/MAI standard)

                # Draw Start
                draw.rectangle([x1, y1, x2, y2], outline="red", width=3)
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                draw.ellipse((cx - 10, cy - 10, cx + 10, cy + 10), fill='blue', outline='white')
                
                action_type = step.get("action", "action").upper()
                draw.text((x1, y1 - 15), f"{i+1}: {action_type}", fill='red')

                # Draw End (Drag)
                if "end_bbox" in step:
                    end_bbox = step["end_bbox"]
                    if all(isinstance(c, (int, float)) and c <= 1000 for c in end_bbox):
                        ex1 = int(end_bbox[0] / 1000 * width)
                        ey1 = int(end_bbox[1] / 1000 * height)
                        ex2 = int(end_bbox[2] / 1000 * width)
                        ey2 = int(end_bbox[3] / 1000 * height)
                    else:
                        ex1, ey1, ex2, ey2 = end_bbox
                    
                    ecx, ecy = (ex1 + ex2) // 2, (ey1 + ey2) // 2
                    draw.rectangle([ex1, ey1, ex2, ey2], outline="green", width=3)
                    draw.ellipse((ecx - 10, ecy - 10, ecx + 10, ecy + 10), fill='green', outline='white')
                    draw.line([(cx, cy), (ecx, ecy)], fill="yellow", width=3)
                    draw.text((ex1, ey1 - 15), "DROP", fill='green')
        
        image.save(output_path)

    def _refine_with_gemini(self, actions: List[Dict], image: Image.Image, prompt: str) -> List[Dict]:
        # This calls the Gemini API via the engine to refine the actions
        # Placeholder logic as we rely on the generic engine.analyze which handles Gemini
        # Ideally we construct a new prompt: "Here is the image and the proposed actions: {actions}. Are they correct for task '{prompt}'? Return refined JSON."
        
        # For now, simply return actions or implement if user specifically requested this specific logic active NOW
        # The user said "esto ya esta configurado para refinar", implying I should leverage existing cap.
        # I'll implement a basic refinement call.
        
        refine_prompt = (
            f"Task: {prompt}\n"
            f"Proposed Actions: {json.dumps(actions)}\n"
            "Verify these actions against the UI image. Correct any wrong coordinates or missed steps.\n"
            "Return ONLY the corrected JSON list of actions."
        )
        
        # We need to temporarily switch to Gemini model if not already
        # But VisionEngine switches automatically if we pass a gemini model name
        # We need the API key from config
        if not Config.ASSISTANT_CONFIG.get("api_key"):
            logger.warning("No API key for refinement, skipping.")
            return actions

        # We need to preserve current model to switch back? 
        # VisionEngine loads on demand, so next step will reload local model if needed.
        # But this is expensive. For MVP, let's assume refinement is high value.
        
        try:
            # Force load gemini for this call
            gemini_model = "google/gemini-2.0-flash-exp" # Or whatever is configured
            # Actually we should use the one in Config or passed in
            
            # Since VisionEngine.analyze handles loading, we just pass the model name in a "virtual" way
            # But wait, VisionEngine.analyze uses `self.current_model_name`.
            # We need to instantiate a separate client or force switch.
            # Let's force switch for now.
            
            # Save current
            prev_model = self.engine.current_model_name
            
            self.engine.load_model(gemini_model)
            refined_response = self.engine.analyze_image(image, refine_prompt)
            refined_actions = self._parse_json_response(refined_response)
            
            # Switch back or leave it for next step to handle
            if prev_model and "gemini" not in prev_model:
                self.engine.load_model(prev_model)
                
            return refined_actions if refined_actions else actions
            
        except Exception as e:
            logger.error(f"Refinement failed: {e}")
            return actions
