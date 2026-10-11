"""Adaptadores para modelos de inferencia generativa."""
from .base import parse_llm_json_response, clean_json_text
from .agy_adapter import AgyAdapter
from .gemini_api_adapter import GeminiApiAdapter
from .openai_adapter import OpenAIAdapter
from .ollama_adapter import OllamaAdapter
from .fallback_adapter import FallbackAdapter
from .factory import ModelAdapterFactory

__all__ = [
    "parse_llm_json_response",
    "clean_json_text",
    "AgyAdapter",
    "GeminiApiAdapter",
    "OpenAIAdapter",
    "OllamaAdapter",
    "FallbackAdapter",
    "ModelAdapterFactory",
]
