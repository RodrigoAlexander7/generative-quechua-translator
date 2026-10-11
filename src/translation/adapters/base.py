"""
Utilidades compartidas para los adaptadores de inferencia generativa.
"""

import json
import re
from typing import Any, Dict


def clean_json_text(text: str) -> str:
    """Extrae y limpia bloques de código JSON o markdown devueltos por LLMs."""
    cleaned = text.strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in cleaned:
        cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()
    return cleaned


def parse_llm_json_response(raw_text: str, default_backend: str, model_name: str) -> Dict[str, Any]:
    """
    Parsea una respuesta textual de LLM asegurando que contenga los campos requeridos
    del esquema de traducción quechua.
    """
    cleaned = clean_json_text(raw_text)
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            # Asegurar claves por defecto si faltan
            data.setdefault("traduccion_es", "")
            data.setdefault("traduccion_literal_glosada", "")
            data.setdefault("evidencialidad", "No determinado")
            data.setdefault("clusividad", None)
            data.setdefault("justificacion_semantica", "")
            data["backend"] = default_backend
            data["model_name"] = model_name
            return data
    except Exception:
        pass

    # Fallback si el modelo respondió texto plano en vez de JSON
    return {
        "traduccion_es": raw_text.strip(),
        "traduccion_literal_glosada": "",
        "evidencialidad": "Texto plano sin estructurar",
        "clusividad": None,
        "justificacion_semantica": "Respuesta no parseable como JSON",
        "backend": default_backend,
        "model_name": model_name
    }
