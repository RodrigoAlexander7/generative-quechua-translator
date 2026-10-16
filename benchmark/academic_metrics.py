"""
Métricas de evaluación académica para traducción Quechua -> Español.
Diseñado para la generación de resultados publicables en papers (ACL / EMNLP / AmericasNLP).

Métricas implementadas:
1. chrF++ (n-gramas de caracteres y palabras, métrica recomendada para morfología rica).
2. BLEU (con suavizado de n-gramas y penalización por brevedad).
3. EPR (Evidentiality Preservation Rate): Preservación de validadores epistémicos (-mi, -si, -chá).
4. CAR (Clusivity Accuracy Rate): Discriminación de 1ra persona plural (incluyente vs excluyente).
"""

import re
import math
from typing import Dict, Any, List, Optional
from collections import Counter


def _get_char_ngrams(text: str, n: int) -> Counter:
    """Extrae n-gramas de caracteres ignorando espacios."""
    collapsed = "".join(text.split())
    if len(collapsed) < n:
        return Counter()
    return Counter(collapsed[i:i+n] for i in range(len(collapsed) - n + 1))


def _get_word_ngrams(tokens: List[str], n: int) -> Counter:
    """Extrae n-gramas de palabras."""
    if len(tokens) < n:
        return Counter()
    return Counter(tuple(tokens[i:i+n]) for i in range(len(tokens) - n + 1))


def compute_sentence_chrf(
    hypothesis: str,
    reference: str,
    char_order: int = 6,
    word_order: int = 2,
    beta: float = 2.0
) -> float:
    """
    Calcula chrF++ (character and word n-gram F-score).
    Implementación autocontenida que replica el estándar de sacrebleu/Popović (2017).
    Rango de salida: 0.0 a 100.0.
    """
    hyp = hypothesis.strip().lower()
    ref = reference.strip().lower()

    if not hyp or not ref:
        return 0.0

    hyp_words = re.findall(r"\w+", hyp)
    ref_words = re.findall(r"\w+", ref)

    char_precisions = []
    char_recalls = []

    for n in range(1, char_order + 1):
        hyp_ngrams = _get_char_ngrams(hyp, n)
        ref_ngrams = _get_char_ngrams(ref, n)

        total_hyp = sum(hyp_ngrams.values())
        total_ref = sum(ref_ngrams.values())

        if total_hyp == 0 or total_ref == 0:
            continue

        overlap = sum((hyp_ngrams & ref_ngrams).values())
        p = overlap / total_hyp if total_hyp > 0 else 0.0
        r = overlap / total_ref if total_ref > 0 else 0.0

        char_precisions.append(p)
        char_recalls.append(r)

    word_precisions = []
    word_recalls = []

    for n in range(1, word_order + 1):
        hyp_ngrams = _get_word_ngrams(hyp_words, n)
        ref_ngrams = _get_word_ngrams(ref_words, n)

        total_hyp = sum(hyp_ngrams.values())
        total_ref = sum(ref_ngrams.values())

        if total_hyp == 0 or total_ref == 0:
            continue

        overlap = sum((hyp_ngrams & ref_ngrams).values())
        p = overlap / total_hyp if total_hyp > 0 else 0.0
        r = overlap / total_ref if total_ref > 0 else 0.0

        word_precisions.append(p)
        word_recalls.append(r)

    all_precisions = char_precisions + word_precisions
    all_recalls = char_recalls + word_recalls

    if not all_precisions or not all_recalls:
        return 0.0

    avg_p = sum(all_precisions) / len(all_precisions)
    avg_r = sum(all_recalls) / len(all_recalls)

    if avg_p + avg_r == 0:
        return 0.0

    beta_sq = beta ** 2
    f_score = (1 + beta_sq) * (avg_p * avg_r) / ((beta_sq * avg_p) + avg_r)
    return round(f_score * 100.0, 2)


def compute_sentence_bleu(hypothesis: str, reference: str, max_n: int = 4) -> float:
    """
    Calcula sentence BLEU con suavizado tipo Chen & Cherry (smoothing 1).
    Rango de salida: 0.0 a 100.0.
    """
    hyp_tokens = re.findall(r"\w+", hypothesis.strip().lower())
    ref_tokens = re.findall(r"\w+", reference.strip().lower())

    hyp_len = len(hyp_tokens)
    ref_len = len(ref_tokens)

    if hyp_len == 0:
        return 0.0

    # Brevity penalty
    if hyp_len > ref_len:
        bp = 1.0
    elif hyp_len == 0:
        bp = 0.0
    else:
        bp = math.exp(1 - (ref_len / hyp_len))

    log_precision_sum = 0.0
    weights = 1.0 / max_n

    for n in range(1, max_n + 1):
        hyp_ngrams = _get_word_ngrams(hyp_tokens, n)
        ref_ngrams = _get_word_ngrams(ref_tokens, n)

        total_hyp = sum(hyp_ngrams.values())
        overlap = sum((hyp_ngrams & ref_ngrams).values())

        # Suavizado de Laplace suave para evitar log(0)
        p_n = (overlap + 0.1) / (total_hyp + 0.1) if total_hyp > 0 else 1e-5
        log_precision_sum += weights * math.log(p_n)

    bleu = bp * math.exp(log_precision_sum)
    return round(bleu * 100.0, 2)


def evaluate_evidentiality_compliance(
    quechua_source: str,
    translation_es: str,
    metadata_evid: Optional[str] = None
) -> Dict[str, Any]:
    """
    Evalúa si la oración quechua codifica evidencialidad (-mi, -si, -chá) y si
    la traducción o metadatos la reflejan fielmente.
    """
    src_lower = quechua_source.lower()
    trans_lower = translation_es.lower()
    meta_lower = (metadata_evid or "").lower()

    # Detectar marcadores en quechua
    has_direct = bool(re.search(r"\b\w+(mi|n)\b", src_lower)) or "-mi" in src_lower
    has_reportative = bool(re.search(r"\b\w+(si|s)\b", src_lower)) or "-si" in src_lower
    has_conjectural = bool(re.search(r"\b\w+(chá|cha)\b", src_lower)) or "-chá" in src_lower or "-cha" in src_lower

    category = "no_marcado"
    correct = True
    notes = "Sin validador marcado"

    if has_reportative:
        category = "reportativo"
        # Debe reflejar testimonio indirecto: "dicen", "cuenta", "según", o en metadatos
        reflected = any(w in trans_lower for w in ["dicen", "cuenta", "según", "se dice", "dijeron"]) or "reportat" in meta_lower
        correct = reflected
        notes = "Reportativo capturado" if reflected else "Faltó marcar reporte indirecto (-si)"
    elif has_conjectural:
        category = "conjetural"
        # Debe reflejar duda o conjetura: "tal vez", "quizás", "acaso", "probablemente", o en metadatos
        reflected = any(w in trans_lower for w in ["tal vez", "quizás", "quiza", "acaso", "probable", "posiblemente"]) or "conjetur" in meta_lower or "duda" in meta_lower
        correct = reflected
        notes = "Conjetura capturada" if reflected else "Faltó reflejar conjetura/duda (-chá)"
    elif has_direct:
        category = "directo_asertivo"
        # En modo directo, no debe contener marcadores de rumor ni duda espuria
        incorrect = any(w in trans_lower for w in ["dicen que", "quizás", "tal vez"])
        correct = not incorrect
        notes = "Asertivo directo respetado" if correct else "Contaminación modal en hecho directo"

    return {
        "expected_evidential": category,
        "is_compliant": correct,
        "notes": notes
    }


def evaluate_clusivity_compliance(
    quechua_source: str,
    translation_es: str,
    metadata_clus: Optional[str] = None
) -> Dict[str, Any]:
    """
    Evalúa la preservación de clusividad pronominal en 1ra persona plural:
    - -nchis / ñoqanchis: Incluyente (tú y yo)
    - -yku / ñoqayku: Excluyente (nosotros sin ti)
    """
    src_lower = quechua_source.lower()
    meta_lower = (metadata_clus or "").lower()

    has_incl = "nchis" in src_lower or "sunchis" in src_lower or "noqanchis" in src_lower or "ñoqanchis" in src_lower
    has_excl = "yku" in src_lower or "noqayku" in src_lower or "ñoqayku" in src_lower

    if not has_incl and not has_excl:
        return {
            "expected_clusivity": "no_aplica",
            "is_compliant": True,
            "notes": "No interviene 1ra plural"
        }

    expected = "incluyente" if has_incl else "excluyente"
    is_compliant = True
    notes = f"Clusividad {expected}"

    if metadata_clus:
        if expected == "incluyente" and ("inclu" in meta_lower):
            is_compliant = True
            notes = "Inclusividad validada en metadatos"
        elif expected == "excluyente" and ("exclu" in meta_lower):
            is_compliant = True
            notes = "Exclusividad validada en metadatos"
        else:
            is_compliant = False
            notes = f"Confusión de clusividad (esperaba {expected}, obtuvo {metadata_clus})"
    else:
        # En modo sin herramientas, el español estándar suele ser ambiguo ("nosotros"),
        # se califica como cumplimiento parcial o neutral a menos que haya contradicción explícita.
        notes = f"Marcador {expected} en fuente quechua (sin metadatos en español)"

    return {
        "expected_clusivity": expected,
        "is_compliant": is_compliant,
        "notes": notes
    }
