"""
Reglas y restricciones morfotácticas de ranuras (Slot Constraints) del quechua sureño.
Verifica que las cadenas de sufijos cumplan el orden canónico gramatical.
"""

from typing import List, Dict, Any, Optional


# Mapeo de sufijos comunes a sus ranuras morfotácticas (1 a 9)
CANONICAL_SLOTS = {
    # Ranura 9: Evidenciales y Validadores finales
    "mi": 9, "m": 9, "si": 9, "s": 9, "chá": 9, "cha": 9, "chu": 9, "puni": 9,
    # Ranura 8: Clíticos y conectivos de discurso / tópico
    "qa": 8, "pas": 8, "pis": 8, "raq": 8, "ña": 8, "lla": 8, "taq": 8,
    # Ranura 5: Casos Nominales
    "ta": 5, "man": 5, "manta": 5, "pi": 5, "wan": 5, "paq": 5, "rayku": 5,
    "kama": 5, "pura": 5, "nka": 5,
    # Ranura 5: Persona Verbal (Sujeto / Futuro)
    "ni": 5, "nki": 5, "n": 5, "nchis": 5, "nchik": 5, "yku": 5, "nkichis": 5, "nku": 5,
    "sunchis": 5, "sunchik": 5, "sqani": 5,
    # Ranura 4: Plural Nominal
    "kuna": 4,
    # Ranura 3: Posesivos Nominales
    "y": 3, "yki": 3,
    # Ranura 3: Tiempo / Aspecto Verbal / Nominalizadores
    "sha": 3, "chka": 3, "rqa": 3, "sqa": 3, "saq": 3, "spa": 3, "pti": 3, "q": 3, "na": 3,
    # Ranura 2: Morfema Eufónico
    "-ni-": 2,
    # Ranura 1-2: Derivacionales y Transicionales
    "naku": 1, "chi": 1, "kuy": 1, "ku": 1, "ri": 1, "raya": 1, "naya": 1, "paya": 1,
    "mu": 1, "pu": 1, "ysi": 1, "cha": 1, "pa": 1, "yachiy": 1
}


class MorphotacticValidator:
    """Valida la coherencia de orden de una secuencia de sufijos en quechua."""

    @staticmethod
    def get_slot(suffix: str, default_slot: int = 5) -> int:
        clean = suffix.lower().lstrip("-")
        return CANONICAL_SLOTS.get(clean, default_slot)

    @staticmethod
    def is_valid_sequence(suffix_chain: List[str]) -> bool:
        """
        Verifica que los sufijos mantengan un orden monótonamente no decreciente de ranura,
        admitiendo clíticos flotantes o ambivalentes (-lla, -puni, etc.).
        """
        if len(suffix_chain) <= 1:
            return True

        floating_clitics = {"lla", "puni", "raq", "ña", "pas", "pis"}
        current_max_slot = 0
        for s in suffix_chain:
            s_clean = s.lower().lstrip("-")
            slot = MorphotacticValidator.get_slot(s_clean)
            if s_clean in floating_clitics:
                continue
            if slot < current_max_slot and not (current_max_slot >= 8 and slot >= 8):
                return False
            current_max_slot = max(current_max_slot, slot)

        return True
