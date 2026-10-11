"""
Módulo de normalización fonético-ortográfica para el quechua.
Maneja conversiones trivocálicas, neutralización de oclusivas y limpieza ortográfica.
"""

import re
from typing import Tuple


class QuechuaNormalizer:
    """Utilidades para normalización de formas superficiales y lemas en quechua."""

    @staticmethod
    def clean_token(token: str) -> str:
        """Limpia puntuación marginal pero preserva apóstrofes glotales internos."""
        t = token.replace("’", "'").replace("‘", "'").replace("`", "'").strip()
        t = re.sub(r"^[^\w']+", "", t)
        t = re.sub(r"[^\w']+$", "", t)
        return t

    @staticmethod
    def to_trivocalic(text: str) -> str:
        """
        Convierte ortografía pentavocálica (e, o) a trivocálica canónica (i, u),
        y normaliza la asimilación nasal hispanizada (mp -> np).
        Ejemplo: 'qheswa' -> 'qhiswa', 'orqo' -> 'urqu', 'hampi' -> 'hanpi'.
        """
        t = text.lower()
        t = t.replace("e", "i").replace("o", "u")
        # Normalización nasal: en quechua canónico ante bilabial se escribe 'np'
        t = t.replace("mp", "np")
        return t

    @staticmethod
    def to_phonetic(text: str) -> str:
        """
        Neutraliza la serie de oclusivas glotalizadas y aspiradas para búsqueda tolerante.
        Ejemplo: k', kh -> k; t', th -> t; ch', chh -> ch; p', ph -> p; q', qh -> q.
        """
        t = text.lower()
        t = t.replace("'", "").replace("’", "")
        t = re.sub(r"([ptcqk])h", r"\1", t)
        return t

    @staticmethod
    def normalize_for_lookup(surface_word: str) -> Tuple[str, str, str]:
        """
        Devuelve tupla (original_limpio, trivocalico, fonetico).
        """
        clean = QuechuaNormalizer.clean_token(surface_word).lower()
        tri = QuechuaNormalizer.to_trivocalic(clean)
        phon = QuechuaNormalizer.to_phonetic(tri)
        return clean, tri, phon
