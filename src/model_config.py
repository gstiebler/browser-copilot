import os
from typing import Any
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.providers.openrouter import OpenRouterProvider
from pydantic_ai.providers.google_gla import GoogleGLAProvider


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


def get_model() -> Any:
    if OPENROUTER_MODEL != "":
        print(f"Using openrouter model: {OPENROUTER_MODEL}")
        return OpenAIModel(
            OPENROUTER_MODEL,
            provider=OpenRouterProvider(api_key=OPENROUTER_API_KEY),
        )
    else:
        print(f"Using Gemini model: {GEMINI_MODEL}")
        return GeminiModel(GEMINI_MODEL, provider=GoogleGLAProvider(api_key=GEMINI_API_KEY))
