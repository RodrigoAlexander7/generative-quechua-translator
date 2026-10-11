"""
Módulo de traducción generativa Quechua -> Español.
Implementa el patrón Puertos y Adaptadores (Arquitectura Hexagonal).
"""
from .prompt_templates import build_translation_prompt, SYSTEM_INSTRUCTION
from .orchestrator import QuechuaTranslator
from .ports.model_port import TranslationModelPort
from .adapters import (
    AgyAdapter,
    GeminiApiAdapter,
    OpenAIAdapter,
    OllamaAdapter,
    FallbackAdapter,
    ModelAdapterFactory,
)

__all__ = [
    "build_translation_prompt",
    "SYSTEM_INSTRUCTION",
    "QuechuaTranslator",
    "TranslationModelPort",
    "AgyAdapter",
    "GeminiApiAdapter",
    "OpenAIAdapter",
    "OllamaAdapter",
    "FallbackAdapter",
    "ModelAdapterFactory",
]
