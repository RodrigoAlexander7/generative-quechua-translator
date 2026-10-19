"""
Orquestador de traducción generativa Quechua -> Español.
Refactorizado bajo el patrón de Puertos y Adaptadores (Arquitectura Hexagonal).

Clase QuechuaTranslator:
- Invoca la segmentación morfo-semántica (Scaffold) de la Etapa 1.
- Genera el prompt estructurado con directivas lingüísticas estrictas.
- Delega la inferencia generativa a un adaptador que implementa TranslationModelPort:
  * AgyAdapter (Antigravity CLI con Gemini)
  * OllamaAdapter (Modelos locales como Llama 3, Qwen, Mistral)
  * GeminiApiAdapter (Google Gemini API directa vía GEMINI_API_KEY)
  * OpenAIAdapter (OpenAI GPT-4o / compatibles vía OPENAI_API_KEY)
  * FallbackAdapter (Reglas morfológicas y glosas deterministas)
"""

import os
import json
import re
from typing import Any, Dict, Optional, List, Union

from .prompt_templates import build_translation_prompt, SYSTEM_INSTRUCTION
from .ports.model_port import TranslationModelPort
from .adapters.factory import ModelAdapterFactory, load_settings
from .adapters.fallback_adapter import FallbackAdapter


class QuechuaTranslator:
    """
    Traductor Generativo y Analizador Morfo-Semántico para Quechua.
    Utiliza Puertos y Adaptadores para desacoplar el motor generativo.
    """

    def __init__(
        self,
        adapter: Optional[TranslationModelPort] = None,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        db_path: Optional[str] = None,
        use_agy: Optional[bool] = None,
        ollama_host: Optional[str] = None,
        openai_base_url: Optional[str] = None,
        agy_bin: Optional[str] = None
    ):
        cfg = load_settings()
        self.db_path = db_path
        self.fallback_adapter = FallbackAdapter()

        # Determinar si se fuerza un proveedor por compatibilidad con use_agy
        effective_provider = provider
        if effective_provider is None:
            if use_agy is True:
                effective_provider = "agy"
            elif use_agy is False:
                # Si se desactiva agy explícitamente, intentar gemini -> openai -> ollama -> fallback
                if api_key or os.environ.get("GEMINI_API_KEY"):
                    effective_provider = "gemini"
                elif os.environ.get("OPENAI_API_KEY"):
                    effective_provider = "openai"
                else:
                    effective_provider = "ollama"

        # Si se inyectó un adaptador directamente, usarlo
        if adapter is not None:
            self.adapter = adapter
        else:
            self.adapter = ModelAdapterFactory.create_adapter(
                provider=effective_provider,
                model_name=model_name,
                api_key=api_key,
                ollama_host=ollama_host,
                openai_base_url=openai_base_url,
                agy_bin=agy_bin
            )

        # Propiedades de compatibilidad hacia atrás
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.model_name = self.adapter.model_name
        self.use_agy = (self.adapter.name == "agy")
        self.agy_bin = agy_bin or cfg.get("agy_bin", "agy")

    def _get_scaffold(self, text: str) -> Dict[str, Any]:
        """
        Obtiene el Morfo-Semantic Scaffold invocando el módulo de segmentación.
        Soporta varias rutas de importación para garantizar interoperabilidad.
        """
        scaffold_fn = None
        for mod_name in ["src.segmentation.scaffold_builder", "src.segmentation.scaffold"]:
            try:
                mod = __import__(mod_name, fromlist=["build_sentence_scaffold", "ScaffoldBuilder"])
                if hasattr(mod, "build_sentence_scaffold"):
                    scaffold_fn = getattr(mod, "build_sentence_scaffold")
                    break
                elif hasattr(mod, "ScaffoldBuilder"):
                    builder = getattr(mod, "ScaffoldBuilder")(db_path=self.db_path)
                    if hasattr(builder, "build_sentence_scaffold"):
                        scaffold_fn = builder.build_sentence_scaffold
                        break
                    elif hasattr(builder, "build"):
                        scaffold_fn = builder.build
                        break
            except (ImportError, Exception):
                continue

        if scaffold_fn:
            res = scaffold_fn(text)
            if hasattr(res, "to_dict"):
                return res.to_dict()
            elif isinstance(res, dict):
                return res

        return self._build_basic_scaffold(text)

    def _build_basic_scaffold(self, text: str) -> Dict[str, Any]:
        """
        Fallback para generar un scaffold elemental consultando directamente QuechuaDB
        si la etapa de segmentación no está accesible en tiempo de import.
        """
        tokens_scaffold = []
        words = re.findall(r"[A-Za-zñÑáéíóúÁÉÍÓÚ'’\-]+|[.,!?;:]", text)

        db = None
        try:
            from src.storage.db import QuechuaDB
            db = QuechuaDB(self.db_path) if self.db_path else QuechuaDB()
        except Exception:
            pass

        for w in words:
            if not re.match(r"[A-Za-zñÑáéíóúÁÉÍÓÚ'’]", w):
                continue
            w_lower = w.lower()

            lemma_info = None
            senses = []
            if db:
                try:
                    lemma_info = db.get_lemma(w_lower)
                    if lemma_info and "senses" in lemma_info:
                        senses = lemma_info["senses"]
                except Exception:
                    pass

            tokens_scaffold.append({
                "surface": w,
                "normalized": w_lower,
                "stem": {
                    "headword": lemma_info.get("headword", w_lower) if lemma_info else w_lower,
                    "pos": lemma_info.get("pos", "s.") if lemma_info else "s.",
                    "senses": senses,
                    "examples": lemma_info.get("examples", []) if lemma_info else []
                },
                "affixes": []
            })

        return {
            "source_sentence": text,
            "tokens": tokens_scaffold
        }

    def _call_gemini_api(self, prompt: str) -> Dict[str, Any]:
        """Método de retrocompatibilidad que invoca GeminiApiAdapter."""
        from .adapters.gemini_api_adapter import GeminiApiAdapter
        adapter = GeminiApiAdapter(api_key=self.api_key, model_name=self.model_name)
        return adapter.generate(prompt)

    def _call_agy_cli(self, prompt: str, effort: str = "low", timeout: int = 180) -> Dict[str, Any]:
        """Método de retrocompatibilidad que invoca AgyAdapter."""
        from .adapters.agy_adapter import AgyAdapter
        adapter = AgyAdapter(agy_bin=self.agy_bin, effort=effort, timeout=timeout)
        return adapter.generate(prompt)

    def _intelligent_fallback_translate(self, scaffold: Dict[str, Any]) -> Dict[str, Any]:
        """Método de retrocompatibilidad que invoca FallbackAdapter."""
        return self.fallback_adapter.generate(prompt="", scaffold=scaffold)

    def translate(self, text: str, long_mode: bool = False, **kwargs: Any) -> Dict[str, Any]:
        """
        Ejecuta el pipeline completo de traducción:
        1. Construcción del scaffold morfo-semántico (compacto si long_mode o len > 120).
        2. Preparación del prompt estructurado con directivas lingüísticas.
        3. Inferencia generativa mediante el adaptador seleccionado (con degradación a Fallback).
        """
        text_clean = text.strip()
        is_long = long_mode or len(text_clean) > 120

        if is_long:
            try:
                from src.segmentation.scaffold import build_compact_scaffold
                scaffold = build_compact_scaffold(text_clean, db_path=self.db_path)
            except Exception:
                scaffold = self._get_scaffold(text_clean)
            prompt = build_translation_prompt(text_clean, scaffold, compact=True)
        else:
            scaffold = self._get_scaffold(text_clean)
            prompt = build_translation_prompt(text_clean, scaffold, compact=False)

        gen_kwargs = dict(kwargs)
        if "effort" not in gen_kwargs:
            gen_kwargs["effort"] = "low"

        # Intentar traducción con el adaptador configurado
        try:
            result = self.adapter.generate(
                prompt=prompt,
                system_instruction=SYSTEM_INSTRUCTION,
                scaffold=scaffold,
                **gen_kwargs
            )
        except Exception as e:
            # Si el adaptador generativo falla, degradar limpiamente al Fallback determinista
            result = self.fallback_adapter.generate(prompt=prompt, scaffold=scaffold)
            result["api_error"] = str(e)
            result["failed_backend"] = self.adapter.name

        # Enriquecer resultado con metadatos del pipeline
        result["source_sentence"] = text_clean
        result["scaffold"] = scaffold
        result["prompt"] = prompt
        result.setdefault("backend", self.adapter.name)
        result.setdefault("model_name", self.adapter.model_name)

        return result
