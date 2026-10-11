"""
Adaptador Fallback determinista y basado en reglas / glosas morfológicas.
Opera 100% offline sin necesidad de ningún LLM ni conexión de red.
"""

import re
from typing import Any, Dict, Optional

from ..ports.model_port import TranslationModelPort


class FallbackAdapter(TranslationModelPort):
    """
    Adaptador determinista basado en el andamiaje morfo-semántico (Scaffold)
    y reglas gramaticales explícitas de sufijos y roles temáticos.
    """

    @property
    def name(self) -> str:
        return "fallback"

    @property
    def model_name(self) -> str:
        return "rule-based-scaffold"

    def is_available(self) -> bool:
        return True

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        scaffold: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        scaffold_dict = scaffold or {}
        tokens = scaffold_dict.get("tokens", [])
        if not tokens:
            return {
                "traduccion_es": scaffold_dict.get("source_sentence", ""),
                "traduccion_literal_glosada": scaffold_dict.get("source_sentence", ""),
                "evidencialidad": "No especificado",
                "clusividad": None,
                "justificacion_semantica": "Sin tokens analizados",
                "backend": "fallback",
                "model_name": self.model_name
            }

        evidencial = "Neutro / No marcado"
        clusividad = None
        modal_prefix = ""

        literal_tokens = []
        token_translations = []
        justificaciones = []

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

            primary_def = headword
            if senses:
                first_sense = senses[0]
                def_text = first_sense.get("definition", "") or first_sense.get("definition_es", "")
                if def_text:
                    clean_def = re.sub(r"^[A-Z][a-z]+\.\s*(?:\([^)]+\)\s*)?", "", def_text)
                    clean_def = clean_def.split(".")[0].split(";")[0].split("||")[0].strip()
                    if clean_def:
                        primary_def = clean_def.split(",")[0].strip()

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

                if m in ("mi", "m"):
                    evidencial = "Certeza absoluta / testimonial directo (el hablante lo atestigua de primera mano)"
                    affix_labels.append("EVID_DIR")
                elif m in ("si", "s"):
                    evidencial = "Reportativo indirecto (información transmitida por terceros: 'dicen que / según cuentan')"
                    modal_prefix = "Dicen que "
                    affix_labels.append("REPORT")
                elif m in ("chá", "cha"):
                    if "EVIDENCIAL" in cat or "EVIDENCIAL" in subcat or "CONJETURAL" in role.upper():
                        evidencial = "Conjetural epistémico (incertidumbre o probabilidad: 'tal vez / quizás')"
                        modal_prefix = "Tal vez "
                        affix_labels.append("CONJ")

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

            if affix_labels:
                tok_gloss = f"{primary_def}-{'-'.join(affix_labels)}"
            else:
                tok_gloss = primary_def
            literal_tokens.append(tok_gloss)

            phrase = primary_def
            if has_plural:
                if not phrase.endswith("s"):
                    phrase = f"{phrase}s"
            if has_case:
                if has_case == "ta":
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

        assembled_es = " ".join(token_translations).capitalize() + "."
        if modal_prefix:
            assembled_es = f"{modal_prefix}{assembled_es[0].lower() + assembled_es[1:]}"

        return {
            "traduccion_es": assembled_es,
            "traduccion_literal_glosada": " ".join(literal_tokens),
            "evidencialidad": evidencial,
            "clusividad": clusividad,
            "justificacion_semantica": "; ".join(justificaciones),
            "backend": "fallback",
            "model_name": self.model_name
        }
