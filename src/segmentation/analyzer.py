"""
Analizador morfosintáctico con salida estructurada (JSON) para consumo de plataforma.

Dado un párrafo o una palabra en quechua, produce un objeto estructurado donde
cada palabra trae su análisis morfosintáctico desglosado: raíz/lema, categoría
gramatical, acepciones, cadena de sufijos (con ranura morfotáctica, categoría,
función y glosa corta tipo Leipzig) y marcadores de evidencialidad/clusividad.

Esta capa NO modifica el segmentador (peeler) ni el scaffold existentes: los
envuelve y reordena su salida en un contrato estable y predecible para que una
plataforma externa pueda, al seleccionar una palabra, desplegar su morfosintaxis.
"""

import re
from typing import Any, Dict, List, Optional

from src.storage.db import QuechuaDB
from src.segmentation.scaffold import ScaffoldBuilder
from src.segmentation.slots import MorphotacticValidator


# ---------------------------------------------------------------------------
# Glosado corto (estilo Leipzig) por morfema. Mapea la forma limpia del sufijo
# a una etiqueta compacta usada en la glosa interlineal.
# ---------------------------------------------------------------------------
GLOSS_SHORT = {
    # Evidenciales / validadores (ranura 9)
    "mi": "EVID.DIR", "m": "EVID.DIR",
    "si": "EVID.REP", "s": "EVID.REP",
    "cha": "EVID.CONJ", "chá": "EVID.CONJ",
    "chu": "INTERR/NEG",
    "puni": "ENF",
    # Clíticos / conectivos (ranura 8)
    "qa": "TOP", "pas": "ADIT", "pis": "ADIT", "raq": "AUN",
    "ña": "YA", "lla": "LIM", "taq": "CONTR",
    # Casos nominales (ranura 5)
    "ta": "AC", "man": "ILA", "manta": "ABL", "pi": "LOC",
    "wan": "INSTR/COM", "paq": "BEN", "rayku": "CAUS",
    "kama": "LIM.TERM", "pura": "ENTRE", "nka": "DISTR",
    # Persona verbal / sujeto / futuro (ranura 5)
    "ni": "1SG", "nki": "2SG", "n": "3SG",
    "nchis": "1PL.INCL", "nchik": "1PL.INCL",
    "yku": "1PL.EXCL", "nkichis": "2PL", "nku": "3PL",
    "sunchis": "1PL.INCL.FUT", "sunchik": "1PL.INCL.FUT",
    "nqa": "3SG.FUT", "saq": "1SG.FUT",
    # Plural nominal (ranura 4)
    "kuna": "PL",
    # Posesivos nominales (ranura 3)
    "y": "1SG.POS", "yki": "2SG.POS",
    # Tiempo / aspecto / nominalizadores (ranura 3)
    "sha": "PROG", "chka": "PROG", "rqa": "PAS", "rqan": "PAS",
    "ran": "PAS", "sqa": "PART.PAS", "spa": "SUBORD", "pti": "SUBORD",
    "q": "AG/HAB", "na": "NMLZ",
    # Objeto verbal / eufónico (ranura 2)
    "-ni-": "EUF", "ni-": "EUF", "wa": "1.OBJ",
    # Derivacionales (ranura 1)
    "naku": "RECIP", "chi": "CAUS", "kuy": "NMLZ", "ku": "REFL",
    "ri": "INCO", "raya": "DUR", "naya": "DESID", "paya": "ITER",
    "mu": "CISL", "pu": "BEN.DIR", "ysi": "ASIST", "pa": "ITER/BEN",
}


class MorphosyntacticAnalyzer:
    """Produce el análisis morfosintáctico estructurado de frases o palabras."""

    # Patrón de segmentación de oraciones (respeta signos finales . ! ? …)
    _SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?…])\s+")

    def __init__(self, db: Optional[QuechuaDB] = None, db_path: Optional[str] = None):
        if db is not None:
            self.builder = ScaffoldBuilder(db=db)
        else:
            self.builder = ScaffoldBuilder(db_path=db_path)

    # -----------------------------------------------------------------------
    # API pública
    # -----------------------------------------------------------------------

    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analiza un párrafo (o palabra) y devuelve la estructura completa:
        {
          "texto_original": str,
          "num_oraciones": int,
          "num_tokens": int,
          "marcadores_globales": {...},
          "oraciones": [ { "indice", "texto", "tokens": [ <token_analizado>, ... ] } ]
        }
        """
        text_clean = (text or "").strip()
        if not text_clean:
            return {
                "texto_original": "",
                "num_oraciones": 0,
                "num_tokens": 0,
                "marcadores_globales": {"evidenciales": [], "clusividad": None},
                "oraciones": [],
            }

        sentences = self._split_sentences(text_clean)

        oraciones: List[Dict[str, Any]] = []
        total_tokens = 0
        global_evidentials: List[str] = []
        global_clusivity: Optional[str] = None

        for s_idx, sentence in enumerate(sentences):
            scaffold = self.builder.build_sentence_scaffold(sentence)
            raw_words = scaffold.get("words", [])

            tokens: List[Dict[str, Any]] = []
            pos_idx = 0
            for w in raw_words:
                token = self._transform_word(w, pos_idx)
                tokens.append(token)
                if not token["es_puntuacion"]:
                    pos_idx += 1
                    total_tokens += 1

            markers = scaffold.get("linguistic_markers", {})
            global_evidentials.extend(markers.get("evidentials", []))
            if markers.get("clusivity") and global_clusivity is None:
                global_clusivity = markers.get("clusivity")

            oraciones.append({
                "indice": s_idx,
                "texto": sentence,
                "marcadores": {
                    "evidenciales": markers.get("evidentials", []),
                    "clusividad": markers.get("clusivity"),
                },
                "tokens": tokens,
            })

        return {
            "texto_original": text_clean,
            "num_oraciones": len(oraciones),
            "num_tokens": total_tokens,
            "marcadores_globales": {
                "evidenciales": sorted(set(global_evidentials)),
                "clusividad": global_clusivity,
            },
            "oraciones": oraciones,
        }

    def analyze_word(self, word: str) -> Dict[str, Any]:
        """Analiza una sola palabra y devuelve su token estructurado."""
        w_scaffold = self.builder.build_word_scaffold(word.strip())
        return self._transform_word(w_scaffold, 0)

    # -----------------------------------------------------------------------
    # Internos
    # -----------------------------------------------------------------------

    def _split_sentences(self, text: str) -> List[str]:
        parts = [p.strip() for p in self._SENTENCE_SPLIT_RE.split(text) if p.strip()]
        return parts if parts else [text]

    def _transform_word(self, w: Dict[str, Any], posicion: int) -> Dict[str, Any]:
        """Convierte una entrada del scaffold en el contrato estable de token."""
        surface = w.get("surface", "")

        if w.get("is_punct"):
            return {
                "token": surface,
                "posicion": None,
                "es_puntuacion": True,
                "raiz": surface,
                "lema": surface,
                "categoria_gramatical": "punct",
                "sufijos": [],
                "glosa": surface,
                "acepciones": [],
                "marcadores": {"evidencialidad": None, "clusividad": None},
                "encontrado_en_diccionario": False,
                "confianza": 1.0,
            }

        raiz = w.get("root", "")
        lema = w.get("canonical_lemma") or w.get("stem", {}).get("headword") or raiz
        pos = w.get("pos", "desconocido")
        found = bool(w.get("found_in_dict"))

        acepciones = self._transform_senses(w.get("senses", []))
        sufijos = [self._transform_suffix(s) for s in w.get("suffixes", [])]

        evidencialidad, clusividad = self._extract_token_markers(sufijos)
        glosa = self._build_gloss(lema, sufijos)
        confianza = self._estimate_confidence(found, sufijos, w.get("suffixes", []))

        return {
            "token": surface,
            "posicion": posicion,
            "es_puntuacion": False,
            "raiz": raiz,
            "lema": lema,
            "categoria_gramatical": pos,
            "glosa": glosa,
            "acepciones": acepciones,
            "sufijos": sufijos,
            "marcadores": {
                "evidencialidad": evidencialidad,
                "clusividad": clusividad,
            },
            "encontrado_en_diccionario": found,
            "confianza": confianza,
        }

    def _transform_senses(self, senses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for s in senses:
            # senses viene de scaffold.build_word_scaffold: {sense_index, definition, domain, synonyms}
            out.append({
                "indice": s.get("sense_index") or s.get("index") or (len(out) + 1),
                "definicion": s.get("definition") or s.get("definition_es") or "",
                "dominio": s.get("domain") or s.get("semantic_domain"),
                "sinonimos": s.get("synonyms"),
            })
        return out

    def _transform_suffix(self, s: Dict[str, Any]) -> Dict[str, Any]:
        morfema = s.get("morpheme", "")
        clean = morfema.strip().lstrip("-").rstrip("-").lower()
        slot = s.get("slot")
        if slot is None:
            slot = MorphotacticValidator.get_slot(clean)
        return {
            "morfema": morfema,
            "slot": slot,
            "categoria": s.get("category", ""),
            "subcategoria": s.get("name", ""),
            "funcion": s.get("role", ""),
            "glosa_corta": GLOSS_SHORT.get(clean, clean.upper()),
            "ejemplos": s.get("examples", ""),
        }

    def _extract_token_markers(self, sufijos: List[Dict[str, Any]]):
        evidencialidad = None
        clusividad = None
        for s in sufijos:
            clean = s["morfema"].strip().lstrip("-").rstrip("-").lower()
            if clean in ("mi", "m"):
                evidencialidad = "DIRECTO / ATESTIGUADO (-mi)"
            elif clean in ("si", "s"):
                evidencialidad = "REPORTATIVO (-si)"
            elif clean in ("cha", "chá"):
                evidencialidad = "CONJETURAL (-chá)"
            if clean in ("nchis", "nchik", "sunchis", "sunchik"):
                clusividad = "INCLUSIVO (hablante + oyente)"
            elif clean == "yku":
                clusividad = "EXCLUSIVO (hablante + otros, sin oyente)"
        return evidencialidad, clusividad

    def _build_gloss(self, lema: str, sufijos: List[Dict[str, Any]]) -> str:
        """Glosa interlineal compacta: LEMA-GLOSA1-GLOSA2..."""
        parts = [lema] if lema else []
        for s in sufijos:
            parts.append(s["glosa_corta"])
        return "-".join(parts) if parts else ""

    def _estimate_confidence(
        self,
        found: bool,
        sufijos: List[Dict[str, Any]],
        raw_suffixes: List[Dict[str, Any]],
    ) -> float:
        """
        Heurística simple de confianza [0..1]:
        - Base alta si la raíz se halló en el diccionario.
        - Penaliza sufijos no reconocidos (categoría DESCONOCIDO).
        """
        score = 0.9 if found else 0.5
        unknown = sum(
            1 for s in raw_suffixes if (s.get("category", "") == "DESCONOCIDO")
        )
        if raw_suffixes:
            score -= 0.1 * (unknown / max(1, len(raw_suffixes)))
        return round(max(0.1, min(1.0, score)), 2)


def analyze_text(text: str, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Función de conveniencia: analiza un texto y devuelve la estructura completa."""
    return MorphosyntacticAnalyzer(db_path=db_path).analyze(text)
