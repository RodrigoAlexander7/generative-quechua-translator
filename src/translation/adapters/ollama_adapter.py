"""
Adaptador para modelos locales servidos mediante Ollama (http://localhost:11434).
Permite traducción generativa 100% offline y local sin enviar datos a la nube.
"""

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from ..ports.model_port import TranslationModelPort
from .base import parse_llm_json_response


class OllamaAdapter(TranslationModelPort):
    """
    Adaptador para Ollama (Llama 3, Qwen, Mistral, Gemma, etc.).
    Utiliza el endpoint REST nativo de Ollama con salida forzada en JSON ('format': 'json').
    """

    def __init__(
        self,
        host: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: int = 180
    ):
        raw_host = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self.host = raw_host.rstrip("/")
        self.timeout = timeout
        self._model_name = (model_name or os.environ.get("OLLAMA_MODEL", "")).strip()

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        if self._model_name:
            return self._model_name
        # Si no se especificó modelo, intentar autodetectar el primer modelo disponible
        models = self.get_available_models()
        if models:
            self._model_name = models[0]
            return self._model_name
        return "llama3.2"

    def get_available_models(self) -> List[str]:
        """Consulta los modelos instalados en la instancia local de Ollama."""
        endpoint = f"{self.host}/api/tags"
        req = urllib.request.Request(endpoint, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
                return models
        except Exception:
            return []

    def is_available(self) -> bool:
        """Verifica conectividad con el daemon de Ollama."""
        endpoint = f"{self.host}/api/tags"
        req = urllib.request.Request(endpoint, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=2) as resp:
                return resp.status == 200
        except Exception:
            return False

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        scaffold: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        target_model = kwargs.get("model") or self.model_name
        endpoint = f"{self.host}/api/chat"

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        options = {
            "temperature": kwargs.get("temperature", 0.1),
            "num_predict": kwargs.get("num_predict", 1024)
        }
        if "num_thread" in kwargs:
            options["num_thread"] = kwargs["num_thread"]
        if "options" in kwargs and isinstance(kwargs["options"], dict):
            options.update(kwargs["options"])

        format_val = kwargs.get("format", "json")
        payload = {
            "model": target_model,
            "messages": messages,
            "stream": False,
            "options": options
        }
        if format_val:
            payload["format"] = format_val

        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                resp_bytes = resp.read()
                resp_json = json.loads(resp_bytes.decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Error HTTP {e.code} en Ollama: {err_body}") from e
        except Exception as e:
            raise RuntimeError(f"No se pudo conectar con Ollama en {self.host}: {e}") from e

        message_obj = resp_json.get("message", {})
        raw_text = message_obj.get("content", "")
        if not raw_text:
            raise ValueError(f"Ollama devolvió una respuesta vacía: {resp_json}")

        raw_mode = kwargs.get("raw_mode", False)
        if raw_mode or format_val is None:
            result = {
                "traduccion_es": raw_text.strip(),
                "traduccion_literal_glosada": "",
                "evidencialidad": "Modo directo",
                "clusividad": None,
                "justificacion_semantica": "",
                "backend": "ollama",
                "model_name": target_model
            }
        else:
            result = parse_llm_json_response(raw_text, default_backend="ollama", model_name=target_model)

        # Enriquecer con métricas empíricas de hardware de Ollama
        eval_count = resp_json.get("eval_count", 0)
        eval_dur_sec = round(resp_json.get("eval_duration", 0) / 1e9, 4)
        result["eval_count"] = eval_count
        result["eval_duration_sec"] = eval_dur_sec
        result["prompt_eval_count"] = resp_json.get("prompt_eval_count", 0)
        result["prompt_eval_duration_sec"] = round(resp_json.get("prompt_eval_duration", 0) / 1e9, 4)
        result["total_duration_sec"] = round(resp_json.get("total_duration", 0) / 1e9, 4)
        if eval_dur_sec > 0:
            result["tokens_per_second"] = round(eval_count / eval_dur_sec, 2)
        else:
            result["tokens_per_second"] = 0.0

        return result
