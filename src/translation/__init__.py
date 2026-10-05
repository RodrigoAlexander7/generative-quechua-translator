"""Módulo de traducción generativa Quechua -> Español."""
from .prompt_templates import build_translation_prompt, SYSTEM_INSTRUCTION
from .orchestrator import QuechuaTranslator

__all__ = ["build_translation_prompt", "SYSTEM_INSTRUCTION", "QuechuaTranslator"]
