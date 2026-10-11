"""
Puerto (interfaz) para motores de inferencia generativa y LLMs.
Implementa el patrón Puertos y Adaptadores (Arquitectura Hexagonal).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class TranslationModelPort(ABC):
    """
    Puerto primario de salida para la generación de traducción y análisis lingüístico.
    Desacopla el dominio de traducción de los proveedores concretos de IA
    (CLI agy, Gemini REST API, OpenAI API, Ollama local, Fallback determinista).
    """

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        scaffold: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Ejecuta la inferencia generativa con el prompt y andamiaje estructurado.

        Debe retornar un diccionario con la estructura canónica:
        {
            "traduccion_es": str,
            "traduccion_literal_glosada": str,
            "evidencialidad": str,
            "clusividad": Optional[str],
            "justificacion_semantica": str,
            "backend": str,
            "model_name": str
        }
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Verifica si el adaptador cuenta con los recursos, binarios,
        claves de API o servicios necesarios para operar.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre identificador único del backend (ej: 'agy', 'ollama', 'gemini_api', 'openai', 'fallback')."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Nombre del modelo específico en uso (ej: 'gemini-2.5-flash', 'llama3.2', etc.)."""
        pass
