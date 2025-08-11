from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class AppConfig:
    app_env: str = os.getenv("APP_ENV", "local")
    llm_provider: str = os.getenv("LLM_PROVIDER", "ollama")
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    comment_author: str = os.getenv("COMMENT_AUTHOR", "ADGM Corporate Agent")
    comment_initials: str = os.getenv("COMMENT_INITIALS", "AA")


CONFIG = AppConfig()
