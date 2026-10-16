"""
Motor de desprendimiento morfológico (Right-to-Left Morpheme Peeling) en Python puro.
Descompone palabras aglutinadas quechuas en raíz(ces) y cadena ordenada de sufijos.
"""

from typing import List, Dict, Any, Optional, Tuple, Set
from src.storage.db import QuechuaDB
from src.segmentation.normalizer import QuechuaNormalizer
from src.segmentation.slots import MorphotacticValidator


# Lista ordenada de sufijos frecuentes por longitud descendente para greedy matching
COMMON_SUFFIXES = [
    "nkichis", "nkichik", "sunchis", "sunchik",
    "manta", "rayku", "nchis", "nchik",
    "kuna", "kama", "pura", "naku",
    "paq", "man", "wan", "taq", "pas", "pis", "raq", "lla", "puni", "chu",
    "rqa", "rqan", "ran", "sqa", "saq", "sha", "chka", "pti", "spa", "yku", "nku", "yki", "nki", "nqa",
    "chi", "kuy", "naya", "raya", "paya", "ysi",
    "ta", "pi", "qa", "mi", "si", "cha", "chá", "ni", "ku", "ri", "mu", "pu", "wa", "ña",
    "na", "pa", "y", "n", "s", "m", "q"
]

# Raíces de clase cerrada (pronombres, demostrativos, partículas) y variantes Quechua Collao
CORE_CLOSED_STEMS = {
    "noqa", "ñoqa", "qan", "pay", "noqanchis", "ñoqanchis", "noqayku", "ñoqayku",
    "qankuna", "paykuna", "kay", "chay", "haqay", "ima", "pi", "may", "mana", "ama",
    "ancha", "ña", "lliw", "llapa", "wakin", "kiki", "sapa", "aswan", "qayna",
    "kunan", "minchha", "hina", "chawpi", "tuta", "pun", "lima", "arequipa", "luis", "rosa",
    "wak'u", "t'aysa", "wesq'a", "sispas", "qowe", "qhaku", "programay"
}


class MorphemePeeler:
    """Segmentador morfológico determinista para quechua."""

    def __init__(self, db: QuechuaDB):
        self.db = db
        self.known_stems: Set[str] = self.db.get_all_lemma_keys() | CORE_CLOSED_STEMS

    def is_known_stem(self, stem: str) -> bool:
        """Verifica si una raíz existe en el lexicón (exacta o trivocálica)."""
        s_clean = stem.lower().strip()
        if s_clean in self.known_stems:
            return True
        s_norm = QuechuaNormalizer.to_trivocalic(s_clean)
        if s_norm in self.known_stems:
            return True
        # Probar con 'y' para verbos cuyo lema en diccionario está en infinitivo
        if (s_clean + "y") in self.known_stems or (s_norm + "y") in self.known_stems:
            return True
        return False

    def segment_word(self, word: str) -> Dict[str, Any]:
        """
        Segmenta una palabra en superficie en raíz y lista ordenada de sufijos.
        Maneja palabras directas, flexionadas, compuestas y desconocidas.
        """
        raw_word = word.strip()
        clean_word, tri_word, _ = QuechuaNormalizer.normalize_for_lookup(raw_word)

        if not clean_word:
            return {"raw": raw_word, "root": "", "suffixes": [], "is_compound": False, "found": False}

        # 1. Caso directo: la palabra completa ya es una raíz conocida en el diccionario
        if self.is_known_stem(clean_word):
            return {
                "raw": raw_word,
                "root": clean_word,
                "suffixes": [],
                "is_compound": False,
                "found": True
            }

        # 2. Desprendimiento morfológico regresivo (Right-to-Left Peeling)
        best_segmentation = self._peel_recursive(clean_word, [])
        if best_segmentation:
            root, suffixes = best_segmentation
            return {
                "raw": raw_word,
                "root": root,
                "suffixes": suffixes,
                "is_compound": False,
                "found": True
            }

        # 3. Detección de palabras compuestas (R1 + R2 + sufijos opcionales)
        compound_result = self._check_compound(clean_word)
        if compound_result:
            r1, r2, suffixes = compound_result
            return {
                "raw": raw_word,
                "root": f"{r1}+{r2}",
                "roots": [r1, r2],
                "suffixes": suffixes,
                "is_compound": True,
                "found": True
            }

        # 4. Fallback: Desprender sufijos conocidos aunque la raíz no esté en el diccionario
        best_fallback = self._peel_fallback(clean_word)
        if best_fallback:
            root, suffixes = best_fallback
            return {
                "raw": raw_word,
                "root": root,
                "suffixes": suffixes,
                "is_compound": False,
                "found": False
            }

        # Sin segmentación posible
        return {
            "raw": raw_word,
            "root": clean_word,
            "suffixes": [],
            "is_compound": False,
            "found": False
        }

    def _peel_recursive(self, current_str: str, accumulated_suffixes: List[str]) -> Optional[Tuple[str, List[str]]]:
        """
        Busca secuencialmente secuencias válidas de sufijos de derecha a izquierda.
        """
        # Condición de éxito: la parte restante es una raíz conocida de al menos 2 letras
        if len(current_str) >= 2 and self.is_known_stem(current_str):
            ordered_suffixes = list(reversed(accumulated_suffixes))
            if MorphotacticValidator.is_valid_sequence(ordered_suffixes):
                return current_str, ordered_suffixes

        # Caso especial eufónico: si termina en consonante + 'ni' y el sufijo posterior es posesivo
        if current_str.endswith("ni") and len(accumulated_suffixes) > 0 and len(current_str) > 3:
            stem_before_ni = current_str[:-2]
            if self.is_known_stem(stem_before_ni):
                ordered = list(reversed(accumulated_suffixes + ["-ni-"]))
                return stem_before_ni, ordered

        # Probar cada sufijo candidato
        for s in COMMON_SUFFIXES:
            if current_str.endswith(s) and len(current_str) > len(s) + 1:
                prefix = current_str[:-len(s)]
                # Comprobar si prefix es raíz
                if len(prefix) >= 2 and self.is_known_stem(prefix):
                    ordered = list(reversed(accumulated_suffixes + [s]))
                    if MorphotacticValidator.is_valid_sequence(ordered):
                        return prefix, ordered

                # Si no es raíz directa, continuar pelando recursivamente (hasta 8 niveles de sufijos)
                if len(accumulated_suffixes) < 8:
                    res = self._peel_recursive(prefix, accumulated_suffixes + [s])
                    if res:
                        return res

        return None

    def _check_compound(self, word: str) -> Optional[Tuple[str, str, List[str]]]:
        """
        Verifica si la palabra es un compuesto de dos raíces: R1 + R2 + [sufijos].
        Ejemplo: allpamayupi -> allpa + mayu + -pi.
        """
        # Primero probar si sin sufijos se divide en dos raíces
        for i in range(3, len(word) - 2):
            part1 = word[:i]
            part2 = word[i:]
            if self.is_known_stem(part1) and self.is_known_stem(part2):
                return part1, part2, []

        # Luego probar desprendiendo sufijos de R2
        for s in COMMON_SUFFIXES:
            if word.endswith(s) and len(word) > len(s) + 5:
                base = word[:-len(s)]
                for i in range(3, len(base) - 2):
                    part1 = base[:i]
                    part2 = base[i:]
                    if self.is_known_stem(part1) and self.is_known_stem(part2):
                        return part1, part2, [s]

        return None

    def _peel_fallback(self, word: str) -> Optional[Tuple[str, List[str]]]:
        """Desprende los sufijos de derecha a izquierda aunque la raíz remanente sea desconocida."""
        curr = word
        suffixes = []
        changed = True
        while changed and len(curr) > 2 and len(suffixes) < 8:
            changed = False
            for s in COMMON_SUFFIXES:
                if curr.endswith(s) and len(curr) - len(s) >= 2:
                    suffixes.insert(0, s)
                    curr = curr[:-len(s)]
                    changed = True
                    break

        if suffixes:
            if MorphotacticValidator.is_valid_sequence(suffixes):
                return curr, suffixes
        return None
