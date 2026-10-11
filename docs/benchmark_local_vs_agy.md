# Benchmark Lingüístico: Modelos Locales (Ollama) vs. Nube (`agy` / Gemini)

Este documento registra los resultados empíricos, la metodología de evaluación y el análisis lingüístico-computacional comparativo entre el motor generativo en la nube (**Antigravity CLI con Gemini**) y motores locales (**Ollama con Llama 3.2 3B y Qwen 3.5 9.7B**), evaluando la efectividad del **Andamiaje Morfo-Semántico (*Morfo-Semantic Scaffold*)** en la traducción Quechua Sureño / Cusco-Collao → Español.

---

## 1. Entorno de Ejecución y Modelos Evaluados

* **Hardware de Prueba**: Linux x86_64, ejecución de Ollama 100% en CPU (sin aceleración discreta por GPU).
* **Versión de Software**: Ollama Daemon (`http://localhost:11434`), Antigravity CLI (`agy`) headless con sesión autenticada.
* **Arquitectura de Software**: Patrón Puertos y Adaptadores (`TranslationModelPort`, `AgyAdapter`, `OllamaAdapter`, `FallbackAdapter`).

### Modelos en Comparación

| Modelo | Parámetros | Cuantización | Tipo de Arquitectura | Entorno |
| :--- | :--- | :--- | :--- | :--- |
| **Gemini (vía `agy`)** | Gran escala (Nube) | Nativa FP16 | Multimodal / Multilingüe con Thinking | Nube Google |
| **`qwen3.5:9b-q4_K_M`** | 9.7 Billones | Q4_K_M (GGUF) | Denso con Razonamiento Interno (*Thinking*) | Local (CPU) |
| **`llama3.2:3b-instruct-q4_K_M`** | 3.2 Billones | Q4_K_M (GGUF) | Denso Instructivo Puro (sin Thinking) | Local (CPU) |
| **`FallbackAdapter`** | 0 (Determinista) | N/A | Reglas gramaticales y glosas morfotácticas 1..9 | Local (Python) |

---

## 2. Casos de Estudio y Resultados Empíricos

---

### Caso de Estudio 1: Oración con Caso Ilativo, Progresivo, Evidencial y Clusividad

**Texto Quechua**:
> `"Wasikunamanmi purishanchis"`

**Desglose Lingüístico Esperado**:
* **Raíz**: `wasi` (casa / morada común).
* **Sufijos nominales**: `-kuna` (plural) + `-man` (caso ilativo / direccional: "hacia") + `-mi` (validador testimonial directo de primera mano).
* **Raíz verbal**: `puri-` (caminar / desplazarse).
* **Sufijos verbales**: `-sha-` (aspecto durativo/progresivo: "está ...-ndo") + `-nchis` (1ra persona plural **incluyente**: tú y yo juntos).
* **Traducción Prototípica**: *"Estamos caminando hacia las casas"* (o *"Caminamos hacia las casas"* con certeza testimonial).

#### Resultados por Modelo

```text
================================================================================
MOTOR: AGY (Gemini 2.5 Flash / Pro)
================================================================================
┌─ TRADUCCIÓN AL ESPAÑOL [Motor: AGY (gemini-via-agy)]
│  Estamos caminando hacia las casas
└──────────────────────────────────────────────────────────

Análisis Morfo-Semántico:
  • Glosa Interlineal:   casa-PL-ILAT-DIR.EVID caminar-PROG-1.PL.INCL
  • Evidencialidad:      Testimonial / directa (-mi): afirma un hecho presenciado de primera mano con certeza asertiva.
  • Clusividad:          1ra persona plural incluyente (-nchis): incluye explícitamente tanto al hablante como al interlocutor ('nosotros: tú y yo').
  • Justificación:       El lema 'wasi' adopta el sentido prototípico espacial de 'casa/vivienda', pluralizado con '-kuna' y marcado con el caso ilativo/direccional '-man' ('hacia las casas'). La raíz verbal 'puri-' ('caminar/andar/desplazarse') combinada con el aspecto durativo/progresivo '-sha-' (-chka-) y la flexión de primera persona plural inclusiva '-nchis' indica una acción en desarrollo realizada conjuntamente por el hablante y el oyente.

Latencia: ~12 segundos. Calidad: 10/10 (Excelente).
```

```text
================================================================================
MOTOR: OLLAMA (llama3.2:3b-instruct-q4_K_M)
================================================================================
┌─ TRADUCCIÓN AL ESPAÑOL [Motor: OLLAMA (llama3.2:3b-instruct-q4_K_M)]
│  Vamos todos a la casa de las escogidas
└──────────────────────────────────────────────────────────

Análisis Morfo-Semántico:
  • Glosa Interlineal:   {'Wasikunamanmi': 'wasi [s.: (Casa de las escogidas)] -kuna (-numeros) -man (-caso) -mi (-evidencial)', 'purishanchis': 'puri [s.: Locomoción] -sha (-derivativo) -nchis (-clusividad)'}
  • Evidencialidad:      -mi (-certeza testimonial directa / indicativo asertivo)
  • Clusividad:          INCLUSIVO (hablante + oyente)
  • Justificación:       La frase utiliza el sufijo -mi para expresar evidencialidad y clusividad... La palabra 'wasi' se refiere a la casa de las escogidas, mientras que 'puri' se refiere a la locomoción...

Latencia: ~15 segundos. Calidad: 5/10 (Deficiente en desambiguación léxica).
```

```text
================================================================================
MOTOR: OLLAMA (qwen3.5:9b-q4_K_M - Modelo con Thinking)
================================================================================
Traza interna de pensamiento (Thinking Process):
  "Analyze Token 1: Wasikunamanmi.
   Lemma: wasi [s.: (Casa de las escogidas)]. Note: The gloss says [(Casa de las escogidas)],
   which looks like a specific definition or perhaps an error in the prompt's provided lemma...
   However, standard Quechua 'wasi' means house/home...
   -man is illative (towards), -kuna is plural -> 'casas'...
   -nchis is inclusive 1st plural -> 'nosotros (tú y yo)'..."

Resultado: Agotó los tokens asignados en CPU durante la fase de razonamiento y excedió el timeout antes de cerrar el bloque JSON.
Latencia: > 90 segundos.
```

---

### Caso de Estudio 2: Polisemia Contextual y Rol Temático Compuesto

**Texto Quechua**:
> `"Taytayqa uywa hampiqmi"`

**Desglose Lingüístico Esperado**:
* `tayta-y-qa`: "en cuanto a mi padre" (`tayta` = padre; `-y` = 1ra persona posesiva; `-qa` = tópico oracional).
* `uywa`: animal doméstico / ganado (de *uyway*: criar).
* `hampi-q-mi`: curandero / sanador de animales (`hampi` = medicina; `-q` = nominalizador agentivo "el que hace X"; `-mi` = validador directo).
* **Compuesto cultural**: `uywa hampiq` = *veterinario* / *sanador de ganado*.
* **Traducción Prototípica**: *"Mi padre es veterinario"* / *"Mi padre cura al ganado"*.

#### Resultados por Modelo

```text
================================================================================
MOTOR: AGY (Gemini 2.5 Flash / Pro)
================================================================================
┌─ TRADUCCIÓN AL ESPAÑOL [Motor: AGY (gemini-via-agy)]
│  Mi padre es veterinario.
└──────────────────────────────────────────────────────────

Análisis Morfo-Semántico:
  • Glosa Interlineal:   tayta-y-qa (padre-1POS-TOP) uywa (animal/ganado) hampi-q-mi (curar-AG-DIR)
  • Evidencialidad:      Testimonial / directa (-mi): afirma un hecho con plena certeza y constatación de primera mano, traduciéndose en modo indicativo asertivo.
  • Clusividad:          No aplica (no interviene 1ra plural)
  • Justificación:       'Taytayqa' marca el tema ('en cuanto a mi padre'). El compuesto 'uywa hampiq' combina 'uywa' (animal doméstico / ganado) y el nominalizador agentivo 'hampiq' (el que cura / sanador / médico), estructurando la ocupación habitual de 'veterinario'. La cópula es cero en predicados nominales asertivos marcados con el validador testimonial '-mi'.

Latencia: ~11 segundos. Calidad: 10/10 (Excelente).
```

```text
================================================================================
MOTOR: OLLAMA (llama3.2:3b-instruct-q4_K_M)
================================================================================
┌─ TRADUCCIÓN AL ESPAÑOL [Motor: OLLAMA (llama3.2:3b-instruct-q4_K_M)]
│  Todavía estoy cansado  <-- [¡ALUCINACIÓN CATASTRÓFICA!]
└──────────────────────────────────────────────────────────

Análisis Morfo-Semántico:
  • Glosa Interlineal:   {'Taytayqa': 'tayta', 'uywa': 'uywa', 'hampiqmi': 'hampiq'}
  • Evidencialidad:      DIRECTO / ATESTIGUADO (-mi)
  • Clusividad:          No aplica (no interviene 1ra plural)
  • Justificación:       La evidencialidad indica una certeza directa y asertiva, mientras que la ausencia de clusividad sugiere un habla inclusiva (tú y yo)

Latencia: ~12 segundos. Calidad: 1/10 (Alucinación pura).
```

---

## 3. Diagnóstico Técnico y Lingüístico

### 3.1. ¿Por qué brilló `qwen3.5:9b` en razonamiento pero falló en tiempo de ejecución?
1. **Inteligencia Lingüística Real**: El modelo de 9.7B parámetros demostró en su traza de *thinking* que **entiende la semántica profunda del quechua**. Fue capaz de cuestionar la primera acepción del diccionario AMLQ (*"Casa de las escogidas"*) y deducir que en el contexto general debía traducirse como *"casas"*.
2. **Cuello de Botella de Hardware (Inferencia en CPU)**: Al ejecutarse en CPU sin offload GPU, Qwen 3.5 genera a aproximadamente $6.8 \text{ tokens/segundo}$.
3. **La Trampa del Thinking en Ollama**: Los modelos con arquitectura *reasoning* generan entre 400 y 900 tokens de monólogo interno antes de producir el JSON. A 7 tokens/seg, esto consume entre 60 y 130 segundos antes de comenzar a emitir la respuesta visible. Si el parámetro `num_predict` está acotado (ej. 512 tokens), el modelo agota la cuota en pleno pensamiento y retorna un cuerpo vacío.

### 3.2. ¿Por qué alucinó `llama3.2:3b`?
1. **Baja Masa Crítica de Parámetros**: 3.2B de parámetros es insuficiente para lenguas aglutinantes de bajos recursos (*Low-Resource Languages*).
2. **Dependencia Ciega del Texto Literal**: En el Caso 1, copió textualmente la nota enciclopédica del diccionario: *"casa de las escogidas"*.
3. **Ruptura de Atención Cruzada**: En el Caso 2, al no encontrar asociaciones inmediatas en su espacio latente entre *uywa* y su vocabulario habitual, se desenganchó del prompt y generó una frase genérica de su preentrenamiento en español (*"Todavía estoy cansado"*).

### 3.3. El Desempeño de `AGY` (Gemini)
Gemini vía `agy` combina:
1. **Velocidad**: Respuesta completa en 11–13 segundos.
2. **Comprensión Idiomática**: Capacidad de sintetizar conceptos compuestos (*uywa + hampiq = veterinario*) en lugar de traducir mecánicamente palabra por palabra.
3. **Rigor Epistémico**: Respeta con precisión absoluta los requerimientos de validadores testimoniados (`-mi`) y clusividad (`-nchis`).

---

## 4. Conclusiones y Hoja de Ruta para Modelos Locales

1. **El andamiaje morfo-semántico (Etapas 0 y 1) es indispensable**: Sin el scaffold, ningún modelo local (ni Llama ni Qwen) habría sido capaz de identificar que `-nchis` era incluyente o que `-mi` denotaba certeza directa.
2. **Filtrado Prototípico en la Etapa 0**: En palabras polisémicas como *wasi*, la base de datos debe priorizar acepciones contemporáneas y universales (*casa, morada*) por encima de notas históricas o arqueológicas arcaicas (*Acllahuasi*), para no desviar la atención de los modelos locales.
3. **Configuración de Modelos Locales**:
   * Para inferencia en CPU, se recomiendan modelos instructivos directos de 7B a 8B sin bloque de thinking expansivo (ej: `qwen2.5:7b-instruct` o `mistral:7b-instruct`).
   * Para modelos tipo reasoning (Qwen 3.5), se requiere aceleración por GPU para permitir que el proceso de pensamiento ocurra en menos de 3 a 5 segundos.
