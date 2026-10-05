---
name: quechua-morphology
description: Descompone palabras y oraciones en quechua en sus raíces léxicas y cadenas de sufijos flexivos, derivacionales y clíticos independientes por ranura morfotáctica.
---

# Runbook: Análisis y Segmentación Morfológica Quechua

Este skill descompone estructuras léxicas aglutinantes complejas en sus formantes mínimos: raíz, alomorfos, ranuras morfotácticas y roles gramaticales.

## Cuándo usar este skill
- Cuando se deba analizar la estructura interna de una palabra compleja (ej. *wasikunamanmi*, *pukllachishankumanpas*).
- Para identificar la raíz canónica antes de consultar un diccionario tradicional.
- Para verificar si una palabra cumple las restricciones de orden morfotáctico (Slots 1 al 9).

## Procedimiento de Ejecución

### Opción A: Vía Antigravity MCP Server
1. Invoca la herramienta MCP:
   ```json
   {
     "name": "quechua_segment",
     "arguments": {
       "text": "wasikunamanmi"
     }
   }
   ```
2. La herramienta devolverá el objeto Morfo-Semantic Scaffold detallando cada token, raíz y secuencia ordenada de afijos.

### Opción B: Vía CLI de Terminal (`qtr`)
Ejecuta en la terminal:
```bash
bin/qtr segment "wasikunamanmi"
```

La terminal desplegará una tabla visual con:
- Token en la superficie.
- Raíz canónica y su categoría gramatical (`s.`, `v.`, etc.).
- Cadena de sufijos desglosada.
- Ranuras morfotácticas y glosas asociadas.
