import os
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.models.gemini import GeminiModel, GeminiModelSettings, ThinkingConfig
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.openrouter import OpenRouterProvider
from pydantic_ai.providers.google_gla import GoogleGLAProvider
from pydantic_ai.providers.anthropic import AnthropicProvider


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

thinking_budget = 1000


def get_model(full_model_name: str) -> Model:
    gemini_thinking_config = ThinkingConfig(include_thoughts=True, thinking_budget=thinking_budget)
    gemini_model_settings = GeminiModelSettings(gemini_thinking_config=gemini_thinking_config)

    model_parts = full_model_name.split("/")
    if len(model_parts) < 2:
        raise ValueError(
            f"Invalid model name format: {full_model_name}. Expected format: 'provider/model_name'."
        )
    provider = model_parts[0]
    model_name = "/".join(model_parts[1:])
    provider_to_model_creator = {
        "openrouter": lambda: OpenAIModel(
            model_name,
            provider=OpenRouterProvider(api_key=OPENROUTER_API_KEY),
        ),
        "google": lambda: GeminiModel(
            model_name,
            provider=GoogleGLAProvider(api_key=GEMINI_API_KEY),
            settings=gemini_model_settings,
        ),
        "anthropic": lambda: AnthropicModel(
            model_name,
            provider=AnthropicProvider(api_key=ANTHROPIC_API_KEY),
        ),
    }

    if provider not in provider_to_model_creator:
        raise ValueError(f"Unknown provider: {provider}")

    return provider_to_model_creator[provider]()
