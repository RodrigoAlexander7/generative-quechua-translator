"""
Runner de Benchmark Académico Multi-Modelo para Modelos Locales (Ollama / Colab GPU).

Compara modelos locales en dos condiciones experimentales:
1. 'with_tool': Traducción asistida por andamiaje morfo-semántico (Etapa 1).
2. 'without_tool': Traducción directa zero-shot sin herramientas ni andamiaje.

Genera automáticamente:
- JSON consolidado con métricas completas y hardware throughput.
- Tabla comparativa lado a lado (Markdown y CSV).
- Tablas en formato LaTeX (booktabs) listas para Overleaf / Paper.
"""

import os
import sys
import json
import time
import argparse
import csv
from typing import Dict, Any, List, Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.translation.orchestrator import QuechuaTranslator
from src.translation.adapters.ollama_adapter import OllamaAdapter
from benchmark.academic_metrics import (
    compute_sentence_chrf,
    compute_sentence_bleu,
    evaluate_evidentiality_compliance,
    evaluate_clusivity_compliance
)


DEFAULT_MODELS = [
    "llama3.2:3b",
    "llama3.1:8b",
    "qwen2.5:7b",
    "qwen2.5:14b",
    "aya-expanse:8b",
    "deepseek-r1:8b"
]


def run_pure_ollama(
    adapter: OllamaAdapter,
    model: str,
    quechua_text: str,
    timeout: int = 120
) -> Dict[str, Any]:
    """
    Ejecuta traducción pura (zero-shot) mediante Ollama sin andamiaje morfológico.
    """
    prompt = (
        "Eres un traductor experto en la lengua Quechua (variante Cusco-Collao y Sureño).\n"
        "Traduce de forma directa, precisa y natural la siguiente oración al español.\n"
        "NO generes explicaciones, notas, análisis ni etiquetas de pensamiento.\n"
        "Entrega ÚNICAMENTE la traducción final al español.\n\n"
        f"Oración en Quechua: \"{quechua_text}\""
    )

    t0 = time.time()
    try:
        res = adapter.generate(
            prompt=prompt,
            model=model,
            format=None,
            raw_mode=True,
            options={"temperature": 0.1, "num_predict": 512}
        )
        elapsed = round(time.time() - t0, 2)
        trans_text = res.get("traduccion_es", "").strip().strip('"').strip("'")
        # Limpiar posibles saltos o notas
        if "\n" in trans_text:
            lines = [l.strip() for l in trans_text.splitlines() if l.strip()]
            trans_text = lines[0] if lines else trans_text

        return {
            "traduccion_es": trans_text,
            "tiempo_segundos": elapsed,
            "tokens_per_second": res.get("tokens_per_second", 0.0),
            "eval_count": res.get("eval_count", 0),
            "backend": "ollama",
            "model_name": model
        }
    except Exception as e:
        elapsed = round(time.time() - t0, 2)
        return {
            "traduccion_es": f"[ERROR]: {e}",
            "tiempo_segundos": elapsed,
            "tokens_per_second": 0.0,
            "eval_count": 0,
            "backend": "ollama",
            "model_name": model
        }


def run_scaffold_ollama(
    translator: QuechuaTranslator,
    model: str,
    quechua_text: str
) -> Dict[str, Any]:
    """
    Ejecuta traducción asistida por andamiaje morfo-semántico compacto (-L) en Ollama.
    """
    t0 = time.time()
    try:
        res = translator.translate(quechua_text, long_mode=True, model=model)
        elapsed = round(time.time() - t0, 2)
        return {
            "traduccion_es": res.get("traduccion_es", "").strip(),
            "traduccion_literal_glosada": res.get("traduccion_literal_glosada", ""),
            "evidencialidad": res.get("evidencialidad", ""),
            "clusividad": res.get("clusividad"),
            "justificacion_semantica": res.get("justificacion_semantica", ""),
            "tiempo_segundos": elapsed,
            "tokens_per_second": res.get("tokens_per_second", 0.0),
            "eval_count": res.get("eval_count", 0),
            "backend": "ollama",
            "model_name": model
        }
    except Exception as e:
        elapsed = round(time.time() - t0, 2)
        return {
            "traduccion_es": f"[ERROR]: {e}",
            "tiempo_segundos": elapsed,
            "tokens_per_second": 0.0,
            "eval_count": 0,
            "backend": "ollama",
            "model_name": model
        }


def generate_comparison_table_md(dataset_results: List[Dict[str, Any]], models: List[str]) -> str:
    """Genera una tabla comparativa Markdown lado a lado."""
    headers = ["#", "Oración Quechua Collao", "Referencia Humana (ES)"]
    for m in models:
        m_short = m.split(":")[0] + ("-" + m.split(":")[1] if ":" in m else "")
        headers.append(f"{m_short} (Con Tool)")
        headers.append(f"{m_short} (Sin Tool)")

    col_align = [" :---: ", " :--- ", " :--- "] + [" :--- "] * (len(models) * 2)
    lines = [
        "# Comparativa Lado a Lado: Traducciones con y sin Herramienta (Modelos Locales)",
        "",
        "| " + " | ".join(headers) + " |",
        "|" + "|".join(col_align) + "|"
    ]

    for item in dataset_results:
        idx = item["id"]
        q_src = item["quechua_source"].replace("|", "/")
        h_ref = item["spanish_reference"].replace("|", "/")
        row = [str(idx), q_src, h_ref]

        for m in models:
            m_res = item["models"].get(m, {})
            t_with = m_res.get("with_tool", {}).get("traduccion_es", "N/A").replace("|", "/").replace("\n", " ")
            t_without = m_res.get("without_tool", {}).get("traduccion_es", "N/A").replace("|", "/").replace("\n", " ")
            row.append(t_with)
            row.append(t_without)

        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def generate_comparison_csv(dataset_results: List[Dict[str, Any]], models: List[str], output_path: str):
    """Genera el archivo CSV con todas las traducciones lado a lado."""
    fieldnames = ["id", "quechua_source", "spanish_reference"]
    for m in models:
        clean_m = m.replace(":", "_").replace("-", "_")
        fieldnames.append(f"{clean_m}_with_tool")
        fieldnames.append(f"{clean_m}_without_tool")
        fieldnames.append(f"{clean_m}_chrf_with")
        fieldnames.append(f"{clean_m}_chrf_without")

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for item in dataset_results:
            row = {
                "id": item["id"],
                "quechua_source": item["quechua_source"],
                "spanish_reference": item["spanish_reference"]
            }
            for m in models:
                clean_m = m.replace(":", "_").replace("-", "_")
                m_res = item["models"].get(m, {})
                w_tool = m_res.get("with_tool", {})
                wo_tool = m_res.get("without_tool", {})

                row[f"{clean_m}_with_tool"] = w_tool.get("traduccion_es", "")
                row[f"{clean_m}_without_tool"] = wo_tool.get("traduccion_es", "")
                row[f"{clean_m}_chrf_with"] = w_tool.get("metrics", {}).get("chrf", 0.0)
                row[f"{clean_m}_chrf_without"] = wo_tool.get("metrics", {}).get("chrf", 0.0)

            writer.writerow(row)


def generate_latex_table(aggregated: Dict[str, Any], models: List[str]) -> str:
    """Genera la tabla en formato LaTeX booktabs para Overleaf / Paper."""
    lines = [
        "% Tabla generada automáticamente para el Paper",
        "\\begin{table*}[t]",
        "\\centering",
        "\\small",
        "\\begin{tabular}{lcccccc}",
        "\\toprule",
        "\\textbf{Model} & \\textbf{Condition} & \\textbf{chrF++ $\\uparrow$} & \\textbf{BLEU $\\uparrow$} & \\textbf{EPR (\\%) $\\uparrow$} & \\textbf{CAR (\\%) $\\uparrow$} & \\textbf{Latency (s) $\\downarrow$} \\\\",
        "\\midrule"
    ]

    for m in models:
        stats = aggregated.get(m, {})
        with_s = stats.get("with_tool", {})
        without_s = stats.get("without_tool", {})

        m_name = m.replace("_", "\\_").replace(":", " ")
        lines.append(f"\\multirow{{2}}{{*}}{{{m_name}}} & \\textit{{w/o Tool}} & {without_s.get('mean_chrf', 0.0):.2f} & {without_s.get('mean_bleu', 0.0):.2f} & {without_s.get('epr_percent', 0.0):.1f}\\% & {without_s.get('car_percent', 0.0):.1f}\\% & {without_s.get('mean_latency', 0.0):.2f}s \\\\")
        lines.append(f" & \\textbf{{w/ Scaffold (Ours)}} & \\textbf{{{with_s.get('mean_chrf', 0.0):.2f}}} & \\textbf{{{with_s.get('mean_bleu', 0.0):.2f}}} & \\textbf{{{with_s.get('epr_percent', 0.0):.1f}\\%}} & \\textbf{{{with_s.get('car_percent', 0.0):.1f}\\%}} & {with_s.get('mean_latency', 0.0):.2f}s \\\\")
        lines.append("\\midrule")

    # Quitar última midrule y poner bottomrule
    lines[-1] = "\\bottomrule"
    lines.append("\\end{tabular}")
    lines.append("\\caption{Comparative evaluation of open-weight LLMs on Quechua Collao translation with and without morpho-semantic scaffolding. chrF++ and BLEU are evaluated against human reference translations. EPR denotes Evidentiality Preservation Rate; CAR denotes Clusivity Accuracy Rate.}")
    lines.append("\\label{tab:local_models_benchmark}")
    lines.append("\\end{table*}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Multi-Model Local Benchmark Runner (Ollama / Colab)")
    parser.add_argument("--models", type=str, default=",".join(DEFAULT_MODELS),
                        help="Modelos separados por coma a evaluar (ej. llama3.2:3b,qwen2.5:7b)")
    parser.add_argument("--dataset", type=str, default="benchmark/dataset.json",
                        help="Ruta al archivo dataset.json")
    parser.add_argument("--start", type=int, default=0, help="Índice inicial")
    parser.add_argument("--end", type=int, default=None, help="Índice final exclusivo")
    parser.add_argument("--ollama-host", type=str, default=None, help="Host de Ollama (ej. http://localhost:11434)")
    parser.add_argument("--output-dir", type=str, default="data/benchmark_results", help="Directorio de salida")
    args = parser.parse_args()

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    os.makedirs(args.output_dir, exist_ok=True)
    docs_dir = os.path.join(REPO_ROOT, "docs")
    os.makedirs(docs_dir, exist_ok=True)

    with open(args.dataset, "r", encoding="utf-8") as f:
        full_dataset = json.load(f)

    end_idx = args.end if args.end is not None else len(full_dataset)
    subset = full_dataset[args.start:end_idx]

    print(f"\n{'='*70}")
    print(f"[*] INICIANDO BENCHMARK MULTI-MODELO (ACADÉMICO)")
    print(f"[*] Oraciones a evaluar: {len(subset)} (índices {args.start} a {end_idx-1})")
    print(f"[*] Modelos seleccionados: {models}")
    print(f"{'='*70}\n")

    adapter = OllamaAdapter(host=args.ollama_host)
    translator = QuechuaTranslator(adapter=adapter)

    # Verificar conectividad con Ollama
    if not adapter.is_available():
        print(f"[!] ADVERTENCIA: No se pudo conectar a Ollama en {adapter.host}.")
        print("[!] Asegúrate de que Ollama esté corriendo con 'ollama serve'.")

    available_models = adapter.get_available_models()
    print(f"[*] Modelos presentes en el servidor Ollama: {available_models}\n")

    results_data = []

    for i, item in enumerate(subset):
        idx = item["id"]
        q_src = item["quechua"]
        sp_ref = item["spanish"]

        print(f"[{i+1}/{len(subset)}] Evaluando #{idx:03d}: '{q_src[:45]}...'")

        item_result = {
            "id": idx,
            "quechua_source": q_src,
            "spanish_reference": sp_ref,
            "models": {}
        }

        for model in models:
            print(f"    -> Modelo: {model}")

            # 1. Condición 'with_tool' (Andamiaje morfo-semántico compacto)
            with_res = run_scaffold_ollama(translator, model, q_src)
            chrf_with = compute_sentence_chrf(with_res["traduccion_es"], sp_ref)
            bleu_with = compute_sentence_bleu(with_res["traduccion_es"], sp_ref)
            evid_with = evaluate_evidentiality_compliance(q_src, with_res["traduccion_es"], with_res.get("evidencialidad"))
            clus_with = evaluate_clusivity_compliance(q_src, with_res["traduccion_es"], with_res.get("clusividad"))

            with_res["metrics"] = {
                "chrf": chrf_with,
                "bleu": bleu_with,
                "evidentiality": evid_with,
                "clusivity": clus_with
            }

            # 2. Condición 'without_tool' (Directo / Zero-shot)
            without_res = run_pure_ollama(adapter, model, q_src)
            chrf_wo = compute_sentence_chrf(without_res["traduccion_es"], sp_ref)
            bleu_wo = compute_sentence_bleu(without_res["traduccion_es"], sp_ref)
            evid_wo = evaluate_evidentiality_compliance(q_src, without_res["traduccion_es"], None)
            clus_wo = evaluate_clusivity_compliance(q_src, without_res["traduccion_es"], None)

            without_res["metrics"] = {
                "chrf": chrf_wo,
                "bleu": bleu_wo,
                "evidentiality": evid_wo,
                "clusivity": clus_wo
            }

            item_result["models"][model] = {
                "with_tool": with_res,
                "without_tool": without_res
            }

            print(f"       [With Tool] chrF++: {chrf_with:.1f} | Latencia: {with_res['tiempo_segundos']}s")
            print(f"       [No Tool]   chrF++: {chrf_wo:.1f} | Latencia: {without_res['tiempo_segundos']}s")

        results_data.append(item_result)

    # ---------------------------------------------------------
    # Calcular Métricas Agregadas para el Paper
    # ---------------------------------------------------------
    aggregated_stats = {}
    for m in models:
        aggregated_stats[m] = {
            "with_tool": {"chrf": [], "bleu": [], "latency": [], "tps": [], "evid_ok": 0, "clus_ok": 0, "total": 0},
            "without_tool": {"chrf": [], "bleu": [], "latency": [], "tps": [], "evid_ok": 0, "clus_ok": 0, "total": 0}
        }

    for item in results_data:
        for m in models:
            m_data = item["models"].get(m, {})
            # with_tool
            w = m_data.get("with_tool", {})
            aggregated_stats[m]["with_tool"]["chrf"].append(w.get("metrics", {}).get("chrf", 0.0))
            aggregated_stats[m]["with_tool"]["bleu"].append(w.get("metrics", {}).get("bleu", 0.0))
            aggregated_stats[m]["with_tool"]["latency"].append(w.get("tiempo_segundos", 0.0))
            aggregated_stats[m]["with_tool"]["tps"].append(w.get("tokens_per_second", 0.0))
            if w.get("metrics", {}).get("evidentiality", {}).get("is_compliant"):
                aggregated_stats[m]["with_tool"]["evid_ok"] += 1
            if w.get("metrics", {}).get("clusivity", {}).get("is_compliant"):
                aggregated_stats[m]["with_tool"]["clus_ok"] += 1
            aggregated_stats[m]["with_tool"]["total"] += 1

            # without_tool
            wo = m_data.get("without_tool", {})
            aggregated_stats[m]["without_tool"]["chrf"].append(wo.get("metrics", {}).get("chrf", 0.0))
            aggregated_stats[m]["without_tool"]["bleu"].append(wo.get("metrics", {}).get("bleu", 0.0))
            aggregated_stats[m]["without_tool"]["latency"].append(wo.get("tiempo_segundos", 0.0))
            aggregated_stats[m]["without_tool"]["tps"].append(wo.get("tokens_per_second", 0.0))
            if wo.get("metrics", {}).get("evidentiality", {}).get("is_compliant"):
                aggregated_stats[m]["without_tool"]["evid_ok"] += 1
            if wo.get("metrics", {}).get("clusivity", {}).get("is_compliant"):
                aggregated_stats[m]["without_tool"]["clus_ok"] += 1
            aggregated_stats[m]["without_tool"]["total"] += 1

    summary_final = {}
    for m, conds in aggregated_stats.items():
        summary_final[m] = {}
        for c_name, c_vals in conds.items():
            tot = c_vals["total"] or 1
            summary_final[m][c_name] = {
                "mean_chrf": round(sum(c_vals["chrf"]) / tot, 2),
                "mean_bleu": round(sum(c_vals["bleu"]) / tot, 2),
                "mean_latency": round(sum(c_vals["latency"]) / tot, 2),
                "mean_tps": round(sum(c_vals["tps"]) / tot, 2),
                "epr_percent": round((c_vals["evid_ok"] / tot) * 100.0, 1),
                "car_percent": round((c_vals["clus_ok"] / tot) * 100.0, 1),
                "total_samples": tot
            }

    # ---------------------------------------------------------
    # Guardar Artefactos
    # ---------------------------------------------------------
    json_path = os.path.join(args.output_dir, "multi_model_benchmark.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary_final, "results": results_data}, f, ensure_ascii=False, indent=2)

    # 1. Tabla de traducciones en Markdown
    table_md = generate_comparison_table_md(results_data, models)
    table_md_path = os.path.join(args.output_dir, "translations_comparison_table.md")
    with open(table_md_path, "w", encoding="utf-8") as f:
        f.write(table_md)

    # 2. Tabla de traducciones en CSV
    csv_path = os.path.join(args.output_dir, "translations_comparison_table.csv")
    generate_comparison_csv(results_data, models, csv_path)

    # 3. Tablas en LaTeX para el Paper
    latex_table = generate_latex_table(summary_final, models)
    latex_path = os.path.join(docs_dir, "paper_tables.tex")
    with open(latex_path, "w", encoding="utf-8") as f:
        f.write(latex_table)

    print(f"\n{'='*70}")
    print("[+] BENCHMARK FINALIZADO CON ÉXITO")
    print(f"[+] Archivo JSON completo: {json_path}")
    print(f"[+] Tabla comparativa Markdown: {table_md_path}")
    print(f"[+] Tabla comparativa CSV: {csv_path}")
    print(f"[+] Tablas LaTeX para Paper: {latex_path}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
