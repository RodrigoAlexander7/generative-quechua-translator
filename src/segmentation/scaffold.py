"""
Constructor de andamiajes morfo-semánticos (Morfo-Semantic Scaffold).
Conecta el segmentador de morfemas con la base de datos de conocimiento
para enriquecer cada palabra con lemas, acepciones completas y funciones de sufijos.
"""

import re
from typing import List, Dict, Any, Optional
from src.storage.db import QuechuaDB
from src.segmentation.peeler import MorphemePeeler
from src.segmentation.normalizer import QuechuaNormalizer


class ScaffoldBuilder:
    """Genera el andamiaje morfo-semántico estructurado para una oración."""

    def __init__(self, db: Optional[QuechuaDB] = None, db_path: Optional[str] = None):
        if db is not None:
            self.db = db
        elif db_path is not None:
            self.db = QuechuaDB(db_path)
        else:
            self.db = QuechuaDB()
        self.peeler = MorphemePeeler(self.db)

    def tokenize_sentence(self, sentence: str) -> List[str]:
        """Separa la oración en tokens de palabras y signos ortográficos."""
        # Normalizar apóstrofes tipográficos curvos (U+2019, U+2018, grave) a apóstrofe recto U+0027
        norm_sentence = sentence.replace("’", "'").replace("‘", "'").replace("`", "'")
        # Respeta apóstrofes internos para consonantes glotalizadas (t'anta, k'aspi, wak'uy)
        pattern = r"([A-Za-zÁÉÍÓÚáéíóúÑñ']+|[.,;:!?¿¡\"()«»—-])"
        tokens = re.findall(pattern, norm_sentence)
        return [t.strip() for t in tokens if t.strip()]

    def build_word_scaffold(self, word: str) -> Dict[str, Any]:
        """Construye el andamiaje morfo-semántico detallado para una palabra."""
        # Si es signo de puntuación
        if re.match(r"^[.,;:!?¿¡\"()«»—-]+$", word):
            return {
                "surface": word,
                "is_punct": True,
                "root": word,
                "pos": "punct",
                "suffixes": []
            }

        seg = self.peeler.segment_word(word)
        root_str = seg["root"]
        suffixes_list = seg["suffixes"]

        # Recuperar información del lema o lemas (en caso de compuesto)
        lemma_data = None
        senses = []
        pos = "desconocido"

        if seg.get("is_compound"):
            # Palabra compuesta (ej. allpa + mayu)
            pos = "s. (compuesto)"
            for r in seg.get("roots", []):
                ld = self.db.get_lemma(r)
                if ld:
                    senses.append({
                        "headword": ld["headword"],
                        "pos": ld["pos"],
                        "senses": [s["definition_es"] for s in ld.get("senses", [])[:3]]
                    })
        else:
            lemma_data = self.db.get_lemma(root_str)
            if not lemma_data and root_str.endswith("y"):
                # Probar sin infinitivo
                lemma_data = self.db.get_lemma(root_str[:-1])
            elif not lemma_data:
                # Probar con infinitivo
                lemma_data = self.db.get_lemma(root_str + "y")

            if lemma_data:
                pos = lemma_data["pos"]
                senses = [
                    {
                        "sense_index": s["sense_index"],
                        "definition": s["definition_es"],
                        "domain": s.get("semantic_domain"),
                        "synonyms": s.get("synonyms")
                    }
                    for s in lemma_data.get("senses", [])
                ]

        # Recuperar información detallada de cada sufijo
        enriched_suffixes = []
        for s in suffixes_list:
            clean_s = s.lstrip("-").rstrip("-")
            suffix_data = self.db.get_suffix(clean_s)
            if suffix_data:
                enriched_suffixes.append({
                    "morpheme": f"-{clean_s}",
                    "name": suffix_data["subcategory"] or suffix_data["category"] or suffix_data["type"],
                    "slot": suffix_data["slot_order"],
                    "category": suffix_data["category"],
                    "role": suffix_data["definition"],
                    "examples": suffix_data["raw_examples"][:150] if suffix_data["raw_examples"] else ""
                })
            elif s == "-ni-":
                enriched_suffixes.append({
                    "morpheme": "-ni-",
                    "name": "Morfema Eufónico",
                    "slot": 2,
                    "category": "FONOTÁCTICO",
                    "role": "Inserta '-ni-' cuando la raíz termina en consonante antes de sufijo posesivo",
                    "examples": "yawar-ni-y = mi sangre"
                })
            else:
                enriched_suffixes.append({
                    "morpheme": f"-{clean_s}",
                    "name": "Sufijo Gramatical",
                    "slot": 5,
                    "category": "DESCONOCIDO",
                    "role": f"Sufijo morfológico -{clean_s}",
                    "examples": ""
                })

        hw = lemma_data["headword"] if lemma_data else root_str
        return {
            "surface": word,
            "is_punct": False,
            "root": root_str,
            "canonical_lemma": hw,
            "stem": {"headword": hw, "pos": pos},
            "pos": pos,
            "found_in_dict": bool(lemma_data or seg.get("is_compound")),
            "senses": senses,
            "suffixes": enriched_suffixes,
            "affixes": enriched_suffixes
        }

    def build_sentence_scaffold(self, sentence: str) -> Dict[str, Any]:
        """Construye el andamiaje morfo-semántico completo para toda una oración."""
        tokens = self.tokenize_sentence(sentence)
        words_scaffold = [self.build_word_scaffold(t) for t in tokens]

        # Resumen lingüístico global (evidenciales detectados, clusividad, etc.)
        evidentials_found = []
        clusivity_found = None

        for w in words_scaffold:
            for s in w.get("suffixes", []):
                m = s["morpheme"]
                if m in ("-mi", "-m"):
                    evidentials_found.append("DIRECTO / ATESTIGUADO (-mi)")
                elif m in ("-si", "-s"):
                    evidentials_found.append("REPORTATIVO (-si)")
                elif m in ("-chá", "-cha"):
                    evidentials_found.append("CONJETURAL (-chá)")
                elif m == "-nchis":
                    clusivity_found = "INCLUSIVO (hablante + oyente)"
                elif m == "-yku":
                    clusivity_found = "EXCLUSIVO (hablante + otros, sin oyente)"

        return {
            "original_sentence": sentence,
            "tokens_count": len(tokens),
            "linguistic_markers": {
                "evidentials": list(set(evidentials_found)),
                "clusivity": clusivity_found
            },
            "words": words_scaffold,
            "tokens": words_scaffold
        }

    def build_compact_scaffold(self, sentence: str) -> Dict[str, Any]:
        """
        Construye una versión ultraligera del andamiaje morfo-semántico optimizada
        para textos largos (hasta 1000 caracteres) y mínima latencia de tokens.
        """
        full = self.build_sentence_scaffold(sentence)
        compact_tokens = []
        for w in full.get("words", []):
            if w.get("is_punct"):
                continue
            surface = w.get("surface", "")
            root = w.get("root", "")
            pos = w.get("pos", "")
            senses = w.get("senses", [])
            primary_def = ""
            if senses:
                raw_d = senses[0].get("definition", "")
                clean_d = re.sub(r"^[A-Z][a-z]+\.\s*(?:\([^)]+\)\s*)?", "", raw_d)
                clean_d = clean_d.split(".")[0].split(";")[0].split("||")[0].strip()
                if clean_d:
                    primary_def = clean_d.split(",")[0].strip()

            affix_desc = []
            for a in w.get("suffixes", []):
                m = a.get("morpheme", "")
                name = a.get("name") or a.get("category", "")
                affix_desc.append(f"{m} ({name})")

            compact_tokens.append({
                "word": surface,
                "lemma": f"{root} [{pos}: {primary_def}]" if primary_def else f"{root} [{pos}]",
                "affixes": ", ".join(affix_desc) if affix_desc else "(sin afijos)"
            })

        return {
            "sentence": sentence,
            "linguistic_markers": full.get("linguistic_markers", {}),
            "compact_tokens": compact_tokens
        }


def build_sentence_scaffold(sentence: str, db: Optional[QuechuaDB] = None, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Función de conveniencia para construir el andamiaje morfo-semántico."""
    builder = ScaffoldBuilder(db=db, db_path=db_path)
    return builder.build_sentence_scaffold(sentence)


def build_compact_scaffold(sentence: str, db: Optional[QuechuaDB] = None, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Función de conveniencia para construir el andamiaje compacto."""
    builder = ScaffoldBuilder(db=db, db_path=db_path)
    return builder.build_compact_scaffold(sentence)


