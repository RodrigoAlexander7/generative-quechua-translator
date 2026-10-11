"""
Adaptador para la API REST directa de Google Gemini.
Utiliza urllib estándar para evitar dependencias externas pesadas.
"""

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from ..ports.model_port import TranslationModelPort
from .base import parse_llm_json_response


class GeminiApiAdapter(TranslationModelPort):
    """
    Adaptador directo a Google Gemini vía REST API con API Key.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: int = 45
    ):
        self.api_key = (api_key or os.environ.get("GEMINI_API_KEY", "")).strip()
        self._model_name = (model_name or os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")).strip()
        self.timeout = timeout

    @property
    def name(self) -> str:
        return "gemini_api"

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
            raise ValueError("GEMINI_API_KEY no está configurada para GeminiApiAdapter.")

        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self._model_name}:generateContent"
            f"?key={self.api_key}"
        )

        payload: Dict[str, Any] = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json"
            }
        }

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                resp_bytes = response.read()
                resp_json = json.loads(resp_bytes.decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Error HTTP {e.code} en Gemini API: {err_body}") from e
        except Exception as e:
            raise RuntimeError(f"Error de conexión con Gemini API: {e}") from e

        candidates = resp_json.get("candidates", [])
        if not candidates:
            raise ValueError(f"Gemini API no devolvió candidatos: {resp_json}")

        content_parts = candidates[0].get("content", {}).get("parts", [])
        if not content_parts:
            raise ValueError("Respuesta vacía de Gemini API.")

        raw_text = content_parts[0].get("text", "")
        return parse_llm_json_response(raw_text, default_backend="gemini_api", model_name=self.model_name)
