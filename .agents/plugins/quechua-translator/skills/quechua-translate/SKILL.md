---
name: quechua-translate
description: Traduce oraciones y textos en lengua Quechua al Español utilizando el pipeline de andamiaje morfo-semántico y modelos generativos, preservando evidencialidad y clusividad.
---

# Runbook: Traducción Contextual Quechua -> Español

Este skill guía al agente o usuario en la traducción precisa de expresiones y textos en Quechua (variante Cusco-Collao y Quechua Sureño).

## Cuándo usar este skill
- Cuando el usuario solicite traducir una oración, frase o párrafo de Quechua a Español.
- Cuando se requiera una traducción certificada que preserve las categorías gramaticales andinas (evidencialidad testimonial, reportativa o conjetural, y clusividad en primera persona plural).

## Procedimiento de Ejecución

### Opción A: Vía Antigravity MCP Server
1. Invoca la herramienta MCP:
   ```json
   {
     "name": "quechua_translate",
     "arguments": {
       "text": "Wasikunapim tiyashanku."
     }
   }
   ```
2. La herramienta devolverá un JSON con:
   - `traduccion_es`: La traducción idiomática en español.
   - `traduccion_literal_glosada`: La glosa interlineal morfema por morfema.
   - `evidencialidad`: Clasificación epistémica (`-mi`, `-si`, `-chá`).
   - `clusividad`: Inclusión/exclusión (`-nchis` vs `-yku`).
   - `justificacion_semantica`: Razonamiento de selección de acepciones.

### Opción B: Vía CLI de Terminal (`qtr`)
Ejecuta en la terminal:
```bash
bin/qtr translate "Wasikunapim tiyashanku."
```
O con salida estructurada en formato JSON:
```bash
bin/qtr translate "Wasikunapim tiyashanku." --json
```

## Validación de Resultados
Al presentar la traducción al usuario:
1. Muestra la traducción final fluida en español.
2. Explica la fuente del conocimiento codificada por el evidencial (ej. si usó `-si`, aclara que es un reporte o testimonio de terceros: *"según dicen"*).
3. Si la oración involucra primera persona plural, destaca si el oyente está incluido o excluido.
