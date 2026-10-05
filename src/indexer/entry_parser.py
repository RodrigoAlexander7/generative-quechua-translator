"""
Parser para el inventario léxico extraído de los diccionarios (AMLQ y fuentes).
Procesa entries.json resolviendo la polisemia, separando acepciones (||)
y extrayendo sinónimos y marcas dialectales.
"""

import json
import os
import re
from typing import List, Dict, Any
from collections import defaultdict
from src.storage.db import QuechuaDB


def parse_raw_definition(def_text: str) -> List[Dict[str, Any]]:
    """
    Desglosa el texto bruto de una definición en múltiples acepciones (senses),
    extrayendo marcas de sinónimos y dialectos.
    """
    senses_raw = def_text.split("||")
    parsed_senses = []

    for idx, raw_sense in enumerate(senses_raw, start=1):
        text = raw_sense.strip()
        if not text:
            continue

        synonyms = ""
        dialects = ""

        # Extraer sinónimos (SINÓN: ...)
        sinon_match = re.search(r"SINÓN:?\s*([^.]+)", text, re.IGNORECASE)
        if sinon_match:
            synonyms = sinon_match.group(1).strip()
            text = text.replace(sinon_match.group(0), "").strip()

        # Extraer variantes dialectales (Pe.Aya:, Bol:, Ec:, Arg:, etc.)
        dialect_matches = re.findall(r"([A-Za-z.]+:\s*[^.]+)", text)
        if dialect_matches:
            dialects = "; ".join(m.strip() for m in dialect_matches)
            for m in dialect_matches:
                text = text.replace(m, "").strip()

        # Extraer dominio semántico inicial si existe (ej. Folk., Relig., Med., Geog., Zool., Bot.)
        domain = None
        domain_match = re.match(r"^([A-Z][a-z]{2,5}\.)\s+(.+)$", text)
        if domain_match:
            domain = domain_match.group(1)
            text = domain_match.group(2)

        clean_def = re.sub(r"\s+", " ", text).strip().rstrip(".")

        parsed_senses.append({
            "sense_index": idx,
            "definition_es": clean_def if clean_def else raw_sense.strip(),
            "semantic_domain": domain,
            "synonyms": synonyms if synonyms else None,
            "dialect_variants": dialects if dialects else None
        })

    return parsed_senses


def load_and_group_entries(json_path: str) -> List[Dict[str, Any]]:
    """
    Carga entries.json y agrupa las entradas repetidas bajo un único lema,
    evitando que la polisemia sobrescriba acepciones.
    """
    with open(json_path, "r", encoding="utf-8") as f:
        raw_entries = json.load(f)

    # Agrupar por (palabra, categoría)
    grouped = defaultdict(list)
    for item in raw_entries:
        palabra = item["palabra"].strip()
        cat = item.get("categoria", "s.").strip()
        definicion = item.get("definicion", "").strip()
        grouped[(palabra, cat)].append(definicion)

    # Extraer también páginas 387 a 405 del PDF AMLQ original (letras W e Y que faltaban)
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(json_path))))
    amlq_pdf = os.path.join(repo_root, "input", "dictionaries", "diccionario-qeswa-academia-mayor-cuzco.pdf")
    if os.path.exists(amlq_pdf):
        try:
            import subprocess
            pdf_text = subprocess.check_output(["pdftotext", "-f", "387", "-l", "405", amlq_pdf, "-"]).decode("utf-8", errors="ignore")
            pdf_matches = re.findall(r"^([a-záéíóúñ'ñ]+)\.\s+(s\.|v\.|adj\.|adv\.|interj\.)\s+(.+)$", pdf_text, re.MULTILINE)
            for hw, cat, defn in pdf_matches:
                grouped[(hw.strip(), cat.strip())].append(defn.strip())
        except Exception:
            pass

    lemmas_list = []
    for (headword, pos), def_list in grouped.items():
        all_senses = []
        sense_counter = 1
        for d in def_list:
            sub_senses = parse_raw_definition(d)
            for s in sub_senses:
                s["sense_index"] = sense_counter
                all_senses.append(s)
                sense_counter += 1

        norm_hw = QuechuaDB.normalize_trivocalic(headword)
        phon_hw = QuechuaDB.to_phonetic(norm_hw)

        lemmas_list.append({
            "headword": headword,
            "headword_normalized": norm_hw,
            "headword_phonetic": phon_hw,
            "pos": pos,
            "source_id": "amlq_cuzco",
            "senses": all_senses
        })

    return lemmas_list
