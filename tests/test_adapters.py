"""
Tests para la arquitectura de Puertos y Adaptadores de traducción.
"""

import os
import sys
import json
from unittest.mock import MagicMock, patch
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.translation.ports.model_port import TranslationModelPort
from src.translation.adapters.base import parse_llm_json_response, clean_json_text
from src.translation.adapters.fallback_adapter import FallbackAdapter
from src.translation.adapters.agy_adapter import AgyAdapter
from src.translation.adapters.gemini_api_adapter import GeminiApiAdapter
from src.translation.adapters.openai_adapter import OpenAIAdapter
from src.translation.adapters.ollama_adapter import OllamaAdapter
from src.translation.adapters.factory import ModelAdapterFactory
from src.translation.orchestrator import QuechuaTranslator


class TestPortsAndAdapters:

    def test_abstract_port_instantiation(self):
        """No se puede instanciar directamente TranslationModelPort sin implementar sus métodos."""
        with pytest.raises(TypeError):
            TranslationModelPort()

    def test_clean_json_text(self):
        """Verifica la extracción de bloques de código markdown JSON."""
        raw = "```json\n{\"traduccion_es\": \"Hola mundo\"}\n```"
        assert clean_json_text(raw) == '{"traduccion_es": "Hola mundo"}'

        raw_simple = "{\"traduccion_es\": \"Hola mundo\"}"
        assert clean_json_text(raw_simple) == '{"traduccion_es": "Hola mundo"}'

    def test_fallback_adapter(self):
        """FallbackAdapter opera deterministamente sin red ni dependencias externas."""
        adapter = FallbackAdapter()
        assert adapter.name == "fallback"
        assert adapter.is_available() is True

        dummy_scaffold = {
            "source_sentence": "Wasikunamanmi purishanchis",
            "tokens": [
                {
                    "surface": "Wasikunamanmi",
                    "stem": {"headword": "wasi", "pos": "s.", "senses": [{"definition": "Casa, morada"}]},
                    "affixes": [
                        {"morpheme": "-kuna", "category": "flexivo", "subcategory": "numero"},
                        {"morpheme": "-man", "category": "flexivo", "subcategory": "caso"},
                        {"morpheme": "-mi", "category": "validador", "subcategory": "evidencial", "role": "testimonial"}
                    ]
                },
                {
                    "surface": "purishanchis",
                    "stem": {"headword": "puriy", "pos": "v.", "senses": [{"definition": "Caminar, andar"}]},
                    "affixes": [
                        {"morpheme": "-sha", "category": "flexivo", "subcategory": "aspecto"},
                        {"morpheme": "-nchis", "category": "flexivo", "subcategory": "persona", "role": "1pl_incl"}
                    ]
                }
            ]
        }

        res = adapter.generate(prompt="", scaffold=dummy_scaffold)
        assert res["backend"] == "fallback"
        assert "casas" in res["traduccion_es"].lower() or "wasi" in res["traduccion_es"].lower()
        assert "testimonial" in res["evidencialidad"].lower() or "certeza" in res["evidencialidad"].lower()
        assert "incluyente" in str(res["clusividad"]).lower()

    def test_gemini_api_adapter(self):
        """GeminiApiAdapter valida la API key y procesa respuestas REST simuladas."""
        adapter_no_key = GeminiApiAdapter(api_key="")
        assert adapter_no_key.is_available() is False
        with pytest.raises(ValueError):
            adapter_no_key.generate("prompt")

        adapter_with_key = GeminiApiAdapter(api_key="test-key", model_name="gemini-2.5-flash")
        assert adapter_with_key.is_available() is True
        assert adapter_with_key.name == "gemini_api"

        mock_payload = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps({
                                    "traduccion_es": "Hacia las casas caminamos.",
                                    "traduccion_literal_glosada": "casa-PL-HACIA caminar-PROG-1PL",
                                    "evidencialidad": "Testimonial directo",
                                    "clusividad": "Incluyente",
                                    "justificacion_semantica": "wasi = casa"
                                })
                            }
                        ]
                    }
                }
            ]
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(mock_payload).encode("utf-8")
            mock_urlopen.return_value.__enter__.return_value = mock_resp

            res = adapter_with_key.generate("dummy prompt")
            assert res["traduccion_es"] == "Hacia las casas caminamos."
            assert res["backend"] == "gemini_api"
            assert res["model_name"] == "gemini-2.5-flash"

    def test_openai_adapter(self):
        """OpenAIAdapter valida la clave y procesa respuestas compatibles con chat completions."""
        adapter = OpenAIAdapter(api_key="sk-test", model_name="gpt-4o-mini")
        assert adapter.is_available() is True
        assert adapter.name == "openai"

        mock_payload = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps({
                            "traduccion_es": "Vamos a las casas.",
                            "traduccion_literal_glosada": "casa-PL-MAN...",
                            "evidencialidad": "Certeza",
                            "clusividad": "Incluyente",
                            "justificacion_semantica": "Traducción contextual"
                        })
                    }
                }
            ]
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(mock_payload).encode("utf-8")
            mock_urlopen.return_value.__enter__.return_value = mock_resp

            res = adapter.generate("dummy prompt")
            assert res["traduccion_es"] == "Vamos a las casas."
            assert res["backend"] == "openai"

    def test_ollama_adapter(self):
        """OllamaAdapter verifica el endpoint y procesa respuestas JSON."""
        adapter = OllamaAdapter(host="http://localhost:11434", model_name="llama3.2:3b-instruct-q4_K_M")
        assert adapter.name == "ollama"

        mock_payload = {
            "message": {
                "content": json.dumps({
                    "traduccion_es": "Caminamos hacia las casas juntos.",
                    "traduccion_literal_glosada": "casa-PL-MAN...",
                    "evidencialidad": "Testimonial",
                    "clusividad": "Incluyente",
                    "justificacion_semantica": "Uso de -nchis"
                })
            }
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(mock_payload).encode("utf-8")
            mock_urlopen.return_value.__enter__.return_value = mock_resp

            res = adapter.generate("dummy prompt")
            assert res["traduccion_es"] == "Caminamos hacia las casas juntos."
            assert res["backend"] == "ollama"
            assert res["model_name"] == "llama3.2:3b-instruct-q4_K_M"

    def test_agy_adapter(self):
        """AgyAdapter invoca el CLI con los argumentos esperados."""
        adapter = AgyAdapter(agy_bin="agy", effort="low")
        assert adapter.name == "agy"

        with patch("subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = json.dumps({
                "traduccion_es": "Traducción vía agy",
                "evidencialidad": "Directo",
                "clusividad": None,
                "justificacion_semantica": "Ok"
            })
            mock_run.return_value = mock_proc

            res = adapter.generate("test prompt")
            assert res["traduccion_es"] == "Traducción vía agy"
            assert res["backend"] == "agy"

    def test_factory_creation(self):
        """ModelAdapterFactory crea instancias de adaptadores según proveedor explícito."""
        assert isinstance(ModelAdapterFactory.create_adapter(provider="fallback"), FallbackAdapter)
        assert isinstance(ModelAdapterFactory.create_adapter(provider="ollama"), OllamaAdapter)
        assert isinstance(ModelAdapterFactory.create_adapter(provider="gemini", api_key="k"), GeminiApiAdapter)
        assert isinstance(ModelAdapterFactory.create_adapter(provider="openai", api_key="k"), OpenAIAdapter)
        assert isinstance(ModelAdapterFactory.create_adapter(provider="agy"), AgyAdapter)

    def test_dependency_injection_in_translator(self):
        """QuechuaTranslator acepta un adaptador inyectado directamente."""
        custom_adapter = FallbackAdapter()
        translator = QuechuaTranslator(adapter=custom_adapter)
        assert translator.adapter is custom_adapter

        res = translator.translate("Wasikunamanmi purishanchis")
        assert res["backend"] == "fallback"
        assert "traduccion_es" in res

    def test_translator_graceful_degradation_on_adapter_failure(self):
        """Si el adaptador falla por excepción de red, QuechuaTranslator degrada al Fallback."""
        failing_adapter = MagicMock(spec=TranslationModelPort)
        failing_adapter.name = "mock_failing"
        failing_adapter.model_name = "failing-model"
        failing_adapter.generate.side_effect = RuntimeError("Conexión perdida")

        translator = QuechuaTranslator(adapter=failing_adapter)
        res = translator.translate("Wasikunamanmi purishanchis")

        assert res["backend"] == "fallback"
        assert "Conexión perdida" in res["api_error"]
        assert res["failed_backend"] == "mock_failing"
        assert res["traduccion_es"] != ""
