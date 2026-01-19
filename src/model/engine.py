import torch
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, AutoModelForCausalLM, MllamaForConditionalGeneration
from qwen_vl_utils import process_vision_info
from PIL import Image
import logging
import os
from openai import OpenAI
from src.config import Config

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VisionEngine:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VisionEngine, cls).__new__(cls)
            cls._instance.model = None
            cls._instance.processor = None
            cls._instance.device = "cuda" if torch.cuda.is_available() else "cpu"
            cls._instance.current_model_name = None
            cls._instance.api_client = None
        return cls._instance

    def load_model(self, model_name: str = "Qwen/Qwen2.5-VL-3B-Instruct"):
        """
        Carga el modelo y el procesador en memoria.
        Soporta Qwen 2.5 VL, Phi-3.5 Vision y Llama 3.2 Vision.
        Also handles API-based models.
        """
        if self.model is not None and self.current_model_name == model_name:
            logger.info("Model already loaded.")
            return

        # Check if it is an API model
        if "gemini" in model_name or "api" in model_name:
             logger.info(f"Configuring API model {model_name}...")
             api_key = Config.ASSISTANT_CONFIG.get("api_key")
             base_url = Config.ASSISTANT_CONFIG.get("base_url")
             if not api_key:
                 logger.error("API Key missing for Gemini Vision")
                 raise ValueError("API Key is required for Gemini Vision")
             
             self.api_client = OpenAI(api_key=api_key, base_url=base_url)
             self.current_model_name = model_name
             
             # Unload local model if exists to save VRAM
             if self.model is not None:
                logger.info("Unloading local model to free VRAM for API usage...")
                del self.model
                del self.processor
                self.model = None
                self.processor = None
                if self.device == "cuda":
                    torch.cuda.empty_cache()
             return

        # Si hay un modelo cargado pero es diferente, liberarlo
        if self.model is not None:
            logger.info("Unloading previous model...")
            del self.model
            del self.processor
            if self.device == "cuda":
                torch.cuda.empty_cache()

        logger.info(f"Loading model {model_name} on {self.device}...")
        
        try:
            dtype = torch.bfloat16 if self.device == "cuda" and torch.cuda.is_bf16_supported() else torch.float16
            
            if "Qwen" in model_name:
                self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
                    model_name,
                    torch_dtype=dtype,
                    device_map="auto" if self.device == "cuda" else None,
                )
                self.processor = AutoProcessor.from_pretrained(model_name)
                
            elif "Tongyi-MAI" in model_name:
                # MAI-UI Handling
                # MAI-UI uses Qwen3VL architecture
                try:
                    from transformers import AutoModelForCausalLM, AutoConfig
                    
                    # Force loading the configuration from remote code first
                    # This registers the Qwen3VLConfig class
                    config = AutoConfig.from_pretrained(model_name, trust_remote_code=True)
                    
                    self.model = AutoModelForCausalLM.from_pretrained(
                        model_name,
                        config=config,
                        torch_dtype=dtype,
                        device_map="auto" if self.device == "cuda" else None,
                        trust_remote_code=True
                    )
                    self.processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)
                except Exception as e:
                    logger.error(f"Error loading MAI model: {e}")
                    raise e

            elif "Phi-3.5-vision" in model_name:
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_name, 
                    device_map="auto" if self.device == "cuda" else None, 
                    torch_dtype=dtype, 
                    trust_remote_code=True, 
                    _attn_implementation='eager' 
                    # Force eager attention to completely bypass Flash Attention checks
                )
                self.processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)
                
            elif "Llama-3.2" in model_name:
                self.model = MllamaForConditionalGeneration.from_pretrained(
                    model_name,
                    torch_dtype=dtype,
                    device_map="auto" if self.device == "cuda" else None,
                )
                self.processor = AutoProcessor.from_pretrained(model_name)
            else:
                # Fallback genérico
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    torch_dtype=dtype,
                    device_map="auto" if self.device == "cuda" else None,
                )
                self.processor = AutoProcessor.from_pretrained(model_name)

            if self.device == "cpu":
                self.model.to("cpu")
                
            self.current_model_name = model_name
            logger.info("Model loaded successfully.")
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise e

    def analyze(self, messages: list, max_tokens: int = 2048) -> str:
        """
        Realiza la inferencia sobre una lista de mensajes estructurados (Chat Format).
        """
        if self.current_model_name is None:
            self.load_model() # Carga default si no hay nada

        if "gemini" in self.current_model_name:
            return self._analyze_gemini_api(messages, max_tokens)
        elif "Qwen" in self.current_model_name:
            return self._analyze_qwen(messages, max_tokens)
        elif "Tongyi-MAI" in self.current_model_name:
            # MAI uses similar flow to Qwen but might have different chat template handling
            return self._analyze_qwen(messages, max_tokens)
        elif "Phi-3.5-vision" in self.current_model_name:
            return self._analyze_phi(messages, max_tokens)
        elif "Llama-3.2" in self.current_model_name:
            return self._analyze_llama(messages, max_tokens)
        else:
            return self._analyze_generic(messages, max_tokens)

    def _analyze_gemini_api(self, messages, max_tokens):
        # Convert local message format to OpenAI/Gemini format
        # Local format often has complex objects for images (PIL images)
        # We need to convert PIL images to base64 for API
        import base64
        import io

        api_messages = []
        for msg in messages:
            content = []
            if isinstance(msg["content"], str):
                content = msg["content"]
            elif isinstance(msg["content"], list):
                for item in msg["content"]:
                    if item["type"] == "text":
                        content.append({"type": "text", "text": item["text"]})
                    elif item["type"] == "image":
                        # Convert PIL to base64
                        img = item["image"]
                        buffered = io.BytesIO()
                        img.save(buffered, format="JPEG")
                        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
                        content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img_str}"
                            }
                        })
            
            api_messages.append({
                "role": msg["role"],
                "content": content
            })

        try:
            response = self.api_client.chat.completions.create(
                model=self.current_model_name,
                messages=api_messages,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"API Error: {e}")
            return f"Error calling API: {str(e)}"

    def _analyze_qwen(self, messages, max_tokens):
        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        if self.device == "cuda": torch.cuda.empty_cache()
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = self.processor(text=[text], images=image_inputs, videos=video_inputs, padding=True, return_tensors="pt")
        inputs = inputs.to(self.device)
        with torch.no_grad():
            generated_ids = self.model.generate(**inputs, max_new_tokens=max_tokens)
        generated_ids_trimmed = [out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)]
        output_text = self.processor.batch_decode(generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)
        return output_text[0]

    def _analyze_phi(self, messages, max_tokens):
        # Phi-3.5 Vision handling
        # Extract images from messages
        images = []
        prompt_content = []
        
        for msg in messages:
            if msg["role"] == "user":
                if isinstance(msg["content"], list):
                    for item in msg["content"]:
                        if item["type"] == "image":
                            images.append(item["image"])
                            prompt_content.append({"type": "image"})
                        elif item["type"] == "text":
                            prompt_content.append({"type": "text", "text": item["text"]})
                        # Video handling for Phi needs frame extraction beforehand
                        # Currently we assume video inputs are converted to images if passed here, 
                        # or we need to update pipeline to sample frames for non-Qwen models.
                        # For now, let's assume pipeline handles video extraction or we fail gracefully.
                else:
                    prompt_content.append({"type": "text", "text": msg["content"]})
        
        # Phi prompt structure
        user_msg = {"role": "user", "content": prompt_content}
        processed_messages = [user_msg] # System prompt is usually prepended or handled by chat template
        
        # Add system prompt if exists (Phi might just treat it as text)
        sys_prompt = next((m["content"] for m in messages if m["role"] == "system"), "")
        if sys_prompt:
             # Phi doesn't strictly have a system role in some versions, but we can prepend
             pass 

        prompt = self.processor.tokenizer.apply_chat_template(processed_messages, tokenize=False, add_generation_prompt=True)
        
        inputs = self.processor(prompt, images=images if images else None, return_tensors="pt").to(self.device)
        
        generation_args = { 
            "max_new_tokens": max_tokens, 
            "temperature": 0.0, 
            "do_sample": False, 
        } 

        generate_ids = self.model.generate(**inputs, eos_token_id=self.processor.tokenizer.eos_token_id, **generation_args) 
        # Remove input tokens 
        generate_ids = generate_ids[:, inputs['input_ids'].shape[1]:]
        response = self.processor.batch_decode(generate_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0] 
        return response

    def _analyze_llama(self, messages, max_tokens):
        # Llama 3.2 Vision handling
        # Similar extraction
        text = self.processor.apply_chat_template(messages, add_generation_prompt=True)
        
        # Extract images (Llama supports video/image inputs via processor)
        # Note: Llama processor expects <|image|> tokens in text
        # The apply_chat_template should handle this if formatted correctly.
        
        # For simplicity, reuse basic extraction logic or assume processor handles list of dicts
        # Currently transformers apply_chat_template for Llama handles list of dicts with type: image
        
        images = []
        for msg in messages:
            if msg["role"] == "user" and isinstance(msg["content"], list):
                for item in msg["content"]:
                    if item["type"] == "image":
                        images.append(item["image"])
        
        inputs = self.processor(text=text, images=images if images else None, return_tensors="pt").to(self.device)
        
        with torch.no_grad():
            generated_ids = self.model.generate(**inputs, max_new_tokens=max_tokens)
            
        generated_ids = generated_ids[:, inputs['input_ids'].shape[1]:]
        return self.processor.decode(generated_ids[0], skip_special_tokens=True)

    def _analyze_generic(self, messages, max_tokens):
        # Basic fallback
        return "Model not fully supported in this engine version."

    def analyze_image(self, image: Image.Image, prompt: str = "Describe what you see in this image.") -> str:
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt},
                ],
            }
        ]
        return self.analyze(messages)
