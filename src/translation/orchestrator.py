"""
Orquestador de traducción generativa Quechua -> Español.
Clase QuechuaTranslator:
- Invoca la segmentación morfo-semántica (Scaffold) de la Etapa 1.
- Genera el prompt estructurado con directivas lingüísticas estrictas.
- Ejecuta la llamada al modelo LLM (Gemini) si GEMINI_API_KEY está configurada.
- Fallback inteligente determinista basado en glosas y reglas gramaticales si no hay API key.
"""

import os
import json
import re
import urllib.request
import urllib.error
from typing import Any, Dict, Optional, List, Union

import subprocess
import shutil

from .prompt_templates import build_translation_prompt, SYSTEM_INSTRUCTION


def load_config() -> Dict[str, Any]:
    """Carga configuración desde config/settings.json si existe."""
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cfg_path = os.path.join(repo_root, "config", "settings.json")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


class QuechuaTranslator:
    """
    Traductor Generativo y Analizador Morfo-Semántico para Quechua.
    Soporta backends de inferencia generativa:
    1. agy (Antigravity CLI vía -p con autenticación nativa)
    2. API directa de Gemini (vía GEMINI_API_KEY)
    3. Fallback inteligente determinista basado en glosas del scaffold.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        db_path: Optional[str] = None,
        use_agy: Optional[bool] = None
    ):
        cfg = load_config()
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "").strip()
        self.model_name = model_name or os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        self.db_path = db_path

        # Determinar si usar AGY CLI:
        # Prioridad: argumento explícito > env vars (QTR_USE_AGY, QUECHUA_USE_AGY, USE_AGY) > config/settings.json > autodetección
        env_val = os.environ.get("QTR_USE_AGY") or os.environ.get("QUECHUA_USE_AGY") or os.environ.get("USE_AGY")
        if use_agy is not None:
            self.use_agy = bool(use_agy)
        elif env_val is not None:
            self.use_agy = env_val.strip().lower() in ("1", "true", "yes", "on")
        elif "use_agy" in cfg:
            self.use_agy = bool(cfg["use_agy"])
        else:
            self.use_agy = bool(shutil.which("agy"))

        self.agy_bin = cfg.get("agy_bin", "agy")

    def _get_scaffold(self, text: str) -> Dict[str, Any]:
        """
        Obtiene el Morfo-Semantic Scaffold invocando el módulo de segmentación.
        Soporta varias rutas de importación para garantizar interoperabilidad.
        """
        # 1. Intentar importar build_sentence_scaffold desde scaffold_builder o scaffold
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

        # 2. Si no está disponible el módulo de segmentación completo aún, construir un scaffold básico
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
        """
        Llama a la API REST de Google Gemini usando urllib estándar.
        """
        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent"
            f"?key={self.api_key}"
        )

        payload = {
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

        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            resp_bytes = response.read()
            resp_json = json.loads(resp_bytes.decode("utf-8"))

        # Extraer texto generado
        candidates = resp_json.get("candidates", [])
        if not candidates:
            raise ValueError("No candidates returned by Gemini API")

        raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        # Limpiar bloques de código markdown si los hay
        cleaned = raw_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[len("```json"):].strip()
        elif cleaned.startswith("```"):
            cleaned = cleaned[len("```"):].strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

        return json.loads(cleaned)

    def _intelligent_fallback_translate(self, scaffold: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fallback inteligente que ensambla una traducción precisa a partir de las glosas
        directas, raíces y sufijos del scaffold.
        """
        tokens = scaffold.get("tokens", [])
        if not tokens:
            return {
                "traduccion_es": scaffold.get("source_sentence", ""),
                "traduccion_literal_glosada": scaffold.get("source_sentence", ""),
                "evidencialidad": "No especificado",
                "clusividad": None,
                "justificacion_semantica": "Sin tokens analizados"
            }

        # 1. Análisis de Evidencialidad y Clusividad global
        evidencial = "Neutro / No marcado"
        clusividad = None
        modal_prefix = ""

        # Mapeos de sufijos y glosas
        literal_tokens = []
        token_translations = []
        justificaciones = []

        # Roles y funciones comunes de sufijos
        suffix_case_map = {
            "ta": "a / (objeto directo)",
            "man": "hacia / a",
            "manta": "desde / de",
            "pi": "en",
            "wan": "con",
            "paq": "para",
            "kama": "hasta",
            "rayku": "por / a causa de",
            "pura": "entre",
            "hina": "como"
        }

        for tok in tokens:
            surface = tok.get("surface", "")
            stem = tok.get("stem", {})
            headword = stem.get("headword", surface)
            pos = stem.get("pos", "")
            senses = stem.get("senses", [])
            affixes = tok.get("affixes", [])

            # Obtener definición principal
            primary_def = headword
            if senses:
                first_sense = senses[0]
                def_text = first_sense.get("definition", "") or first_sense.get("definition_es", "")
                if def_text:
                    # Limpiar notas de diccionario (ej: "Zool. (Lama pacos) Alpaca, paco...")
                    clean_def = re.sub(r"^[A-Z][a-z]+\.\s*(?:\([^)]+\)\s*)?", "", def_text)
                    clean_def = clean_def.split(".")[0].split(";")[0].split("||")[0].strip()
                    if clean_def:
                        # Extraer primera palabra o término compuesto
                        primary_def = clean_def.split(",")[0].strip()

            # Glosa interlineal morfema por morfema
            affix_labels = []
            has_plural = False
            has_case = None
            has_prog = False
            subject_person = None

            for aff in affixes:
                m = aff.get("morpheme", "").lstrip("-").lower()
                cat = aff.get("category", "").upper()
                subcat = aff.get("subcategory", "").upper()
                role = aff.get("role", "")

                # Detectar evidenciales
                if m in ("mi", "m"):
                    evidencial = "Certeza absoluta / testimonial directo (el hablante lo atestigua de primera mano)"
                    affix_labels.append("EVID_DIR")
                elif m in ("si", "s"):
                    evidencial = "Reportativo indirecto (información transmitida por terceros: 'dicen que / según cuentan')"
                    modal_prefix = "Dicen que "
                    affix_labels.append("REPORT")
                elif m == "chá" or m == "cha":
                    if "EVIDENCIAL" in cat or "EVIDENCIAL" in subcat or "CONJETURAL" in role.upper():
                        evidencial = "Conjetural epistémico (incertidumbre o probabilidad: 'tal vez / quizás')"
                        modal_prefix = "Tal vez "
                        affix_labels.append("CONJ")

                # Detectar clusividad
                if m == "nchis":
                    clusividad = "1ra persona plural incluyente (nosotros, incluyéndote a ti)"
                    affix_labels.append("1PL_INCL")
                    subject_person = "nosotros (incluyente)"
                elif m == "yku":
                    clusividad = "1ra persona plural excluyente (nosotros, pero no tú)"
                    affix_labels.append("1PL_EXCL")
                    subject_person = "nosotros (excluyente)"
                elif m == "kuna":
                    has_plural = True
                    affix_labels.append("PL")
                elif m in suffix_case_map:
                    has_case = m
                    affix_labels.append(m.upper())
                elif m in ("sha", "chka"):
                    has_prog = True
                    affix_labels.append("PROG")
                elif m == "nku":
                    affix_labels.append("3PL")
                    subject_person = "ellos/ellas"
                elif m == "nki":
                    affix_labels.append("2SG")
                    subject_person = "tú"
                elif m == "ni":
                    affix_labels.append("1SG")
                    subject_person = "yo"
                elif m == "n":
                    affix_labels.append("3SG")
                    subject_person = "él/ella"
                else:
                    affix_labels.append(m.upper())

            # Construir glosa para este token
            if affix_labels:
                tok_gloss = f"{primary_def}-{'-'.join(affix_labels)}"
            else:
                tok_gloss = primary_def
            literal_tokens.append(tok_gloss)

            # Construir frase en español para este token
            phrase = primary_def
            if has_plural:
                if not phrase.endswith("s"):
                    phrase = f"{phrase}s"
            if has_case:
                case_prep = suffix_case_map.get(has_case, "")
                if has_case == "ta":
                    # Acusativo con objeto
                    phrase = f"a {phrase}" if pos.startswith("s") else phrase
                elif has_case == "pi":
                    phrase = f"en {phrase}"
                elif has_case == "man":
                    phrase = f"hacia {phrase}"
                elif has_case == "manta":
                    phrase = f"desde {phrase}"
                elif has_case == "wan":
                    phrase = f"con {phrase}"
                elif has_case == "paq":
                    phrase = f"para {phrase}"

            if has_prog:
                if subject_person:
                    phrase = f"están {phrase}" if "ellos" in subject_person else f"está {phrase}"

            token_translations.append(phrase)
            justificaciones.append(
                f"Raíz '{headword}' ({pos}): '{primary_def}'"
                + (f" con sufijos [{', '.join(affix_labels)}]" if affix_labels else "")
            )

        # Ensamblar traducción final en español
        assembled_es = " ".join(token_translations).capitalize() + "."
        if modal_prefix:
            assembled_es = f"{modal_prefix}{assembled_es[0].lower() + assembled_es[1:]}"

        return {
            "traduccion_es": assembled_es,
            "traduccion_literal_glosada": " ".join(literal_tokens),
            "evidencialidad": evidencial,
            "clusividad": clusividad,
            "justificacion_semantica": "; ".join(justificaciones)
        }

    def _call_agy_cli(self, prompt: str, effort: str = "low", timeout: int = 180) -> Dict[str, Any]:
        """
        Invoca el CLI 'agy' (Antigravity) de forma no interactiva con -p.
        Aprovecha la autenticación nativa y aplica flags de alta velocidad:
        --effort low y --disable-slash-commands.
        """
        agy_cmd = shutil.which(self.agy_bin) or self.agy_bin

        # Ejecutar agy en modo print no interactivo con esfuerzo bajo y sin comandos/skills
        cmd = [
            agy_cmd,
            "--dangerously-skip-permissions",
            "--disable-slash-commands",
            "--effort", effort,
            "-p", prompt
        ]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if proc.returncode != 0:
            err_msg = proc.stderr.strip() or f"Código de salida: {proc.returncode}"
            raise RuntimeError(f"Fallo al invocar agy: {err_msg}")

        raw_output = proc.stdout.strip()

        # Extraer JSON de la respuesta (manejar bloques markdown ```json ... ```)
        cleaned = raw_output
        if "```json" in cleaned:
            cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()

        try:
            parsed = json.loads(cleaned)
            parsed["backend"] = "agy"
            return parsed
        except json.JSONDecodeError:
            # Fallback si agy devolvió texto libre
            return {
                "traduccion_es": raw_output,
                "traduccion_literal_glosada": "",
                "evidencialidad": "Procesado vía agy",
                "clusividad": None,
                "justificacion_semantica": "Traducción directa de Gemini vía agy",
                "backend": "agy"
            }

    def translate(self, text: str, long_mode: bool = False) -> Dict[str, Any]:
        """
        Ejecuta el flujo completo de traducción:
        1. Construcción del scaffold morfo-semántico (compacto si long_mode o len > 120).
        2. Preparación del prompt estructurado.
        3. Inferencia generativa (vía agy o Gemini API) o Fallback inteligente.
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

        result = None
        # 1. Intentar con agy CLI si está habilitado
        if self.use_agy:
            try:
                result = self._call_agy_cli(prompt, effort="low", timeout=180)
            except Exception as e:
                # Si agy falla, degradar a API de Gemini o fallback
                if self.api_key:
                    try:
                        result = self._call_gemini_api(prompt)
                        result["backend"] = "gemini_api"
                    except Exception as api_err:
                        result = self._intelligent_fallback_translate(scaffold)
                        result["backend"] = "fallback"
                        result["api_error"] = f"agy error: {e}; api error: {api_err}"
                else:
                    result = self._intelligent_fallback_translate(scaffold)
                    result["backend"] = "fallback"
                    result["api_error"] = f"agy error: {e}"
        # 2. Intentar con Gemini API directa si hay key
        elif self.api_key:
            try:
                result = self._call_gemini_api(prompt)
                result["backend"] = "gemini_api"
            except Exception as e:
                result = self._intelligent_fallback_translate(scaffold)
                result["backend"] = "fallback"
                result["api_error"] = str(e)
        # 3. Fallback determinista
        else:
            result = self._intelligent_fallback_translate(scaffold)
            result["backend"] = "fallback"

        # Añadir metadatos enriquecidos
        result["source_sentence"] = text_clean
        result["scaffold"] = scaffold
        result["prompt"] = prompt

        return result

