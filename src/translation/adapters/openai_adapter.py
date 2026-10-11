"""
Adaptador para APIs compatibles con el protocolo OpenAI.
Permite usar OpenAI (gpt-4o, gpt-4o-mini) u otros proveedores compatibles (Groq, DeepSeek, vLLM, LocalAI).
"""

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from ..ports.model_port import TranslationModelPort
from .base import parse_llm_json_response


class OpenAIAdapter(TranslationModelPort):
    """
    Adaptador compatible con la especificación OpenAI Chat Completions.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 45
    ):
        self.api_key = (api_key or os.environ.get("OPENAI_API_KEY", "")).strip()
        self._model_name = (model_name or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")).strip()
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.timeout = timeout

    @property
    def name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model_name

    def is_available(self) -> bool:
        return bool(self.api_key)

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        scaffold: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY no está configurada para OpenAIAdapter.")

        endpoint = f"{self.base_url}/chat/completions"

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._model_name,
            "messages": messages,
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }

        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=req_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                resp_bytes = response.read()
                resp_json = json.loads(resp_bytes.decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Error HTTP {e.code} en OpenAI API: {err_body}") from e
        except Exception as e:
            raise RuntimeError(f"Error de conexión con OpenAI API: {e}") from e

        choices = resp_json.get("choices", [])
        if not choices:
            raise ValueError(f"OpenAI API no devolvió opciones: {resp_json}")

        raw_text = choices[0].get("message", {}).get("content", "")
        return parse_llm_json_response(raw_text, default_backend="openai", model_name=self.model_name)
