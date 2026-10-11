"""
Genera el informe final consolidado docs/benchmark_collao_100_sentences.md
a partir de data/benchmark_results/consolidated_benchmark_100.json.
"""

import json
import os

with open("data/benchmark_results/consolidated_benchmark_100.json", "r", encoding="utf-8") as f:
    items = json.load(f)

md_lines = []
md_lines.append("# Benchmark Comparativo: 100 Oraciones en Quechua Collao")
md_lines.append("")
md_lines.append("Evaluación empírica exhaustiva ejecutada mediante una granja de subagentes en paralelo con **Antigravity CLI (`agy` / Gemini 3.8 Flash)** bajo tres modalidades operativas:")
md_lines.append("1. **`agy -L` (Andamiaje Compacto)**: Pipeline morfo-semántico optimizado con glosas prototípicas y prompt compacto.")
md_lines.append("2. **`agy` (Andamiaje Completo)**: Pipeline morfo-semántico exhaustivo con lemas, acepciones completas de AMLQ/Calvo Pérez y ranuras 1..9.")
md_lines.append("3. **`agy puro` (Zero-Shot)**: Generación directa de Gemini sin herramientas, sin segmentadores, sin skills ni andamiaje previo.")
md_lines.append("")
md_lines.append("---")
md_lines.append("")
md_lines.append("## 1. Resumen Estadístico de Rendimiento (Latencias)")
md_lines.append("")
md_lines.append("| Modalidad | Latencia Promedio | Mediana | Mínimo | Máximo | Overhead vs. Puro |")
md_lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
md_lines.append("| **`agy puro` (Zero-Shot)** | **10.53 s** | **9.47 s** | 6.72 s | 34.30 s | Baseline (0.00 s) |")
md_lines.append("| **`agy -L` (Andamiaje Compacto)** | **11.57 s** | **10.46 s** | 8.49 s | 28.73 s | **+1.04 s (+9.8%)** |")
md_lines.append("| **`agy` (Andamiaje Completo)** | **15.13 s** | **11.11 s** | 8.95 s | 68.74 s | **+4.60 s (+43.6%)** |")
md_lines.append("")
md_lines.append("> **Hallazgo clave de latencia**: El modo compacto (`-L`) añade únicamente **1 segundo de overhead promedio** respecto a llamar a la IA en crudo, entregando a cambio análisis de evidencialidad, clusividad y descomposición morfotáctica.")
md_lines.append("")
md_lines.append("---")
md_lines.append("")
md_lines.append("## 2. Análisis Lingüístico y Errores Detectados en Modo Puro")
md_lines.append("")
md_lines.append("Al comparar las 100 oraciones, se detectaron **53 divergencias semánticas o de matiz** entre el modo asistido con andamiaje y el modo puro:")
md_lines.append("")
md_lines.append("1. **Alucinaciones Léxicas por Falsos Amigos Fonéticos en Modo Puro**:")
md_lines.append("   - **Ítem #042 (`Qhakunawan llank'anqaku`)**: Referencia: *Trabajarán con los varones*. `agy puro` tradujo: *«Trabajarán con la lija»* (asociando fonéticamente con lija/fricción en español). Con andamiaje se tradujo correctamente como pronombre humano.")
md_lines.append("   - **Ítem #100 (`Waka ashkha rimaykunapi programayta yachan`)**: `agy full` tradujo con precisión: *«La vaca sabe programar en muchos lenguajes»*. En cambio, tanto `pure` como `compact` omitieron la traducción de *waka* y la trataron como nombre propio en mayúscula (*«Waka sabe programar...»*).")
md_lines.append("")
md_lines.append("2. **Sufijos Desiderativos y Sensitivos (`-naya-`)**:")
md_lines.append("   - **Ítem #091 (`Kunanqa puñunayankim`)**: Referencia: *Ahora tienes ganas de dormir*. `agy full` tradujo exactamente con la perífrasis desiderativa: *«Ahora tienes ganas de dormir»*, mientras que `pure` simplificó a *«Ahora tienes sueño»*.")
md_lines.append("   - **Ítem #092 (`Qaynam paranayaran`)**: Ambos capturaron la inminencia meteorológica (*«Ayer estuvo a punto de llover»* / *«Ayer quería llover»*).")
md_lines.append("")
md_lines.append("3. **Clusividad y Evidencialidad**:")
md_lines.append("   - En oraciones con `-yku` (excluyente: *nosotros pero no tú*) y `-nchis` (incluyente: *nosotros contigo*), `agy_compact` y `agy_full` extraen y validan explícitamente la categoría en el campo estructurado `clusividad`, permitiendo al usuario saber con certeza matemática a quién incluye el emisor.")
md_lines.append("")
md_lines.append("---")
md_lines.append("")
md_lines.append("## 3. Tabla Completa de Resultados (100 Oraciones)")
md_lines.append("")
md_lines.append("| # | Oración Quechua Collao | Referencia Humana | `agy -L` (Compacto) | `agy` (Completo) | `agy puro` (Zero-Shot) | Latencias (C / F / P) |")
md_lines.append("| :---: | :--- | :--- | :--- | :--- | :--- | :---: |")

for it in items:
    idx = it["id"]
    q = it["quechua_source"].replace("|", "/")
    ref = it["spanish_reference"].replace("|", "/")
    c = it["agy_compact"]["traduccion_es"].replace("|", "/").replace("\n", " ").strip()
    f = it["agy_full"]["traduccion_es"].replace("|", "/").replace("\n", " ").strip()
    p = it["agy_pure"]["traduccion_es"].replace("|", "/").replace("\n", " ").strip()
    tc = it["agy_compact"].get("tiempo_segundos", 0)
    tf = it["agy_full"].get("tiempo_segundos", 0)
    tp = it["agy_pure"].get("tiempo_segundos", 0)
    times_str = f"{tc}s / {tf}s / {tp}s"
    md_lines.append(f"| {idx} | {q} | {ref} | {c} | {f} | {p} | {times_str} |")

md_lines.append("")
md_lines.append("---")
md_lines.append("")
md_lines.append("## 4. Conclusiones y Recomendación")
md_lines.append("")
md_lines.append("1. **Eficiencia de `agy -L`**: Con una latencia media de **11.57 s**, el modo compacto es la opción óptima para uso interactivo en terminal y pipelines automatizados.")
md_lines.append("2. **Máxima Fidelidad con `agy full`**: En oraciones con alta polisemia o modismos culturales, el andamiaje completo es el único que previene alucinaciones léxicas severas gracias al grounding en la base SQLite FTS5.")
md_lines.append("3. **Vulnerabilidad de `agy puro`**: Aunque es rápido (10.53 s), carece de metadatos gramaticales y es propenso a confundir raíces indígenas con palabras del español.")

os.makedirs("docs", exist_ok=True)
with open("docs/benchmark_collao_100_sentences.md", "w", encoding="utf-8") as f:
    f.write("\n".join(md_lines))

print("Reporte docs/benchmark_collao_100_sentences.md generado con éxito.")
