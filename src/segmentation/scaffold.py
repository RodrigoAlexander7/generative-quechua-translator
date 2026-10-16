"""
Constructor de andamiajes morfo-semánticos (Morfo-Semantic Scaffold).
Conecta el segmentador de morfemas con la base de datos de conocimiento
para enriquecer cada palabra con lemas, acepciones completas y funciones de sufijos.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from src.storage.db import QuechuaDB
from src.segmentation.peeler import MorphemePeeler
from src.segmentation.normalizer import QuechuaNormalizer


# Glosas canónicas para pronombres, partículas de clase cerrada, variantes Quechua Collao
# y raíces frecuentes cuya primera entrada en AMLQ es un arcaísmo o abreviatura
CORE_LEXICON_GLOSSES: Dict[str, Tuple[str, str]] = {
    "noqa": ("pron.", "Yo (1SG)"),
    "ñoqa": ("pron.", "Yo (1SG)"),
    "noqayku": ("pron.", "Nosotros (1PL excluyente: sin ti)"),
    "ñoqayku": ("pron.", "Nosotros (1PL excluyente: sin ti)"),
    "noqanchis": ("pron.", "Nosotros (1PL incluyente: tú y yo)"),
    "ñoqanchis": ("pron.", "Nosotros (1PL incluyente: tú y yo)"),
    "qan": ("pron.", "Tú (2SG)"),
    "qankuna": ("pron.", "Ustedes (2PL)"),
    "pay": ("pron.", "Él / Ella (3SG)"),
    "paykuna": ("pron.", "Ellos / Ellas (3PL)"),
    "kay": ("pron./v.", "Este, esta, esto / aquí (o verbo ser/estar)"),
    "chay": ("pron.", "Ese, esa, eso"),
    "haqay": ("pron.", "Aquel, aquella"),
    "ima": ("pron.", "Qué / cosa"),
    "mana": ("adv.", "No (negación)"),
    "ama": ("adv.", "No (prohibitivo)"),
    "ancha": ("adv.", "Muy, sumamente"),
    "ña": ("adv.", "Ya"),
    "lliw": ("pron./adj.", "Todos, totalmente"),
    "llapa": ("adj.", "Todo, todos"),
    "llapan": ("adj.", "Todos, la totalidad"),
    "ilapan": ("adj.", "Todos, la totalidad"),
    "wakin": ("pron.", "Algunos, una parte"),
    "kiki": ("adj.", "Mismo, en persona (yo mismo / tú mismo)"),
    "sapa": ("adj.", "Solo, cada (o aumentativo -sapa)"),
    "aswan": ("adv.", "Más (comparativo)"),
    "hina": ("adv.", "Como, así como"),
    "qayna": ("adv.", "Ayer"),
    "kunan": ("adv.", "Ahora, hoy"),
    "minchha": ("adv.", "Pasado mañana"),
    "chawpi": ("s./adj.", "Medio, mitad, centro"),
    "tuta": ("s.", "Noche"),
    "huk": ("adj./num.", "Un, uno, otro"),
    "musuq": ("adj.", "Nuevo"),
    "allin": ("adj./adv.", "Bueno, bien"),
    "sumaq": ("adj.", "Hermoso, lindo, bonito"),
    "hatun": ("adj.", "Grande"),
    "huch'uy": ("adj.", "Pequeño"),
    "yuraq": ("adj.", "Blanco"),
    "yana": ("adj.", "Negro"),
    "puka": ("adj.", "Rojo"),
    "phiña": ("adj.", "Enojado, bravo, molesto"),
    "sallqa": ("adj.", "Salvaje, silvestre, de puna"),
    "ashkha": ("adj.", "Muchos, bastante"),
    "wasi": ("s.", "Casa, hogar, vivienda (yachay wasi = escuela/colegio)"),
    "waka": ("s.", "Vaca, ganado vacuno"),
    "runa": ("s.", "Persona, gente, ser humano"),
    "alqo": ("s.", "Perro"),
    "allqo": ("s.", "Perro"),
    "aiqo": ("s.", "Perro"),
    "michi": ("s./v.", "Gato (s.) / Pastear ganado (v. michiy)"),
    "qowe": ("s.", "Cuy, conejillo de Indias"),
    "qowi": ("s.", "Cuy, conejillo de Indias"),
    "wallpa": ("s.", "Gallina"),
    "k'anka": ("s.", "Gallo"),
    "urpi": ("s.", "Paloma"),
    "taruka": ("s.", "Venado andino"),
    "huk'ucha": ("s.", "Ratón"),
    "llama": ("s.", "Llama (camélido andino)"),
    "uywa": ("s.", "Ganado, animal doméstico"),
    "t'anta": ("s.", "Pan"),
    "sara": ("s.", "Maíz"),
    "papa": ("s.", "Papa, patata"),
    "aycha": ("s.", "Carne"),
    "tullu": ("s.", "Hueso"),
    "mikhuna": ("s.", "Comida, alimento (o v. mikhuy = comer)"),
    "p'acha": ("s.", "Ropa, vestimenta"),
    "ñakch'a": ("s./v.", "Peine (s.) / Peinar (v. ñakch'ay)"),
    "pichana": ("s.", "Escoba"),
    "puñuna": ("s.", "Cama"),
    "pukllana": ("s.", "Juguete"),
    "manka": ("s.", "Olla"),
    "punku": ("s.", "Puerta"),
    "chukcha": ("s.", "Cabello, pelo"),
    "maki": ("s.", "Mano"),
    "k'iri": ("s.", "Herida"),
    "qolqe": ("s.", "Dinero, plata"),
    "chakra": ("s.", "Chacra, terreno de cultivo"),
    "llaqta": ("s.", "Pueblo, ciudad"),
    "ñan": ("s.", "Camino"),
    "wawa": ("s.", "Hijo/a (de la mujer), niño pequeño"),
    "ususi": ("s.", "Hija"),
    "tayta": ("s.", "Papá, padre"),
    "mama": ("s.", "Mamá, madre"),
    "tura": ("s.", "Hermano (de la mujer)"),
    "masi": ("s.", "Compañero, par, amigo"),
    "erqe": ("s.", "Niño, niña"),
    "warma": ("s.", "Niño, muchacho"),
    "sipas": ("s.", "Señorita, joven"),
    "sispas": ("s.", "Señorita, joven"),
    "qhari": ("s.", "Varón, hombre"),
    "qhaku": ("s.", "Varón, hombre (qharikuna)"),
    "yachaq": ("s.", "Estudiante, el que aprende/sabe"),
    "onqosqa": ("adj./s.", "Enfermo"),
    "sayk'usqa": ("adj.", "Cansado"),
    "wak'u": ("v.", "Cocinar (variante Collao de wayk'uy)"),
    "wayk'u": ("v.", "Cocinar"),
    "wayk'una": ("v./s.", "Cocinar / para cocinar"),
    "mikhu": ("v.", "Comer (mikhuy)"),
    "ranti": ("v.", "Comprar (rantiy)"),
    "rantiq": ("s./v.", "A comprar / comprador"),
    "llank'a": ("v.", "Trabajar (llank'ay)"),
    "llank'ana": ("s./v.", "Trabajo, tarea (llank'ay = trabajar)"),
    "taki": ("v.", "Cantar (takiy)"),
    "takina": ("v./s.", "Cantar / canción"),
    "puklla": ("v.", "Jugar (pukllay)"),
    "picha": ("v.", "Limpiar, barrer (pichay)"),
    "t'aqsa": ("v.", "Lavar ropa (t'aqsay)"),
    "t'aysa": ("v.", "Lavar ropa (variante de t'aqsay)"),
    "puñu": ("v.", "Dormir (puñuy)"),
    "puñuku": ("v.", "Dormir (puñukuy)"),
    "puri": ("v.", "Caminar, andar (puriy)"),
    "ri": ("v.", "Ir (riy)"),
    "hamu": ("v.", "Venir (hamuy)"),
    "apa": ("v.", "Llevar (apay)"),
    "saqe": ("v.", "Dejar (saqey)"),
    "tarpu": ("v.", "Sembrar (tarpuy)"),
    "hasp'i": ("v.", "Escarbar la tierra/papa (hasp'iy)"),
    "kuchu": ("v.", "Cortar (kuchuy)"),
    "hampi": ("v.", "Curar, sanar (hampiy)"),
    "hanpi": ("v.", "Curar, sanar (hanpiy)"),
    "sipi": ("v.", "Matar (sipiy)"),
    "hap'i": ("v.", "Atrapar, agarrar (hap'iy)"),
    "wesq'a": ("v.", "Cerrar (wisq'ay)"),
    "wisq'a": ("v.", "Cerrar (wisq'ay)"),
    "maqchi": ("v.", "Lavar manos/cara (maqchiy)"),
    "tiya": ("v.", "Vivir, habitar, residir / sentarse (tiyay)"),
    "wiña": ("v.", "Crecer (wiñay)"),
    "rima": ("v.", "Hablar (rimay)"),
    "rimay": ("s./v.", "Idioma, lenguaje / hablar"),
    "yanapa": ("v.", "Ayudar (yanapay)"),
    "yacha": ("v.", "Saber, aprender (yachay)"),
    "yachachi": ("v.", "Enseñar (yachachiy)"),
    "muna": ("v.", "Querer, amar (munay)"),
    "maqa": ("v.", "Pelear, golpear (maqay)"),
    "taka": ("v.", "Pelear a golpes, golpear (takay)"),
    "tusu": ("v.", "Bailar (tusuy)"),
    "waqa": ("v.", "Llorar (waqay)"),
    "sama": ("v.", "Descansar (samay)"),
    "tuku": ("v.", "Terminar, acabar (tukuy)"),
    "ruwa": ("v.", "Hacer (ruway)"),
    "urma": ("v.", "Caer, caerse (urmay)"),
    "tari": ("v.", "Encontrar, hallar (tariy)"),
    "chura": ("v.", "Poner, colocar (churay)"),
    "wasicha": ("v.", "Techar o construir casa (wasichay)"),
    "qhellicha": ("v.", "Ensuciar (qhellichay)"),
    "wiraya": ("v.", "Engordar (wirayay)"),
    "yanaya": ("v.", "Ponerse negro, ennegrecer (yanayay)"),
    "pukaya": ("v.", "Ponerse rojo, enrojecer (pukayay)"),
    "yuraqya": ("v.", "Volverse blanco, encanecer (yuraqyay)"),
    "thantaya": ("v.", "Envejecer o desgastarse la ropa (thantayay)"),
    "para": ("v./s.", "Llover (paray) / lluvia"),
    "chikchi": ("v./s.", "Granizar (chikchiy) / granizo"),
    "ka": ("v.", "Ser, estar, haber (kay)"),
    "kasha": ("v.", "Estar (kashay = ka-sha-)"),
    "programay": ("v.", "Programar (préstamo)")
}

SUFFIX_SHORT_GLOSS: Dict[str, str] = {
    "ta": "acusativo (objeto directo) o meta",
    "man": "ilativo ('a / hacia') o potencial/condicional ('-ría')",
    "manta": "ablativo ('de / desde / acerca de') o comparativo ('más ... que')",
    "pi": "locativo ('en')",
    "wan": "instrumental/comitativo ('con')",
    "paq": "benefactivo/propósito ('para / para que')",
    "rayku": "causal ('por / a causa de')",
    "kama": "limitativo ('hasta')",
    "pura": "interactivo ('entre miembros de un mismo grupo')",
    "ntin": "inclusivo ('junto con')",
    "yoq": "posesivo ('que tiene')",
    "sapa": "aumentativo ('con mucho')",
    "kuna": "plural ('-s')",
    "y": "1SG posesivo ('mi') o infinitivo verbal",
    "yki": "2SG posesivo ('tu') o transición 1->2",
    "n": "3SG ('él/ella' o posesivo 'su') o evidencial directo tras vocal",
    "nchis": "1PL incluyente ('nosotros [tú y yo]' / 'nuestro')",
    "nchik": "1PL incluyente ('nosotros [tú y yo]' / 'nuestro')",
    "yku": "1PL excluyente ('nosotros [sin ti]' / 'nuestro')",
    "nkichis": "2PL ('ustedes')",
    "nku": "3PL ('ellos/ellas' o posesivo 'su de ellos')",
    "ni": "1SG verbal ('yo')",
    "-ni-": "partícula eufónica antes de posesivo",
    "nki": "2SG verbal ('tú')",
    "saq": "1SG futuro ('yo -ré'; con -ku = 1PL.EXCL futuro)",
    "nqa": "3SG futuro ('él/ella -rá'; con -ku = 3PL futuro)",
    "sunchis": "1PL incluyente futuro ('nosotros -remos')",
    "sun": "1PL incluyente futuro/exhortativo ('vamos a / -remos')",
    "sha": "progresivo ('estar -ndo')",
    "chka": "progresivo ('estar -ndo')",
    "rqa": "pasado experimentado",
    "rqan": "3SG pasado experimentado",
    "ran": "3SG pasado experimentado",
    "sqa": "participio ('-do') o pasado narrativo/pluscuamperfecto ('había -do')",
    "spa": "gerundio de sujeto idéntico ('-ndo / tras hacer')",
    "pti": "subordinador de sujeto distinto ('cuando / al')",
    "q": "agentivo o propósito con verbo de movimiento ('a + infinitivo')",
    "na": "nominalizador de propósito/objeto ('para -r / lo que se -a')",
    "ysi": "cooperativo/asistivo ('ayudar a')",
    "chi": "causativo ('hacer que otro haga')",
    "naya": "desiderativo/inminencia ('tener ganas de / querer / estar a punto de')",
    "naku": "recíproco ('mutuamente / entre sí')",
    "ku": "reflexivo ('-se') o pluralizador verbal (-saqku / -nqaku / -wankiku)",
    "mu": "traslocativo/cislocativo ('ir a hacer / hacia acá')",
    "pu": "benefactivo/regresivo",
    "wa": "objeto de 1ra persona ('me / nos')",
    "raq": "continuativo ('todavía / aún')",
    "ña": "ya ('ya')",
    "pas": "aditivo ('también')",
    "pis": "aditivo ('también')",
    "puni": "enfático/certeza ('de todas maneras / siempre / mismo')",
    "lla": "limitativo ('solo / nomás / pequeño')",
    "chu": "negación (con mana) o interrogación",
    "qa": "marcador de tópico",
    "mi": "evidencial directo/testimonial (certeza)",
    "m": "evidencial directo/testimonial (certeza)",
    "si": "evidencial reportativo ('dicen que')",
    "s": "evidencial reportativo ('dicen que')",
    "chá": "evidencial conjetural ('tal vez / quizás')"
}

VERBAL_SUFFIX_MARKERS = {
    "sha", "chka", "rqa", "rqan", "ran", "sqa", "saq", "nqa", "sunchis", "sun",
    "nki", "nkichis", "ni", "spa", "pti", "ysi", "chi", "naku", "naya", "mu", "pu", "wa"
}


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

        clean_s_set = {s.lstrip("-").rstrip("-") for s in suffixes_list}
        is_likely_verbal = bool(clean_s_set & VERBAL_SUFFIX_MARKERS)

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
            # Si tiene sufijos verbales, priorizar el lema verbal en infinitivo (root + 'y')
            if is_likely_verbal and not root_str.endswith("y"):
                lemma_data = self.db.get_lemma(root_str + "y") or self.db.get_lemma(root_str)
            else:
                lemma_data = self.db.get_lemma(root_str)
                if not lemma_data and root_str.endswith("y"):
                    lemma_data = self.db.get_lemma(root_str[:-1])
                elif not lemma_data:
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

            # Inyectar glosa canónica como primera acepción si existe en CORE_LEXICON_GLOSSES
            r_low = root_str.lower()
            if r_low in CORE_LEXICON_GLOSSES:
                c_pos, c_def = CORE_LEXICON_GLOSSES[r_low]
                if pos == "desconocido" or is_likely_verbal:
                    pos = c_pos
                senses.insert(0, {
                    "sense_index": 0,
                    "definition": c_def,
                    "domain": None,
                    "synonyms": None
                })

        # Recuperar información detallada de cada sufijo
        enriched_suffixes = []
        for s in suffixes_list:
            clean_s = s.lstrip("-").rstrip("-")
            suffix_data = self.db.get_suffix(clean_s)
            short_role = SUFFIX_SHORT_GLOSS.get(clean_s)
            if suffix_data:
                enriched_suffixes.append({
                    "morpheme": f"-{clean_s}",
                    "name": suffix_data["subcategory"] or suffix_data["category"] or suffix_data["type"],
                    "slot": suffix_data["slot_order"],
                    "category": suffix_data["category"],
                    "role": short_role or suffix_data["definition"],
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
                    "category": "FUNCIONAL",
                    "role": short_role or f"Sufijo morfológico -{clean_s}",
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
            "found_in_dict": bool(lemma_data or seg.get("is_compound") or root_str.lower() in CORE_LEXICON_GLOSSES),
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
            r_low = w.get("root", "").lower()
            if r_low in ("noqanchis", "ñoqanchis"):
                clusivity_found = "INCLUSIVO (hablante + oyente)"
            elif r_low in ("noqayku", "ñoqayku"):
                clusivity_found = "EXCLUSIVO (hablante + otros, sin oyente)"
            for s in w.get("suffixes", []):
                m = s["morpheme"]
                if m in ("-mi", "-m"):
                    evidentials_found.append("DIRECTO / ATESTIGUADO (-mi)")
                elif m in ("-si", "-s"):
                    evidentials_found.append("REPORTATIVO (-si)")
                elif m in ("-chá", "-cha"):
                    evidentials_found.append("CONJETURAL (-chá)")
                elif m in ("-nchis", "-nchik", "-sunchis", "-sunchik"):
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
                for s_item in senses:
                    raw_d = (s_item.get("definition") or "").strip()
                    dom = (s_item.get("domain") or "").strip()
                    clean_d = re.sub(r"^\.\s*\.\s*\.\s*", "", raw_d).strip()
                    clean_d = re.sub(r"^[A-Z][a-z]+\.\s*(?:\([^)]+\)\s*)?", "", clean_d)
                    clean_d = clean_d.split("||")[0].split(";")[0].strip()
                    if clean_d and clean_d.lower() != root.lower() and clean_d not in ("V", "V.", "Mús", "Mús."):
                        primary_def = clean_d
                        break
                    elif dom:
                        primary_def = dom.rstrip(".")
                        break

            affix_desc = []
            for a in w.get("suffixes", []):
                m = a.get("morpheme", "")
                clean_m = m.lstrip("-").rstrip("-")
                short_gloss = SUFFIX_SHORT_GLOSS.get(clean_m) or a.get("name") or a.get("category", "")
                affix_desc.append(f"{m} ({short_gloss})")

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


