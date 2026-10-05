"""
Parser para el archivo de sufijos (suffixes - V3.0.csv).
Estructura taxonomía, alomorfías, ranuras morfotácticas canónicas (slots 1..9),
definiciones y ejemplos de uso bilingües.
"""

import csv
import re
from typing import List, Dict, Any


def determine_slot_order(tipo: str, subtipo: str, categoria: str, subcategoria: str, sufijo: str) -> int:
    """
    Asigna una ranura morfotáctica canónica (1 a 9) según la taxonomía lingüística quechua.
    """
    s_upper = sufijo.upper().strip()
    sub_upper = subcategoria.upper()
    cat_upper = categoria.upper()
    subt_upper = subtipo.upper()
    t_upper = tipo.upper()

    # Evidenciales y Validadores (última posición en la palabra)
    if "VALIDADOR" in subt_upper or s_upper in ("MI", "M", "SI", "S", "CHÁ", "CHA", "CHU"):
        return 9

    # Conectivos e Independientes de discurso (-qa, -pas, -raq, -ña, -lla, -taq, -puni)
    if "INDEPENDIENTE" in t_upper or s_upper in ("QA", "PAS", "PIS", "RAQ", "ÑA", "LLA", "TAQ", "PUNI"):
        return 8

    # Casos Nominales (-ta, -man, -manta, -pi, -wan, -paq, -rayku, -kama, etc.)
    if "CASO" in sub_upper or "FLEXIVO DE CASO" in sub_upper:
        return 5

    # Plural Nominal (-kuna)
    if s_upper == "KUNA" or ("NOMINAL" in cat_upper and "NUMERO" in sub_upper):
        return 4

    # Persona y Posesivo Nominal (-y, -yki, -n, -nchis, -yku) y eufónico -ni-
    if s_upper == "NI":
        return 2  # Antes de posesivo
    if "NOMINAL" in cat_upper and "PERSONA" in sub_upper:
        return 3

    # Verbal Flexivo: Persona y Número
    if "VERBAL" in cat_upper and ("PERSONA" in sub_upper or "NUMERO" in sub_upper):
        return 5

    # Verbal Flexivo: Tiempo y Aspecto (-sha, -chka, -rqa, -sqa, -saq, etc.)
    if "TIEMPO" in sub_upper or "ASPECTO" in sub_upper or s_upper in ("SHA", "CHKA", "RQA", "SQA", "SAQ", "Q"):
        return 3

    # Verbal Derivacional / Transicional
    if "VERBAL DERIVACIONAL" in cat_upper or "DERIVATIVO" in sub_upper:
        return 2

    # Nominal Derivacional
    if "NOMINAL DERIVACIONAL" in cat_upper:
        return 2

    # Predeterminado
    return 4


def parse_suffixes_csv(csv_path: str) -> List[Dict[str, Any]]:
    """
    Lee suffixes - V3.0.csv y devuelve una lista de diccionarios con metadatos estructurados.
    """
    suffixes = []
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader)
        for row in reader:
            if not row or not any(row):
                continue
            sufijo_raw = row[0].strip() if len(row) > 0 else ""
            if not sufijo_raw:
                continue

            tipo = row[1].strip() if len(row) > 1 else ""
            subtipo = row[2].strip() if len(row) > 2 else ""
            categoria = row[3].strip() if len(row) > 3 else ""
            subcategoria = row[4].strip() if len(row) > 4 else ""
            definicion = row[6].strip() if len(row) > 6 else ""
            ejemplos = row[7].strip() if len(row) > 7 else ""

            # Extraer alomorfos si vienen con barra (ej. Q/PAQ, MANTA/MANTAQ, etc.)
            clean_sufijo = sufijo_raw.lower().lstrip("-")
            allomorph_list = []
            if "/" in clean_sufijo:
                parts = [p.strip() for p in clean_sufijo.split("/") if p.strip()]
                primary_morpheme = parts[0]
                for p in parts:
                    allomorph_list.append(p)
            else:
                primary_morpheme = clean_sufijo
                allomorph_list.append(clean_sufijo)

            # Inclusiones fonológicas de alomorfía conocida
            if primary_morpheme == "mi" and "m" not in allomorph_list:
                allomorph_list.append("m")
            elif primary_morpheme == "si" and "s" not in allomorph_list:
                allomorph_list.append("s")
            elif primary_morpheme == "sha" and "chka" not in allomorph_list:
                allomorph_list.append("chka")
            elif primary_morpheme == "pas" and "pis" not in allomorph_list:
                allomorph_list.append("pis")

            slot = determine_slot_order(tipo, subtipo, categoria, subcategoria, primary_morpheme)

            suffixes.append({
                "morpheme": sufijo_raw,
                "morpheme_clean": primary_morpheme,
                "type": tipo,
                "subtype": subtipo,
                "category": categoria,
                "subcategory": subcategoria,
                "slot_order": slot,
                "definition": definicion,
                "raw_examples": ejemplos,
                "allomorphs": list(set(allomorph_list))
            })

    return suffixes
