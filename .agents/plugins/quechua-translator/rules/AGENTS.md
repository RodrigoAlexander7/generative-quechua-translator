# Directivas Lingüísticas de Quechua para Antigravity (`agy`)

Al interactuar con textos en lengua Quechua o traducir entre Quechua y Español, el agente DEBE seguir de forma obligatoria las siguientes directivas:

## 1. Obligación de Segmentación Morfo-Semántica
- **Herramienta Obligatoria**: Antes de responder o proponer una traducción al usuario, invoca SIEMPRE la herramienta MCP `quechua_segment` o ejecuta `qtr segment "<oración>"`.
- **Prohibición de Alucinación**: Jamás adivines la raíz léxica ni traduzcas una palabra larga como si fuera una sola entidad atómica. El quechua es aglutinante y exclusivamente sufijante; una sola palabra puede contener una raíz y hasta 7 sufijos encadenados.

## 2. Rigor Epistémico en Evidencialidad (Validadores)
El quechua codifica gramaticalmente la fuente del conocimiento y la certeza epistémica. Un error en evidencialidad invalida la traducción:
- **-mi / -n (Evidencial Testimonial / Directo)**: Traduce en modo indicativo asertivo directo ("él come", "ciertamente"). Indica que al hablante le consta de primera mano.
- **-si / -s (Evidencial Reportativo / Testimonio Indirecto)**: DEBES anteponer o indicar explícitamente "dicen que...", "según cuentan...", "se dice que...".
- **-chá (Evidencial Conjetural / Duditativo)**: DEBES reflejar conjetura o duda epistémica ("tal vez...", "quizás...", "probablemente...").

## 3. Clusividad Pronominal en 1ra Persona Plural
El quechua distingue estrictamente entre:
- **-nchis / ñoqanchis (Incluyente)**: Nosotros (incluyendo al oyente / "tú y yo").
- **-yku / ñoqayku (Excluyente)**: Nosotros (pero no tú / excluyendo al oyente).
El agente debe explicitar o preservar esta distinción en el análisis.

## 4. Mapeo Canónico de Casos y Roles Temáticos
- **-ta**: Objeto directo (acusativo) o meta de movimiento ("a", "hacia").
- **-man**: Ilativo / direccional ("hacia", "a"), destinatario u objeto indirecto.
- **-manta**: Procedencia / origen ("de", "desde") o materia ("hecho de").
- **-pi**: Locativo ("en", "sobre", "dentro de").
- **-wan**: Instrumental ("con", "mediante") o compañía ("en compañía de").
- **-paq**: Benefactivo ("para", "en beneficio de").

## 5. Desambiguación de Polisemia
Palabras de alta polisemia (como *wasi*, que posee más de 20 acepciones registradas: casa, templo, cárcel, nido, familia, etc.) no deben traducirse automáticamente con su primera entrada. El agente debe contrastar los argumentos del predicado verbal y seleccionar la acepción contextualmente apropiada, justificando la elección en la salida.
