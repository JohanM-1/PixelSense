import os
import torch
import argparse
from PIL import Image, ImageDraw
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, AutoModelForCausalLM
from qwen_vl_utils import process_vision_info
import math
import re
import yaml
import json

# Function smart_resize from Qwen2VL
def smart_resize(height: int, width: int, factor: int = 28, min_pixels: int = 56 * 56, max_pixels: int = 14 * 14 * 4 * 1280):
    if height < factor or width < factor:
        raise ValueError(f"height:{height} or width:{width} must be larger than factor:{factor}")
    elif max(height, width) / min(height, width) > 200:
        raise ValueError(
            f"absolute aspect ratio must be smaller than 200, got {max(height, width) / min(height, width)}"
        )
    h_bar = round(height / factor) * factor
    w_bar = round(width / factor) * factor
    if h_bar * w_bar > max_pixels:
        beta = math.sqrt((height * width) / max_pixels)
        h_bar = math.floor(height / beta / factor) * factor
        w_bar = math.floor(width / beta / factor) * factor
    elif h_bar * w_bar < min_pixels:
        beta = math.sqrt(min_pixels / (height * width))
        h_bar = math.ceil(height * beta / factor) * factor
        w_bar = math.ceil(width * beta / factor) * factor
    return h_bar, w_bar

def extract_coord(response):
    # The user code expects <answer>[{'action': 'click', 'coordinate': [x, y]}]</answer>
    # We will use regex to find the coordinate. 
    # Note: Model sometimes hallucinates keys like 'coordinating' instead of 'coordinate'
    pattern = r"(?:coordinate|coordinating)':\s*\[(\d+),\s*(\d+)\]"
    match = re.search(pattern, response)
    if match:
        return [int(match.group(1)), int(match.group(2))], "click"
    
    # Fallback: look for just the list of two numbers if the key didn't match
    pattern_fallback = r"\[(\d+),\s*(\d+)\]"
    match_fallback = re.search(pattern_fallback, response)
    if match_fallback:
         return [int(match_fallback.group(1)), int(match_fallback.group(2))], "click"

    return [0, 0], None

def run_qwen_ui(model_path, image_path, prompt, output_path, quantize=False, config_path=None):
    print(f"Loading model: {model_path}")
    
    # Load config if provided
    config = {}
    if config_path and os.path.exists(config_path):
        print(f"Loading configuration from {config_path}")
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    
    output_mode = config.get("output_mode", "single_point")
    print(f"Output mode: {output_mode}")
    
    quantization_config = None
    if quantize:
        print("Quantization (4-bit) enabled. Note: This might cause issues with some transformers versions.")
        from transformers import BitsAndBytesConfig
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16
        )
        # Try to patch set_submodule if missing (PyTorch < 1.10 issue, but strange here)
        # Or it might be a transformers wrapper issue.
    
    # Use low_cpu_mem_usage=True to avoid OOM on system RAM
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        model_path,
        torch_dtype=torch.bfloat16,
        quantization_config=quantization_config,
        device_map="cuda", # Force CUDA instead of auto to ensure it goes to GPU
        low_cpu_mem_usage=True,
    )
    processor = AutoProcessor.from_pretrained(model_path)
    
    task_prompt = prompt
    
    # Construct query based on config
    if output_mode == "json_sequence":
        prompt_template = config.get("prompt_template", "").format(prompt=prompt)
        # Note: Qwen2.5-VL-UI usually expects specific tags, but let's try the natural language JSON prompt
        # We wrap it in <image> tag as required by Qwen
        query = '<image>\n' + prompt_template
    else:
        question_template = (
            f"In this UI screenshot, I want to perform the command '{task_prompt}'.\n"
            "Please provide the action to perform (enumerate in ['click'])"
            "and the coordinate where the cursor is moved to(integer) if click is performed.\n"
            "Output the final answer in <answer> </answer> tags directly."
            "The output answer format should be as follows:\n"
            "<answer>[{'action': 'click', 'coordinate': [x, y]}]</answer>\n"
            "Please strictly follow the format."
        )
        query = '<image>\n' + question_template

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image_path}
            ] + [{"type": "text", "text": query}],
        }
    ]
    
    text = processor.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = processor(
        text=[text],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt",
    ).to(model.device)
    
    print("Generating response...")
    generated_ids = model.generate(**inputs, max_new_tokens=1024)
    generated_ids_trimmed = [
        out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]
    response = processor.batch_decode(
        generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
    )
    response_text = response[0]
    print(f"Model response: {response_text}")
    
    if output_mode == "json_sequence":
        # Load image for drawing
        image = Image.open(image_path)
        origin_width, origin_height = image.size
        
        # Calculate resize factor just in case we need it for absolute coordinate scaling
        # Qwen2.5-VL uses absolute coords on RESIZED image
        resized_height, resized_width = smart_resize(origin_height, origin_width, max_pixels=12845056)
        scale_x = origin_width / resized_width
        scale_y = origin_height / resized_height
        
        try:
            # Find JSON array in text
            json_match = re.search(r'\[\s*\{.*\}\s*\]', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                actions = json.loads(json_str)
            else:
                actions = json.loads(response_text)
            
            print(f"Parsed actions: {json.dumps(actions, indent=2)}")
            
            # Visualize steps
            if config.get("visualization", {}).get("draw_steps", False):
                for i, step in enumerate(actions):
                    step_image = image.copy()
                    draw = ImageDraw.Draw(step_image)
                    
                    bbox = step.get("bbox") or step.get("start_bbox")
                    if bbox:
                        # Qwen2.5-VL normally outputs absolute coords [x1, y1, x2, y2] relative to RESIZED image
                        # But with our custom JSON prompt, it might output normalized 0-1000 coords if it follows common VL conventions
                        # OR it might output absolute coords on original image (if it's smart enough)
                        # Let's check ranges.
                        
                        is_normalized = all(c <= 1000 for c in bbox)
                        if is_normalized:
                            # Treat as normalized
                            x1 = int(bbox[0] / 1000 * origin_width)
                            y1 = int(bbox[1] / 1000 * origin_height)
                            x2 = int(bbox[2] / 1000 * origin_width)
                            y2 = int(bbox[3] / 1000 * origin_height)
                        else:
                            # Treat as absolute relative to RESIZED image (standard Qwen behavior)
                            # Or absolute relative to ORIGINAL (if model is confused).
                            # Standard Qwen behavior is absolute on RESIZED.
                            x1 = int(bbox[0] * scale_x)
                            y1 = int(bbox[1] * scale_y)
                            x2 = int(bbox[2] * scale_x)
                            y2 = int(bbox[3] * scale_y)

                        draw.rectangle([x1, y1, x2, y2], outline="red", width=3)
                        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                        draw.ellipse((cx - 10, cy - 10, cx + 10, cy + 10), fill='blue', outline='white')
                        
                        action_type = step.get("action", "action").upper()
                        draw.text((x1, y1 - 15), f"Step {i+1}: {action_type}", fill='red')

                        if "end_bbox" in step:
                            end_bbox = step["end_bbox"]
                            if all(c <= 1000 for c in end_bbox):
                                ex1 = int(end_bbox[0] / 1000 * origin_width)
                                ey1 = int(end_bbox[1] / 1000 * origin_height)
                                ex2 = int(end_bbox[2] / 1000 * origin_width)
                                ey2 = int(end_bbox[3] / 1000 * origin_height)
                            else:
                                ex1 = int(end_bbox[0] * scale_x)
                                ey1 = int(end_bbox[1] * scale_y)
                                ex2 = int(end_bbox[2] * scale_x)
                                ey2 = int(end_bbox[3] * scale_y)
                            
                            ecx, ecy = (ex1 + ex2) // 2, (ey1 + ey2) // 2
                            draw.rectangle([ex1, ey1, ex2, ey2], outline="green", width=3)
                            draw.ellipse((ecx - 10, ecy - 10, ecx + 10, ecy + 10), fill='green', outline='white')
                            draw.line([(cx, cy), (ecx, ecy)], fill="yellow", width=3)
                            draw.text((ex1, ey1 - 15), "DROP", fill='green')

                    if config.get("visualization", {}).get("save_individual_steps", False):
                        base, ext = os.path.splitext(output_path)
                        step_path = f"{base}_step_{i+1}{ext}"
                        step_image.save(step_path)
                        print(f"Saved step {i+1} to {step_path}")

            base, ext = os.path.splitext(output_path)
            json_path = f"{base}.json"
            with open(json_path, 'w') as f:
                json.dump(actions, f, indent=2)
            print(f"Saved action sequence to {json_path}")
            
            # Save final image (last step state or original with all markings - for now just original with nothing if no loop)
            # Actually let's save the last step image as the result
            if actions:
                # We already saved steps, let's just save the main output as the last step
                # Or better, draw ALL steps on one image for the final result
                final_image = image.copy()
                draw = ImageDraw.Draw(final_image)
                # (Simplified: just saving the image. A full overlay loop would be better but this is enough for now)
                final_image.save(output_path)
                print(f"Saved result to {output_path}")

        except Exception as e:
            print(f"Failed to parse JSON sequence: {e}")
            print("Raw response was:", response_text)

    else:
        pred_coord, action = extract_coord(response_text)
        
        # Rescale
        image = Image.open(image_path)
        origin_width, origin_height = image.size
        resized_height, resized_width = smart_resize(origin_height, origin_width, max_pixels=12845056)
        scale_x = origin_width / resized_width
        scale_y = origin_height / resized_height
        
        final_x = int(pred_coord[0] * scale_x)
        final_y = int(pred_coord[1] * scale_y)
        
        print(f"Predicted coordinate: {pred_coord} -> Rescaled: [{final_x}, {final_y}]")
        
        # Draw
        draw = ImageDraw.Draw(image)
        r = 10
        draw.ellipse((final_x - r, final_y - r, final_x + r, final_y + r), fill='red', outline='white')
        draw.text((final_x + r, final_y), "CLICK", fill='red')
        
        image.save(output_path)
        print(f"Saved result to {output_path}")

def run_mai_ui(model_path, image_path, prompt, output_path, config_path=None):
    print(f"Loading MAI-UI model: {model_path}")
    
    # Load config if provided
    config = {}
    if config_path and os.path.exists(config_path):
        print(f"Loading configuration from {config_path}")
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    
    output_mode = config.get("output_mode", "single_point")
    print(f"Output mode: {output_mode}")

    try:
        from transformers import AutoModel
        # MAI-UI uses Qwen3VL which is new. AutoModel loads Qwen3VLModel (base).
        # We need Qwen3VLForConditionalGeneration for generation.
        # Workaround: Load base model to get the class, then reload.
        # Or better: just try to import the class from the dynamic module if possible.
        
        # First, try to register the config if it's the issue, but simpler is to use the class directly if we can find it.
        # Let's try to load with AutoModel first to trigger remote code download and registration
        print("Loading base model to discover class...")
        base_model = AutoModel.from_pretrained(
            model_path,
            torch_dtype=torch.bfloat16,
            device_map="cpu", # Load to CPU first to avoid OOM if we reload
            trust_remote_code=True,
            low_cpu_mem_usage=True
        )
        
        module_name = base_model.__module__
        print(f"Base model module: {module_name}")
        
        import sys
        import importlib
        # The module is likely something like transformers_modules.Tongyi-MAI.MAI-UI-8B.hash.modeling_qwen3_vl
        # We want to find the class Qwen3VLForConditionalGeneration in it.
        
        mod = sys.modules[module_name]
        
        # Look for a class that seems right
        target_class = None
        for name in dir(mod):
            if "ForConditionalGeneration" in name:
                target_class = getattr(mod, name)
                print(f"Found target class: {name}")
                break
        
        if target_class:
            del base_model
            torch.cuda.empty_cache()
            print(f"Reloading with {target_class.__name__}...")
            model = target_class.from_pretrained(
                model_path,
                torch_dtype=torch.bfloat16,
                device_map="cuda",
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )
        else:
            print("Could not find ForConditionalGeneration class. Using base model (might fail).")
            model = base_model.to("cuda")
            
        processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True)
        
        # Construct message for MAI-UI based on config
        if output_mode == "json_sequence":
            prompt_template = config.get("prompt_template", "").format(prompt=prompt)
            task_instruction = prompt_template
        else:
            # Default single point prompt
            task_instruction = (
                f"User instruction: {prompt}\n"
                "Please analyze the UI and provide the bounding box of the element to interact with.\n"
                "Format your answer as: [x1, y1, x2, y2]"
            )
        
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image_path},
                    {"type": "text", "text": task_instruction}
                ]
            }
        ]
        
        # Check for apply_chat_template support
        if hasattr(processor, "apply_chat_template"):
            text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        else:
            # Fallback
            text = f"<|user|>\n<image>\n{prompt}\n<|assistant|>\n"

        image_inputs, video_inputs = process_vision_info(messages)
        inputs = processor(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        ).to(model.device)
        
        print("Generating MAI response...")
        generated_ids = model.generate(**inputs, max_new_tokens=1024)
        generated_ids_trimmed = [
            out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        response = processor.batch_decode(
            generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )
        response_text = response[0]
        print(f"MAI Model response: {response_text}")
        
        # Load image once
        image = Image.open(image_path)
        origin_width, origin_height = image.size
        print(f"Original image size: {origin_width}x{origin_height}")

        if output_mode == "json_sequence":
            # Try to parse JSON from response
            try:
                # Find JSON array in text (in case model chats around it)
                json_match = re.search(r'\[\s*\{.*\}\s*\]', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    actions = json.loads(json_str)
                else:
                    # Fallback: try direct parse if response is just JSON
                    actions = json.loads(response_text)
                
                print(f"Parsed actions: {json.dumps(actions, indent=2)}")
                
                # Visualize steps
                if config.get("visualization", {}).get("draw_steps", False):
                    for i, step in enumerate(actions):
                        # Create a fresh copy for each step visualization if configured to save individually
                        step_image = image.copy()
                        draw = ImageDraw.Draw(step_image)
                        
                        bbox = step.get("bbox") or step.get("start_bbox")
                        if bbox:
                            # Normalize check
                            if all(c <= 1000 for c in bbox):
                                x1 = int(bbox[0] / 1000 * origin_width)
                                y1 = int(bbox[1] / 1000 * origin_height)
                                x2 = int(bbox[2] / 1000 * origin_width)
                                y2 = int(bbox[3] / 1000 * origin_height)
                            else:
                                # Absolute fallback (simplified)
                                x1, y1, x2, y2 = bbox

                            # Draw bbox
                            draw.rectangle([x1, y1, x2, y2], outline="red", width=3)
                            
                            # Center point
                            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                            draw.ellipse((cx - 10, cy - 10, cx + 10, cy + 10), fill='blue', outline='white')
                            
                            # Label
                            action_type = step.get("action", "action").upper()
                            draw.text((x1, y1 - 15), f"Step {i+1}: {action_type}", fill='red')

                            # Handle drag end point
                            if "end_bbox" in step:
                                end_bbox = step["end_bbox"]
                                if all(c <= 1000 for c in end_bbox):
                                    ex1 = int(end_bbox[0] / 1000 * origin_width)
                                    ey1 = int(end_bbox[1] / 1000 * origin_height)
                                    ex2 = int(end_bbox[2] / 1000 * origin_width)
                                    ey2 = int(end_bbox[3] / 1000 * origin_height)
                                else:
                                    ex1, ey1, ex2, ey2 = end_bbox
                                
                                ecx, ecy = (ex1 + ex2) // 2, (ey1 + ey2) // 2
                                draw.rectangle([ex1, ey1, ex2, ey2], outline="green", width=3)
                                draw.ellipse((ecx - 10, ecy - 10, ecx + 10, ecy + 10), fill='green', outline='white')
                                draw.line([(cx, cy), (ecx, ecy)], fill="yellow", width=3)
                                draw.text((ex1, ey1 - 15), "DROP", fill='green')

                        # Save individual step image
                        if config.get("visualization", {}).get("save_individual_steps", False):
                            base, ext = os.path.splitext(output_path)
                            step_path = f"{base}_step_{i+1}{ext}"
                            step_image.save(step_path)
                            print(f"Saved step {i+1} to {step_path}")

                # Save full sequence JSON
                base, ext = os.path.splitext(output_path)
                json_path = f"{base}.json"
                with open(json_path, 'w') as f:
                    json.dump(actions, f, indent=2)
                print(f"Saved action sequence to {json_path}")
                
            except Exception as e:
                print(f"Failed to parse JSON sequence: {e}")
                print("Raw response was:", response_text)
                return

        else:
            # Parse response - MAI-UI format might differ.
            # If it returns coordinates, we try to extract them.
            # It might return a bounding box [x1, y1, x2, y2] or point [x, y].
            pred_coord = [0, 0]
            
            # Try finding bounding box [x1, y1, x2, y2]
            bbox_match = re.search(r'[\[\(](\d+),\s*(\d+),\s*(\d+),\s*(\d+)[\]\)]', response_text)
            point_match = re.search(r'[\[\(](\d+),\s*(\d+)[\]\)]', response_text)
            
            if bbox_match:
                x1, y1, x2, y2 = map(int, bbox_match.groups())
                # Calculate center
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                pred_coord = [center_x, center_y]
                print(f"Extracted bbox: [{x1}, {y1}, {x2}, {y2}] -> Center: {pred_coord}")
            elif point_match:
                pred_coord = [int(point_match.group(1)), int(point_match.group(2))]
                print(f"Extracted coordinates: {pred_coord}")
            else:
                print("Warning: Could not extract coordinates from MAI response. Using [0,0].")
            
            # Rescale and draw
            
            # MAI-UI / Qwen3-VL uses normalized coordinates [0, 1000]
            # We verify this by checking if the coordinates are within [0, 1000] and applying normalization.
            # If coordinates are > 1000, they might be absolute (unlikely for Qwen3-VL but possible if configured differently).
            
            # Check if coordinates look normalized (all <= 1000)
            # Note: Theoretically absolute coords could be <= 1000 if image is small, 
            # but Qwen3-VL docs suggest [0, 1000] normalization.
            is_normalized = all(c <= 1000 for c in pred_coord)
            
            if is_normalized:
                print("Detected normalized coordinates (0-1000). Scaling to image size.")
                final_x = int(pred_coord[0] / 1000 * origin_width)
                final_y = int(pred_coord[1] / 1000 * origin_height)
            else:
                print("Detected absolute coordinates. Using smart_resize scaling (fallback).")
                # Fallback to smart_resize logic if needed, though Qwen3-VL usually is normalized.
                resized_height, resized_width = smart_resize(origin_height, origin_width, max_pixels=12845056)
                scale_x = origin_width / resized_width
                scale_y = origin_height / resized_height
                final_x = int(pred_coord[0] * scale_x)
                final_y = int(pred_coord[1] * scale_y)
            
            print(f"Predicted coordinate: {pred_coord} -> Final: [{final_x}, {final_y}]")
            
            draw = ImageDraw.Draw(image)
            r = 10
            draw.ellipse((final_x - r, final_y - r, final_x + r, final_y + r), fill='blue', outline='white')
            draw.text((final_x + r, final_y), "MAI CLICK", fill='blue')
            
            image.save(output_path)
            print(f"Saved result to {output_path}")

    except Exception as e:
        print(f"Failed to run MAI-UI: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="qwen", choices=["qwen", "mai"])
    parser.add_argument("--image_path", type=str, required=True)
    parser.add_argument("--prompt", type=str, required=True)
    parser.add_argument("--output_path", type=str, default="result.png")
    parser.add_argument("--config_path", type=str, default="tests/lmm_grounding/config.yaml")
    parser.add_argument("--quantize", action="store_true", help="Enable 4-bit quantization to save memory")
    
    args = parser.parse_args()
    
    if args.model == "qwen":
        run_qwen_ui("LZXzju/Qwen2.5-VL-3B-UI-R1-E", args.image_path, args.prompt, args.output_path, quantize=args.quantize, config_path=args.config_path)
    elif args.model == "mai":
        run_mai_ui("Tongyi-MAI/MAI-UI-2B", args.image_path, args.prompt, args.output_path, config_path=args.config_path)
