# Generative Quechua Translator (QTR)

Sistema de traducción generativa Quechua ↔ Español con arquitectura desacoplada en tres etapas: **Indexación y Preparación (Etapa 0)**, **Segmentación Morfo-Semántica Determinista (Etapa 1)** y **Traducción Generativa Guiada (Etapa 2)**. Empaquetado como herramienta de terminal y plugin nativo para **Antigravity CLI (`agy`)**.

---

## 🚀 Inicio Rápido

### 1. Requisitos
- Python 3.9+ (sin dependencias C externas; utiliza la librería estándar y SQLite FTS5).

### 2. Construir la Base de Conocimiento (Etapa 0)
Ingesta automáticamente los diccionarios (AMLQ y fuentes) y el catálogo taxonómico de sufijos en `data/quechua_knowledge.db`:

```bash
bin/qtr index
```

### 3. Ejecutar Pruebas Unitarias
```bash
python3 -m unittest discover tests
```

---

## 🛠️ Comandos de Terminal (`bin/qtr`)

El ejecutable `bin/qtr` provee una interfaz enriquecida con colores ANSI:

### Búsqueda de Lemas y Acepciones (Resuelve Polisemia)
```bash
bin/qtr lookup wasi
bin/qtr lookup allpaqa
```

### Consulta de Sufijos y Morfotaxis
```bash
bin/qtr suffix kuna
bin/qtr suffix manta
bin/qtr suffix mi
```

### Segmentación Morfológica por Ranura (Etapa 1)
Desprende sufijos de derecha a izquierda, valida las ranuras morfotácticas canónicas (1..9), resuelve el morfema eufónico `-ni-`, y normaliza variaciones pentavocálicas/trivocálicas:
```bash
bin/qtr segment "wasikunamanmi"
bin/qtr segment "Taytayqa uywa hampiqmi"
bin/qtr segment "pukllashanchis"
```

### Traducción Generativa Asistida (Etapa 2)
Ensambla el andamiaje morfo-semántico (*Morfo-Semantic Scaffold*) con las definiciones de los lemas y las funciones de los sufijos, obligando al modelo a respetar evidenciales y clusividad:
```bash
bin/qtr translate "Taytayqa uywa hampiqmi"
```

---

## 🧩 Integración con Antigravity (`agy`)

El proyecto incluye un **Plugin de Workspace** completo en `.agents/plugins/quechua-translator/`:

1. **Servidor MCP Nativo (`src/mcp_server.py`)**:
   Registrado en `mcp_config.json` vía transporte Stdio, expone 4 herramientas directas al agente:
   - `quechua_segment`: Segmentación morfológica determinista en raíces, sufijos y ranuras.
   - `quechua_lookup`: Consulta en SQLite FTS5 de acepciones, dominios semánticos y ejemplos bilingües.
   - `quechua_suffix`: Consulta taxonómica y fonotáctica de sufijos.
   - `quechua_translate`: Pipeline completo de traducción generativa asistida.

2. **Reglas de Comportamiento (`AGENTS.md`)**:
   Directivas activas que prohíben la alucinación léxica y exigen el uso del segmentador y el respeto a:
   - **Evidenciales**: `-mi` (testimonial directo), `-si` (reportativo: "dicen que..."), `-chá` (conjetural: "tal vez...").
   - **Clusividad**: `-nchis` (inclusivo: nosotros contigo) vs `-yku` (exclusivo: nosotros sin ti).
   - **Casos Nominales**: Mapeo estricto de `-ta` (acusativo/meta), `-man` (ilativo), `-manta` (ablativo), `-pi` (locativo), `-wan` (instrumental/comitativo), `-paq` (benefactivo).

3. **Skills Especializados (`skills/`)**:
   - `quechua-translate`: Runbook para traducción de oraciones y párrafos complejos.
   - `quechua-morphology`: Runbook para análisis lingüístico formal y verificación de ranuras.
   - `quechua-search`: Runbook para búsqueda rápida en diccionarios y catálogo morfológico.

---

## 📂 Estructura del Proyecto

```text
generative-quechua-translator/
├── AGENTS.md                                    # Directivas lingüísticas del agente en el workspace
├── bin/
│   └── qtr                                      # CLI ejecutable de terminal
├── data/
│   └── quechua_knowledge.db                     # Base de datos SQLite FTS5 (Etapa 0)
├── docs/
│   └── architecture_and_agy_plugin_design.md   # Especificación de arquitectura técnica
├── input/
│   ├── dictionaries/                            # PDFs originales (AMLQ y Calvo Pérez)
│   ├── paqocha-fst/                             # Recursos previos y entries.json (13,750 entradas)
│   └── sufix/                                   # suffixes - V3.0.csv (148 sufijos estructurados)
├── src/
│   ├── cli.py                                   # Interfaz CLI con formato ANSI
│   ├── mcp_server.py                            # Servidor MCP Stdio para Antigravity
│   ├── storage/
│   │   └── db.py                                # Capa relacional SQLite FTS5 y B-Tree
│   ├── indexer/
│   │   ├── entry_parser.py                      # Parser léxico con resolución de polisemia
│   │   ├── suffix_parser.py                     # Parser taxonómico de sufijos
│   │   └── build_db.py                          # Script de ingesta y generación de la base de datos
│   ├── segmentation/
│   │   ├── normalizer.py                        # Normalización fonética y pentavocálica/trivocálica
│   │   ├── slots.py                             # Restricciones morfotácticas de ranuras (1..9)
│   │   ├── peeler.py                            # Algoritmo de Morpheme Peeling R2L en Python puro
│   │   └── scaffold.py                          # Constructor del Scaffold Morfo-Semántico
│   └── translation/
│       ├── prompt_templates.py                  # Plantillas de prompt con directivas lingüísticas
│       └── orchestrator.py                      # Orquestador generativo (Gemini + Fallback)
├── tests/
│   └── test_segmentation.py                     # Batería de pruebas unitarias
└── .agents/
    └── plugins/
        └── quechua-translator/                  # Bundle del Plugin de AGY
            ├── plugin.json                      # Manifiesto
            ├── mcp_config.json                  # Configuración MCP Stdio
            ├── rules/AGENTS.md                  # Reglas del plugin
            └── skills/                          # Skills ejecutables por el agente
```
