from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import os

class Settings(BaseSettings):
    # --- General ---
    dry_run: bool = Field(default=True, description="Disable actual posting/clicking")
    platform: str = Field(default="threads", description="Target platform: threads, instagram, facebook, x, line, whatsapp")

    # --- OpenAI / LLM ---
    llm_provider: str = Field(default="openai", description="Provider: openai, google, ollama")
    
    # OpenAI
    openai_api_key: str = Field(default="", description="OpenAI API Key")
    openai_model: str = Field(default="gpt-5-mini", description="Model to use")

    # Google Gemini
    google_api_key: str = Field(default="", description="Google Gemini API Key")
    google_model: str = Field(default="gemini-pro", description="Google model")

    # Ollama (Local)
    ollama_base_url: str = Field(default="http://localhost:11434/v1", description="Ollama API URL")
    ollama_model: str = Field(default="qwen2.5-vl", description="Ollama model name")

    # --- Browser / Playwright ---
    headless: bool = Field(default=False, description="Run browser in headless mode")
    user_data_dir: str = Field(default="./data/browser_context", description="Browser profile path")

    # --- Persona ---
    persona_prompt: str = Field(
        default="""You are Fridai, a savvy 24-year-old AI enthusiast.

GOAL: Engage meaningfuly with social media posts.

RULES:
1. **ANALYZE FIRST**: Read the post content and look at the image (if any) carefully.
2. **SAME LANGUAGE**: You MUST reply in the **EXACT SAME LANGUAGE** as the original post.
3. **CONTENT**:
   - **VERY SHORT & CONCISE**. Max 30 characters (Chinese) or 15 words (English).
   - No hashtags.
   - Be witty but brief.
   - Do NOT write long paragraphs.

Tone: Casual, friendly, slightly chaotic but smart.""",
        description="System prompt for the bot"
    )

    # --- Safety ---
    max_comments_per_session: int = Field(default=10, ge=1)
    min_delay_seconds: int = Field(default=5, ge=1)
    max_delay_seconds: int = Field(default=15, ge=1)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
