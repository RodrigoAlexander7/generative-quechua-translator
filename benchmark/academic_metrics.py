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


# ---------------------------------------------------------------------------
# Detección de evidencialidad y clusividad (a nivel de palabra, con exclusiones)
# ---------------------------------------------------------------------------
# NOTA METODOLÓGICA: estas reglas solo PROPONEN etiquetas gold. Para el paper,
# las etiquetas deben verificarse manualmente en benchmark/dataset.json
# (campos "gold_evidential" y "gold_clusivity"); si existen, se usan siempre.

_VOWELS = "aeiouáéíóú"
# Terminaciones en -s que NO son reportativo (-pas/-pis aditivo, -chis persona plural)
_NON_REPORTATIVE_S = ("pas", "pis", "chis", "chik")
_HEDGES = ["tal vez", "quizás", "quizas", "quiza", "acaso", "probablemente", "posiblemente", "seguramente"]
_REPORT_MARKERS = ["dicen", "dice que", "cuentan", "según", "segun", "se dice", "dijeron", "contaron"]


def _words(text: str) -> List[str]:
    norm = text.lower().replace("’", "'").replace("‘", "'")
    return re.findall(r"[a-zñáéíóú']+", norm)


def detect_evidential(quechua_source: str) -> str:
    """Propone la categoría evidencial de la oración: reportativo > conjetural > directo > no_marcado."""
    found = set()
    for w in _words(quechua_source):
        if len(w) < 3:
            continue
        if w.endswith("chá"):
            found.add("conjetural")
        elif w.endswith("si") or (w.endswith("s") and w[-2] in _VOWELS and not w.endswith(_NON_REPORTATIVE_S)):
            found.add("reportativo")
        elif w.endswith("mi") or (w.endswith("m") and w[-2] in _VOWELS):
            found.add("directo")
    for cat in ("reportativo", "conjetural", "directo"):
        if cat in found:
            return cat
    return "no_marcado"


def detect_clusivity(quechua_source: str) -> str:
    """Propone la clusividad de 1PL: incluyente, excluyente, mixto o no_aplica."""
    incl = excl = False
    for w in _words(quechua_source):
        if "nchis" in w or "nchik" in w:
            incl = True
        # -yku persona/posesivo excluyente: al final de palabra o seguido solo de caso/clítico.
        # Se excluyen -y-kuna (mi + plural), -rayku (causal) y -yku- derivacional (samaykusunchis).
        if (re.search(r"yku(paq|pi|ta|man|manta|wan|pas|qa|raq|lla|mi|m)?$", w) and not w.endswith("rayku")) \
                or w.endswith(("saqku", "kiku")):
            excl = True
    if incl and excl:
        return "mixto"
    if incl:
        return "incluyente"
    if excl:
        return "excluyente"
    return "no_aplica"


def evaluate_evidentiality_compliance(
    quechua_source: str,
    translation_es: str,
    gold_label: Optional[str] = None
) -> Dict[str, Any]:
    """
    Evalúa la evidencialidad SOLO sobre el texto traducido (misma vara para
    ambas condiciones; los metadatos del andamiaje no cuentan).
    - reportativo: la traducción debe marcar reporte ("dicen que", "según"...).
    - conjetural: la traducción debe marcar duda ("tal vez", "quizás"...).
    - directo: la traducción NO debe introducir reporte ni duda espurios.
    is_compliant = None cuando la oración no está marcada (se excluye del EPR).
    """
    expected = gold_label or detect_evidential(quechua_source)
    t = translation_es.lower()
    has_hedge = any(h in t for h in _HEDGES)
    has_report = any(r in t for r in _REPORT_MARKERS)

    if expected == "reportativo":
        ok = has_report
    elif expected == "conjetural":
        ok = has_hedge
    elif expected == "directo":
        ok = not (has_hedge or has_report)
    else:
        return {"expected_evidential": expected, "is_compliant": None, "notes": "Sin validador marcado"}

    return {
        "expected_evidential": expected,
        "is_compliant": ok,
        "notes": "Respetado" if ok else f"Evidencial {expected} no reflejado en la traducción"
    }


def evaluate_clusivity_compliance(
    quechua_source: str,
    metadata_clus: Optional[str] = None,
    gold_label: Optional[str] = None
) -> Dict[str, Any]:
    """
    Evalúa la clusividad declarada en los metadatos estructurados.
    El español no distingue nosotros incluyente/excluyente en la superficie,
    por eso en la condición sin herramienta (sin metadatos) devuelve
    is_compliant = None (no evaluable) en lugar de asumir acierto.
    """
    expected = gold_label or detect_clusivity(quechua_source)
    if expected in ("no_aplica", "mixto"):
        return {"expected_clusivity": expected, "is_compliant": None, "notes": "Excluido del CAR"}
    if not metadata_clus:
        return {"expected_clusivity": expected, "is_compliant": None, "notes": "Sin metadatos (no evaluable)"}

    m = str(metadata_clus).lower()
    says_incl = "inclu" in m
    says_excl = "exclu" in m
    ok = (expected == "incluyente" and says_incl and not says_excl) or \
         (expected == "excluyente" and says_excl and not says_incl)
    return {
        "expected_clusivity": expected,
        "is_compliant": ok,
        "notes": "Correcto" if ok else f"Esperaba {expected}, obtuvo: {metadata_clus}"
    }


def paired_bootstrap(scores_a: List[float], scores_b: List[float], n_resamples: int = 2000, seed: int = 42) -> Dict[str, Any]:
    """
    Remuestreo bootstrap pareado (Koehn, 2004) de la diferencia media A - B.
    Devuelve la diferencia, el IC 95% y un p-valor unilateral aproximado (P[delta <= 0]).
    """
    import random
    n = min(len(scores_a), len(scores_b))
    if n == 0:
        return {"delta": None, "ci95": None, "p_value": None, "n": 0}
    rng = random.Random(seed)
    diffs = [scores_a[i] - scores_b[i] for i in range(n)]
    observed = sum(diffs) / n
    boots = []
    for _ in range(n_resamples):
        sample = [diffs[rng.randrange(n)] for _ in range(n)]
        boots.append(sum(sample) / n)
    boots.sort()
    lo = boots[int(0.025 * n_resamples)]
    hi = boots[int(0.975 * n_resamples) - 1]
    p = sum(1 for b in boots if b <= 0) / n_resamples
    return {"delta": round(observed, 2), "ci95": [round(lo, 2), round(hi, 2)], "p_value": round(p, 4), "n": n}
