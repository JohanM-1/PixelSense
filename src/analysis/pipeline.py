import os
import math
import json
import logging
import torch
from src.model.engine import VisionEngine
from src.utils.video_processing import create_focus_crop, get_video_duration
from src.config import Config
from src.prompts import DEFAULT_SYSTEM_PROMPT, DEFAULT_USER_PROMPT
from src.analysis.processing import map_detail_to_params, merge_results

logger = logging.getLogger(__name__)

class VideoAnalyzer:
    def __init__(self, config=None):
        self.config = config or Config
        self.engine = VisionEngine()
        # Ensure model is loaded if needed, or rely on VisionEngine lazy loading

    def reload_model(self, model_name):
        """
        Forces a reload of the model with the new name.
        """
        self.engine.load_model(model_name)

    def analyze_video(self, video_path, detail="medium", roi=None, system_prompt=None, user_prompt=None, progress_callback=None):
        """
        Main entry point for analyzing a video.
        """
        if not os.path.exists(video_path):
            logger.error(f"Video path does not exist: {video_path}")
            return None

        params = map_detail_to_params(detail)
        duration = get_video_duration(video_path)
        
        segment_duration = params["segment_duration"]
        num_segments = math.ceil(duration / segment_duration)
        
        msg = f"Splitting video into {num_segments} segments of {segment_duration}s each."
        logger.info(msg)
        if progress_callback:
            progress_callback({"type": "info", "message": msg, "total_segments": num_segments})
        
        segment_results = []
        
        # Use provided prompts or defaults
        sys_prompt_tmpl = system_prompt or DEFAULT_SYSTEM_PROMPT
        usr_prompt_tmpl = user_prompt or DEFAULT_USER_PROMPT

        for i in range(num_segments):
            start = i * segment_duration
            end = min((i + 1) * segment_duration, duration)
            
            if progress_callback:
                progress_callback({
                    "type": "segment_start", 
                    "segment_index": i, 
                    "total_segments": num_segments,
                    "start": start,
                    "end": end
                })

            seg_result = self._analyze_segment(
                video_path, start, end, params, i, num_segments, roi,
                sys_prompt_tmpl, usr_prompt_tmpl
            )
            segment_results.append(seg_result)
            
            if progress_callback:
                progress_callback({
                    "type": "segment_complete",
                    "segment_index": i,
                    "result": seg_result
                })

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                
        final_json = merge_results(segment_results, duration, params)
        return final_json, segment_results

    def _analyze_segment(self, video_path, start_time, end_time, params, segment_index, total_segments, roi, system_prompt_tmpl, user_prompt_tmpl):
        """
        Analyzes a single segment.
        """
        log_entry = {
            "segment_index": segment_index,
            "start_time": start_time,
            "end_time": end_time,
            "status": "pending",
            "raw_response": None,
            "parsed_events": [],
            "error": None
        }
        
        video_input_list = []
        
        # 1. Main Video
        video_input_list.append({
            "type": "video",
            "video": video_path,
            "max_pixels": params["max_pixels"],
            "fps": params["fps"],
            "video_start": start_time,
            "video_end": end_time
        })
        
        focus_prompt_part = ""
        crop_path = f"temp_crop_seg_{segment_index}.mp4"
        
        if roi:
            try:
                create_focus_crop(video_path, crop_path, roi, start_time=start_time, end_time=end_time)
                
                # 2. Focus Video
                video_input_list.append({
                    "type": "video",
                    "video": crop_path,
                    "max_pixels": params["max_pixels"],
                    "fps": params["fps"], 
                })
                
                focus_prompt_part = "\nVIDEO 1 is the FULL GAMEPLAY. VIDEO 2 is a ZOOMED CROP of the SKILL HUD (Bottom). Use Video 2 to precisely identify which skill icons (Q,W,E,R) go on cooldown or flash active."
                
            except Exception as e:
                logger.error(f"Failed to create crop for segment {segment_index}: {e}")

        # Format prompts
        system_prompt = system_prompt_tmpl.format(
            start_time=start_time,
            end_time=end_time,
            focus_prompt_part=focus_prompt_part
        )
        
        user_prompt = user_prompt_tmpl.format(
            start_time=start_time,
            end_time=end_time
        )
        
        content_list = []
        for v in video_input_list:
            content_list.append(v)
        content_list.append({"type": "text", "text": user_prompt})

        # Model-specific message formatting
        current_model = Config.MODEL_NAME
        
        if "Phi-3.5" in current_model:
            # Phi-3.5 usually expects a simpler structure or handles system prompts differently
            # For Phi-3.5 Vision via AutoProcessor, it often prefers just User/Assistant roles
            # and might not support the system role as a separate message object in the same way Qwen does via chat template.
            # We'll prepend the system prompt to the user text to be safe and compatible.
            
            # Remove system prompt from separate message and prepend to user text
            user_text_combined = f"{system_prompt}\n\n{user_prompt}"
            
            # Rebuild content list with new text
            content_list_phi = []
            for v in video_input_list:
                content_list_phi.append(v)
            content_list_phi.append({"type": "text", "text": user_text_combined})
            
            messages = [
                {"role": "user", "content": content_list_phi}
            ]
        else:
            # Default (Qwen and others supporting standard system role)
            messages = [
                {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
                {"role": "user", "content": content_list}
            ]
        
        print(f"   Analyzing Segment {segment_index+1}/{total_segments} ({start_time:.1f}s - {end_time:.1f}s)...")
        
        try:
            response = self.engine.analyze(messages, max_tokens=params["max_tokens"])
            log_entry["raw_response"] = response
            
            # Cleanup crop
            if roi and os.path.exists(crop_path):
                os.remove(crop_path)
            
            # Basic cleanup
            response = response.replace("```json", "").replace("```", "").strip()
            
            parsed = json.loads(response)
            
            if isinstance(parsed, list):
                log_entry["parsed_events"] = parsed
                log_entry["status"] = "success"
                log_entry["events"] = parsed
                return log_entry
            elif isinstance(parsed, dict) and "events" in parsed:
                log_entry["parsed_events"] = parsed["events"]
                log_entry["status"] = "success"
                log_entry["events"] = parsed["events"]
                return log_entry
            else:
                logger.warning(f"Unexpected JSON structure in segment {segment_index}: {parsed.keys()}")
                log_entry["status"] = "structure_error"
                log_entry["error"] = f"Unexpected keys: {parsed.keys()}"
                log_entry["events"] = []
                return log_entry
                
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON for segment {segment_index}")
            log_entry["status"] = "json_error"
            log_entry["error"] = "JSONDecodeError"
            log_entry["events"] = []
            if roi and os.path.exists(crop_path):
                os.remove(crop_path)
            return log_entry
        except Exception as e:
            logger.error(f"Error analyzing segment {segment_index}: {e}")
            log_entry["status"] = "execution_error"
            log_entry["error"] = str(e)
            log_entry["events"] = []
            if roi and os.path.exists(crop_path):
                os.remove(crop_path)
            return log_entry
