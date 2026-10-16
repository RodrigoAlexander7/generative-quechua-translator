"""
Plantillas de prompts para traducción generativa Quechua -> Español.
Diseñado para alimentar a LLMs (Gemini / Claude / GPT) con un
Andamiaje Morfo-Semántico (Morfo-Semantic Scaffold) estructurado.
"""

import json
from typing import Any, Dict, Union


SYSTEM_INSTRUCTION = """Eres un lingüista especialista en lengua quechua (variante Cusco-Collao y Quechua Sureño) y traductor profesional al español.
Tu tarea es traducir con la máxima fidelidad morfosintáctica y naturalidad idiomática oraciones en Quechua al Español a partir del análisis morfo-semántico estructurado que se te proporciona."""


PROMPT_TEMPLATE = """Eres un lingüista especialista en lengua quechua (variante Cusco-Collao y Quechua Sureño) y traductor profesional al español.

Tu tarea es traducir la siguiente oración en Quechua al Español de forma fluida, exacta e idiomática, apoyándote ESTRICTAMENTE en el análisis morfo-semántico provisto.

### DIRECTIVAS LINGÜÍSTICAS OBLIGATORIAS:
1. EVIDENCIALIDAD EPISTÉMICA (VALIDADORES):
   - Evidencial testimonial/directo (-mi / -n): Traduce en tono indicativo asertivo directo (el hablante lo presenció o le consta con certeza absoluta).
   - Evidencial reportativo/indirecto (-si / -s): DEBES reflejar explícitamente que es información transmitida por terceros ("dicen que...", "según cuentan...", "se dice que...").
   - Evidencial conjetural (-chá): DEBES reflejar incertidumbre, conjetura o deducción epistémica ("tal vez...", "quizás...", "probablemente...").

2. CLUSIVIDAD PRONOMINAL EN 1RA PERSONA PLURAL:
   - 1ra persona plural incluyente (-nchis / ñoqanchis): Implica "nosotros (incluyéndote a ti / al interlocutor)". Refleja el carácter inclusivo si el contexto lo amerita o explícalo en la clusividad.
   - 1ra persona plural excluyente (-yku / ñoqayku): Implica "nosotros (pero no tú / sin incluirte a ti)".

3. CASOS Y ROLES TEMÁTICOS NOMINALES:
   - -ta: Objeto directo (acusativo) o meta de movimiento ("a", "hacia").
   - -man: Ilativo/direccional ("a", "hacia"), destinatario u objeto indirecto.
   - -manta: Ablativo/procedencia ("de", "desde", "acerca de") o causa/material.
   - -pi: Locativo ("en", "sobre", "dentro de").
   - -wan: Instrumental ("con", "mediante") o comitativo/compañía ("con", "junto a").
   - -paq: Benefactivo ("para", "en favor de").

4. POLISEMIA Y DESAMBIGUACIÓN CONTEXTUAL:
   - Entre las múltiples acepciones proporcionadas en el diccionario para cada raíz (especialmente palabras altamente polisémicas como 'wasi', 'allpa', etc.), selecciona la acepción exacta que guarde perfecta concordancia semántica con el predicado y sus argumentos.
   - Nunca inventes significados ajenos al repertorio léxico proporcionado.

5. NATURALIDAD Y PRECISIÓN IDIOMÁTICA:
   - La traducción al español debe ser gramaticalmente impecable y natural, evitando un calco palabra por palabra desarticulado, pero conservando rigurosamente todos los matices funcionales de los sufijos flexivos, derivacionales y validadores.

---
### DATOS DE ENTRADA:
Oración Original Quechua:
"{source_sentence}"

Andamiaje Morfo-Semántico (Análisis de Raíces y Sufijos):
```json
{scaffold_json}
```

---
### FORMATO DE RESPUESTA REQUERIDO:
Debes responder EXCLUSIVAMENTE con un objeto JSON válido (sin explicaciones fuera del bloque JSON) con la siguiente estructura:
{{
  "traduccion_es": "<traducción final en español fluida y precisa>",
  "traduccion_literal_glosada": "<glosa interlineal morfema por morfema en español>",
  "evidencialidad": "<análisis del matiz de certeza, testimonio, reporte o conjetura>",
  "clusividad": "<análisis de inclusión o exclusión si interviene 1ra plural, o null si no aplica>",
  "justificacion_semantica": "<breve justificación de la acepción seleccionada para cada raíz polisémica y la concordancia de casos>"
}}
"""


COMPACT_PROMPT_TEMPLATE = """Eres un lingüista especialista en lengua quechua (variante Cusco-Collao y Sureño) y traductor profesional al español.
Tu tarea es traducir el siguiente texto en Quechua al Español de forma fluida, idiomática y precisa, apoyándote en el análisis morfo-semántico compacto provisto.

### DIRECTIVAS LINGÜÍSTICAS:
1. EVIDENCIALIDAD: -mi/-n = certeza testimonial directa / indicativo asertivo; -si/-s = reportativo ("dicen que..."); -chá = conjetura ("tal vez...", "quizás...").
2. CLUSIVIDAD: -nchis = nosotros (tú y yo / incluyente); -yku = nosotros (sin ti / excluyente).
3. CASOS Y AFINIDADES: -ta (acusativo/meta), -man (ilativo/hacia), -manta (ablativo/de/desde), -pi (locativo/en), -wan (instrumental/con), -paq (benefactivo/para).
4. REGLA ESTRICTA DE ENTORNO: NO busques en internet ni intentes invocar herramientas externas; traduce directamente a partir del texto y las glosas dadas.
5. TRADUCCIÓN COMPLETA: "traduccion_es" debe estar 100% en español. NUNCA copies palabras quechua sin traducir; si una raíz es dudosa, usa su glosa del andamiaje o la acepción más plausible por contexto.

---
Texto Original Quechua:
"{source_sentence}"

Andamiaje Morfo-Semántico Compacto:
```json
{scaffold_json}
```

---
Responde EXCLUSIVAMENTE con un objeto JSON válido (sin texto extra):
{{
  "traduccion_es": "<traducción final en español fluida, coherente y precisa>",
  "traduccion_literal_glosada": "<glosa interlineal morfema por morfema>",
  "evidencialidad": "<análisis de evidencialidad>",
  "clusividad": "<análisis de clusividad o null>",
  "justificacion_semantica": "<breve justificación semántica y sintáctica>"
}}
"""


def format_scaffold_json(scaffold: Union[Dict[str, Any], str]) -> str:
    """Convierte el scaffold en un string JSON formateado y legible."""
    if isinstance(scaffold, str):
        try:
            parsed = json.loads(scaffold)
            return json.dumps(parsed, indent=2, ensure_ascii=False)
        except Exception:
            return scaffold
    elif hasattr(scaffold, "to_dict"):
        return json.dumps(scaffold.to_dict(), indent=2, ensure_ascii=False)
    elif isinstance(scaffold, dict):
        return json.dumps(scaffold, indent=2, ensure_ascii=False)
    else:
        return str(scaffold)


def build_translation_prompt(source_sentence: str, scaffold: Union[Dict[str, Any], str], compact: bool = False) -> str:
    """
    Construye el prompt completo para el LLM a partir de la oración fuente
    y del Morfo-Semantic Scaffold generado en la Etapa 1.
    """
    scaffold_json_str = format_scaffold_json(scaffold)
    template = COMPACT_PROMPT_TEMPLATE if compact else PROMPT_TEMPLATE
    prompt = template.format(
        source_sentence=source_sentence.strip(),
        scaffold_json=scaffold_json_str
    )
    return prompt
