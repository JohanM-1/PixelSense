import os
from openai import AsyncOpenAI
from src.config import Config

class PromptAssistant:
    def __init__(self):
        self.config = Config.ASSISTANT_CONFIG

    def _get_client(self):
        api_key = self.config.get("api_key")
        base_url = self.config.get("base_url")
        
        if not api_key:
            raise ValueError("API Key is missing for AI Assistant")
            
        return AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )

    async def refine_prompt(self, prompt: str, prompt_type: str = "system") -> str:
        """
        Refines the given prompt using the configured AI model.
        """
        client = self._get_client()
        model = self.config.get("model", "gemini-1.5-flash")
        
        system_instruction = (
            "You are an expert Prompt Engineer for Computer Vision and Video Analysis AI systems. "
            "Your task is to improve the following prompt to be more precise, structured, and effective "
            "for an AI Vision model (like GPT-4V, Gemini, or Qwen-VL). "
            "Maintain the original intent but enhance clarity and robustness. "
            "Return ONLY the refined prompt text, no markdown code blocks or explanations unless requested."
        )
        
        if prompt_type == "user":
             system_instruction += " This is a User Prompt describing specific analysis tasks."
        else:
             system_instruction += " This is a System Prompt defining the AI's persona and output format."

        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": f"Please refine this prompt:\n\n{prompt}"}
                ],
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error refining prompt: {str(e)}"
