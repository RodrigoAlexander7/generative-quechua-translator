"""
Enriquecedor morfosintáctico para quechua Cusco-Collao.
Deduce roles temáticos, casos gramaticales, evidencialidad, clusividad,
persona/número y rasgos aspectuales a partir de la descomposición morfológica.
Cumple estrictamente con las directivas lingüísticas de AGENTS.md.
"""

from typing import Dict, Any, List, Optional


# Mapeo canónico de sufijos de caso a caso y rol temático (Directiva 4 de AGENTS.md)
CASE_MAPPINGS = {
    "ta": {
        "case": "acusativo",
        "thematic_role": "objeto directo / meta de movimiento",
        "description": "Marca el paciente de la acción verbal o el destino hacia donde se dirige el movimiento."
    },
    "man": {
        "case": "ilativo / direccional",
        "thematic_role": "destinatario / dirección / objeto indirecto",
        "description": "Indica orientación hacia un lugar, destinatario de la acción o complemento indirecto."
    },
    "manta": {
        "case": "ablativo / procedencia",
        "thematic_role": "origen / procedencia / materia / tema",
        "description": "Señala punto de partida, material del que algo está hecho o tema de conversación ('acerca de')."
    },
    "pi": {
        "case": "locativo",
        "thematic_role": "ubicación espacial / temporal",
        "description": "Indica localización estática ('en', 'sobre', 'dentro de') en el espacio o en el tiempo."
    },
    "wan": {
        "case": "instrumental / comitativo",
        "thematic_role": "instrumento / compañía",
        "description": "Expresa el instrumento con el que se realiza la acción ('con') o compañía ('junto con')."
    },
    "paq": {
        "case": "benefactivo",
        "thematic_role": "beneficiario / propósito",
        "description": "Señala a favor o en beneficio de quién se realiza la acción ('para')."
    },
    "pa": {
        "case": "genitivo",
        "thematic_role": "poseedor / relación genitiva",
        "description": "Expresa pertenencia o relación de posesión tras raíz terminada en vocal ('de')."
    },
    "q": {
        "case": "genitivo (alomorfo)",
        "thematic_role": "poseedor / relación genitiva",
        "description": "Alomorfo genitivo tras raíz nominal terminada en consonante o nominalizador."
    },
    "rayku": {
        "case": "causal",
        "thematic_role": "causa / motivo",
        "description": "Expresa la razón o el motivo determinante de la acción ('por', 'a causa de')."
    },
    "kama": {
        "case": "limitativo",
        "thematic_role": "límite espacial / temporal",
        "description": "Señala el término o límite espacial o temporal de una acción ('hasta')."
    },
    "pura": {
        "case": "interactivo / asociativo",
        "thematic_role": "reciprocidad grupal",
        "description": "Indica relación mutua o exclusividad entre pares del mismo grupo ('entre')."
    }
}

# Evidenciales epistémicos (Directiva 2 de AGENTS.md)
EVIDENTIAL_MAPPINGS = {
    "mi": {
        "type": "testimonial_directo",
        "gloss": "DIR",
        "description": "Evidencial testimonial directo: al hablante le consta de primera mano lo afirmado (modo indicativo asertivo directo)."
    },
    "m": {
        "type": "testimonial_directo",
        "gloss": "DIR",
        "description": "Alomorfo de -mi tras vocal: conocimiento testimonial de primera mano."
    },
    "si": {
        "type": "reportativo",
        "gloss": "REP",
        "description": "Evidencial reportativo / testimonio indirecto: conocimiento de oídas ('dicen que...', 'según cuentan...')."
    },
    "s": {
        "type": "reportativo",
        "gloss": "REP",
        "description": "Alomorfo de -si tras vocal: testimonio indirecto / reportativo."
    },
    "chá": {
        "type": "conjetural_dubitativo",
        "gloss": "CONJ",
        "description": "Evidencial conjetural o dubitativo: conjetura o probabilidad epistémica ('tal vez...', 'quizás...')."
    },
    "cha": {
        "type": "conjetural_dubitativo",
        "gloss": "CONJ",
        "description": "Variante de -chá: conjetura o probabilidad epistémica."
    }
}

# Clusividad pronominal en 1ra persona plural (Directiva 3 de AGENTS.md)
CLUSIVITY_MAPPINGS = {
    "nchis": {
        "type": "inclusivo",
        "description": "1ra persona plural incluyente: incluye explícitamente al oyente ('tú y yo' / ñoqanchis)."
    },
    "nchik": {
        "type": "inclusivo",
        "description": "Variante dialectal incluyente: incluye al oyente."
    },
    "sunchis": {
        "type": "inclusivo_futuro",
        "description": "1ra persona plural futura incluyente: 'haremos (todos juntos)'."
    },
    "sunchik": {
        "type": "inclusivo_futuro",
        "description": "Variante futura incluyente."
    },
    "yku": {
        "type": "exclusivo",
        "description": "1ra persona plural excluyente: excluye explícitamente al oyente ('nosotros pero no tú' / ñoqayku)."
    }
}

# Marcadores discursivos y pragmáticos
PRAGMATIC_MAPPINGS = {
    "qa": {"name": "tópico", "role": "Marca el tema de la oración o información conocida / contextualizada."},
    "taq": {"name": "contrastivo / aditivo", "role": "Introduce contraste o adición enfática ('y', 'en cambio')."},
    "pas": {"name": "aditivo / inclusivo", "role": "Marca inclusión o adición ('también', 'incluso')."},
    "pis": {"name": "aditivo / inclusivo (alomorfo)", "role": "Variante Collao de -pas ('también', 'incluso')."},
    "chu": {"name": "interrogativo / polaridad", "role": "Pregunta sí/no o marca de polaridad negativa junto a mana/ama."},
    "lla": {"name": "limitativo / afectivo", "role": "Denota restricción o matiz afectivo/cortés ('solo', 'nomás', 'apenas')."},
    "puni": {"name": "enfático / certeza", "role": "Refuerza la certidumbre o habitualidad ('siempre', 'ciertamente')."},
    "raq": {"name": "continuativo", "role": "Indica persistencia temporal o prioridad ('todavía', 'aún', 'primero')."},
    "ña": {"name": "discontinuativo", "role": "Indica cambio de estado o culminación temporal ('ya')."}
}

# Rasgos de persona y número
PERSON_NUMBER_MAPPINGS = {
    "y": "1SG (posesivo nominal: mi)",
    "yki": "2SG (posesivo nominal: tu)",
    "n": "3SG (posesivo nominal: su / sujeto verbal 3SG)",
    "nchis": "1PL.INCL (incluyente: nuestro / nosotros)",
    "yku": "1PL.EXCL (excluyente: nuestro / nosotros)",
    "ykichis": "2PL (posesivo nominal: vuestro)",
    "nku": "3PL (posesivo nominal: sus / sujeto verbal 3PL)",
    "ni": "1SG (sujeto verbal: yo)",
    "nki": "2SG (sujeto verbal: tú)",
    "nkichis": "2PL (sujeto verbal: ustedes)",
    "wa": "1SG.OBJ (objeto verbal: a mí)",
    "sunki": "2SG.OBJ (sujeto 3SG a objeto 2SG: él te... a ti)"
}

# Rasgos verbales y aspectuales
VERBAL_ASPECT_MAPPINGS = {
    "sha": "progresivo / durativo (estar haciendo)",
    "chka": "progresivo / durativo (variante estándar)",
    "rqa": "tiempo pasado simple testimonial",
    "sqa": "pasado no testimonial / participio perfectivo",
    "saq": "tiempo futuro 1SG",
    "nqa": "tiempo futuro 3SG",
    "mu": "cislocativo / translocativo (hacia acá / allá)",
    "pu": "regresivo / benefactivo (retornar / en favor de uno)",
    "ku": "reflexivo / voz media / plural verbal",
    "chi": "causativo (hacer hacer)",
    "rqo": "urgencia / inceptivo (hacer con presteza)",
    "ru": "urgencia / inceptivo (alomorfo)",
    "naya": "desiderativo / inminencia (ganas de)",
    "raya": "estado continuo / durativo",
    "paya": "frecuentativo / reiterativo",
    "spa": "subordinador correferencial simultáneo (haciendo...)",
    "pti": "subordinador condicional / interreferencial (si... / cuando...)",
    "na": "participio de obligación / nominalizador de futuro o lugar"
}


class SyntacticEnricher:
    """Calcula el enriquecimiento sintáctico y pragmático para un token quechua."""

    @classmethod
    def enrich_token(
        cls,
        surface: str,
        root: str,
        pos: str,
        suffixes: List[Dict[str, Any]],
        is_punct: bool = False
    ) -> Dict[str, Any]:
        """
        Retorna un diccionario detallado con las funciones sintácticas deducidas
        a partir de la cadena de sufijos y la categoría léxica.
        """
        if is_punct:
            return {
                "case": None,
                "thematic_role": "puntuación",
                "evidentiality": None,
                "clusivity": None,
                "person_number": None,
                "pragmatics": [],
                "verbal_aspect": []
            }

        suffix_forms = [
            s.get("morpheme", "").lstrip("-").rstrip("-").lower()
            for s in suffixes
        ]

        # 1. Caso y Rol Temático
        case_info = None
        for s_form in suffix_forms:
            if s_form in CASE_MAPPINGS:
                case_info = CASE_MAPPINGS[s_form]
                break

        # Si no hay sufijo de caso pero es sustantivo, pronombre o adjetivo, es caso directo/nominativo
        if not case_info:
            clean_pos = (pos or "").lower()
            if any(p in clean_pos for p in ["s.", "sust", "pron", "adj"]):
                case = "nominativo"
                thematic_role = "sujeto / atributo predicativo"
            elif any(p in clean_pos for p in ["v.", "verb"]):
                case = "verbal"
                thematic_role = "núcleo del predicado"
            elif any(p in clean_pos for p in ["adv", "part"]):
                case = "invariable"
                thematic_role = "modificador adverbial / circunstancial"
            else:
                case = "nominativo / directo"
                thematic_role = "sujeto / argumento directo"
        else:
            case = case_info["case"]
            thematic_role = case_info["thematic_role"]

        # 2. Evidencialidad epistémica
        evidentiality = None
        for s_form in suffix_forms:
            if s_form in EVIDENTIAL_MAPPINGS:
                evidentiality = EVIDENTIAL_MAPPINGS[s_form]
                break

        # 3. Clusividad pronominal (1ra persona plural)
        clusivity = None
        for s_form in suffix_forms:
            if s_form in CLUSIVITY_MAPPINGS:
                clusivity = CLUSIVITY_MAPPINGS[s_form]
                break

        # Caso especial: pronombre léxico (ej: ñoqanchis, nuqanchis, ñoqayku, nuqayku)
        root_clean = root.lower().replace("’", "'").strip()
        if "nchis" in root_clean or "nchik" in root_clean:
            clusivity = CLUSIVITY_MAPPINGS["nchis"]
        elif "yku" in root_clean:
            clusivity = CLUSIVITY_MAPPINGS["yku"]

        # 4. Persona y Número
        person_number = []
        for s_form in suffix_forms:
            if s_form in PERSON_NUMBER_MAPPINGS:
                person_number.append(PERSON_NUMBER_MAPPINGS[s_form])

        # 5. Marcadores pragmáticos / discursivos
        pragmatics = []
        for s_form in suffix_forms:
            if s_form in PRAGMATIC_MAPPINGS:
                pragmatics.append(f"{PRAGMATIC_MAPPINGS[s_form]['name']} (-{s_form})")

        # 6. Rasgos aspectuales y verbales
        verbal_aspect = []
        for s_form in suffix_forms:
            if s_form in VERBAL_ASPECT_MAPPINGS:
                verbal_aspect.append(f"{VERBAL_ASPECT_MAPPINGS[s_form]} (-{s_form})")

        return {
            "case": case,
            "thematic_role": thematic_role,
            "evidentiality": evidentiality["type"] if evidentiality else None,
            "evidentiality_detail": evidentiality["description"] if evidentiality else None,
            "clusivity": clusivity["type"] if clusivity else None,
            "clusivity_detail": clusivity["description"] if clusivity else None,
            "person_number": person_number if person_number else None,
            "pragmatics": pragmatics,
            "verbal_aspect": verbal_aspect
        }
