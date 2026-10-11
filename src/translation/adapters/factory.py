"""
Fábrica de Adaptadores para selección dinámica de modelos.
Implementa el patrón Factory para instanciar adaptadores según configuración,
variables de entorno o detección automática de capacidades del sistema.
"""

import json
import os
import shutil
from typing import Any, Dict, Optional

from ..ports.model_port import TranslationModelPort
from .agy_adapter import AgyAdapter
from .fallback_adapter import FallbackAdapter
from .gemini_api_adapter import GeminiApiAdapter
from .ollama_adapter import OllamaAdapter
from .openai_adapter import OpenAIAdapter


def load_settings() -> Dict[str, Any]:
    """Carga configuración desde config/settings.json."""
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    cfg_path = os.path.join(repo_root, "config", "settings.json")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


class ModelAdapterFactory:
    """
    Factoría para crear y resolver instancias de TranslationModelPort.
    """

    @classmethod
    def create_adapter(
        cls,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        ollama_host: Optional[str] = None,
        openai_base_url: Optional[str] = None,
        agy_bin: Optional[str] = None,
        effort: str = "low",
        timeout: Optional[int] = None
    ) -> TranslationModelPort:
        """
        Crea el adaptador apropiado según el proveedor especificado o autodetección.
        Proveedores soportados: 'agy', 'gemini'/'gemini_api', 'openai', 'ollama', 'fallback', 'auto'.
        """
        cfg = load_settings()
        gemini_cfg = cfg.get("gemini", {})
        openai_cfg = cfg.get("openai", {})
        ollama_cfg = cfg.get("ollama", {})

        # Determinar proveedor objetivo
        target_provider = (
            provider
            or os.environ.get("QTR_PROVIDER")
            or os.environ.get("QUECHUA_TRANSLATION_PROVIDER")
            or cfg.get("provider")
            or "auto"
        ).strip().lower()

        # Si el proveedor es explícito
        if target_provider in ("agy",):
            bin_path = agy_bin or cfg.get("agy_bin", "agy")
            return AgyAdapter(
                agy_bin=bin_path,
                effort=effort,
                timeout=timeout or 180,
                model_name=model_name or "gemini-via-agy"
            )

        if target_provider in ("gemini", "gemini_api"):
            key = api_key or os.environ.get("GEMINI_API_KEY", "")
            m_name = model_name or gemini_cfg.get("model") or os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
            return GeminiApiAdapter(
                api_key=key,
                model_name=m_name,
                timeout=timeout or 45
            )

        if target_provider in ("openai", "openai_compatible"):
            key = api_key or os.environ.get("OPENAI_API_KEY", "")
            m_name = model_name or openai_cfg.get("model") or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
            base = openai_base_url or openai_cfg.get("base_url") or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
            return OpenAIAdapter(
                api_key=key,
                model_name=m_name,
                base_url=base,
                timeout=timeout or 45
            )

        if target_provider in ("ollama", "local"):
            host = ollama_host or ollama_cfg.get("host") or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
            m_name = model_name or ollama_cfg.get("model") or os.environ.get("OLLAMA_MODEL", "")
            return OllamaAdapter(
                host=host,
                model_name=m_name,
                timeout=timeout or 120
            )

        if target_provider in ("fallback", "rules", "rule_based"):
            return FallbackAdapter()

        # Modo 'auto': Resolución jerárquica inteligente
        # 1. Si agy está disponible y habilitado
        use_agy_env = os.environ.get("QTR_USE_AGY") or os.environ.get("USE_AGY")
        agy_allowed = True
        if use_agy_env is not None:
            agy_allowed = use_agy_env.lower() in ("1", "true", "yes", "on")
        elif "use_agy" in cfg:
            agy_allowed = bool(cfg["use_agy"])

        bin_path = agy_bin or cfg.get("agy_bin", "agy")
        agy_adapter = AgyAdapter(agy_bin=bin_path, effort=effort, timeout=timeout or 180)
        if agy_allowed and agy_adapter.is_available():
            return agy_adapter

        # 2. Si hay GEMINI_API_KEY
        gemini_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        if gemini_key:
            return GeminiApiAdapter(
                api_key=gemini_key,
                model_name=model_name or gemini_cfg.get("model", "gemini-2.5-flash"),
                timeout=timeout or 45
            )

        # 3. Si hay OPENAI_API_KEY
        openai_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if openai_key:
            return OpenAIAdapter(
                api_key=openai_key,
                model_name=model_name or openai_cfg.get("model", "gpt-4o-mini"),
                base_url=openai_base_url or openai_cfg.get("base_url", "https://api.openai.com/v1"),
                timeout=timeout or 45
            )

        # 4. Si Ollama está ejecutándose localmente
        ollama_inst = OllamaAdapter(
            host=ollama_host or ollama_cfg.get("host", "http://localhost:11434"),
            model_name=model_name or ollama_cfg.get("model", "")
        )
        if ollama_inst.is_available():
            return ollama_inst

        # 5. Fallback determinista
        return FallbackAdapter()
