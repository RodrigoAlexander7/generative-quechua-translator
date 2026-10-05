---
name: quechua-search
description: Búsqueda rápida de lemas polisémicos, definiciones, ejemplos contextuales y taxonomía de sufijos en los corpus lingüísticos del Quechua Cusco-Collao.
---

# Runbook: Búsqueda Léxica y Catálogo de Sufijos Quechua

Este skill permite realizar consultas exactas y de texto completo (FTS5) sobre el vocabulario quechua y la base de datos de 245 sufijos.

## Cuándo usar este skill
- Cuando se requiera conocer todas las acepciones de una palabra polisémica (ej. *wasi*, *allpa*, *tiyay*).
- Para consultar la definición, categoría funcional y ejemplos de uso de un sufijo gramatical (ej. *-kuna*, *-manta*, *-sha*, *-nchis*).
- Para revisar ejemplos oracionales auténticos registrados en las fuentes académicas (AMLQ y Julio Calvo Pérez).

## Procedimiento de Ejecución

### Opción A: Búsqueda de Lemas y Acepciones
- **Vía MCP**:
  ```json
  {
    "name": "quechua_lookup",
    "arguments": {
      "word": "wasi"
    }
  }
  ```
- **Vía CLI de Terminal**:
  ```bash
  bin/qtr lookup wasi
  ```

### Opción B: Consulta de Sufijos
- **Vía MCP**:
  ```json
  {
    "name": "quechua_suffix",
    "arguments": {
      "suffix": "kuna"
    }
  }
  ```
- **Vía CLI de Terminal**:
  ```bash
  bin/qtr suffix kuna
  ```

## Salida Esperada
- Para lemas: Categoría gramatical, variantes regionales (`Pe.Aya:`, `Bol:`, etc.), sinónimos, listado completo de acepciones numeradas y oraciones de ejemplo.
- Para sufijos: Ranura morfotáctica (Slots 1 a 9), tipo/subtipo (flexivo, derivacional, clítico), descripción gramatical detallada y ejemplos con su traducción al español.
