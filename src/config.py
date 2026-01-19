
class Config:
    # Model Configuration
    MODEL_NAME = "microsoft/Phi-3.5-vision-instruct"
    
    # Available Models
    AVAILABLE_MODELS = [
        {
            "id": "Qwen/Qwen2.5-VL-3B-Instruct",
            "name": "Qwen 2.5 VL 3B (Fast & Native Video)",
            "provider": "Alibaba Cloud",
            "type": "qwen"
        },
        {
            "id": "microsoft/Phi-3.5-vision-instruct",
            "name": "Phi-3.5 Vision (Microsoft)",
            "provider": "Microsoft",
            "type": "phi"
        },
        {
            "id": "meta-llama/Llama-3.2-11B-Vision-Instruct",
            "name": "Llama 3.2 11B Vision (Meta)",
            "provider": "Meta",
            "type": "llama"
        },
        {
            "id": "gemini-2.0-flash",
            "name": "Gemini 2.0 Flash (API)",
            "provider": "Google",
            "type": "gemini-api"
        }
    ]
    
    USE_API = False
    
    # Analysis Configuration
    DEFAULT_DETAIL = "medium"

    # AI Assistant Configuration (Prompt Editor)
    ASSISTANT_CONFIG = {
        "provider": "gemini", # 'gemini', 'openai', 'kilo'
        "api_key": "",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/", # Default for Gemini
        "model": "gemini-1.5-flash-8b"
    }
