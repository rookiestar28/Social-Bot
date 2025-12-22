from abc import ABC, abstractmethod
from openai import AsyncOpenAI
import google.generativeai as genai
from config import settings
import logging

logger = logging.getLogger(__name__)

class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, system_prompt: str, user_content: str, image_base64: str = None) -> str:
        pass

class OpenAIProvider(LLMProvider):
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model

    async def generate(self, system_prompt: str, user_content: str, image_base64: str = None) -> str:
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        if image_base64:
            # Multimodal payload
            user_msg = {
                "role": "user", 
                "content": [
                    {"type": "text", "text": user_content},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            }
            messages.append(user_msg)
        else:
            # Text-only payload
            messages.append({"role": "user", "content": user_content})

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=200
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            raise

class GoogleProvider(LLMProvider):
    def __init__(self):
        genai.configure(api_key=settings.google_api_key)
        # Verify model supports vision? Assuming gemini-pro-vision or similar if needed, 
        # but modern 'gemini-pro' or 'gemini-1.5-flash' handles both.
        self.model = genai.GenerativeModel(settings.google_model)

    async def generate(self, system_prompt: str, user_content: str, image_base64: str = None) -> str:
        content_parts = [system_prompt, "\n\nUser Post: " + user_content]
        
        if image_base64:
             # Convert base64 back to bytes for Gemini? 
             # Gemini API often takes a specific dict for blob
             import base64
             image_data = {
                 'mime_type': 'image/jpeg',
                 'data': base64.b64decode(image_base64)
             }
             content_parts.append(image_data)

        try:
            response = await self.model.generate_content_async(content_parts)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Google Gemini generation failed: {e}")
            raise

class OllamaProvider(LLMProvider):
    def __init__(self):
        # Ollama is OpenAI-compatible
        self.client = AsyncOpenAI(
            base_url=settings.ollama_base_url,
            api_key="ollama" 
        )
        self.model = settings.ollama_model

    async def generate(self, system_prompt: str, user_content: str, image_base64: str = None) -> str:
        messages = [
            {"role": "system", "content": system_prompt}
        ]

        if image_base64:
             # Standard OpenAI Vision format
            user_msg = {
                "role": "user", 
                "content": [
                    {"type": "text", "text": user_content},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            }
            messages.append(user_msg)
        else:
            messages.append({"role": "user", "content": user_content})

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=200
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise

class BotBrain:
    def __init__(self):
        self.provider = self._get_provider()
        logger.info(f"BotBrain initialized with provider: {settings.llm_provider}")

    def _get_provider(self) -> LLMProvider:
        p = settings.llm_provider.lower()
        if p == "google":
            return GoogleProvider()
        elif p == "ollama":
            return OllamaProvider()
        else:
            return OpenAIProvider()

    async def generate_comment(self, text_content: str, image_base64: str = None) -> str:
        if settings.dry_run:
            logger.info("[DRY_RUN] Generating mock comment")
            return "This is a dry-run comment mock!"
            
        return await self.provider.generate(
            system_prompt=settings.persona_prompt,
            user_content=text_content,
            image_base64=image_base64
        )
