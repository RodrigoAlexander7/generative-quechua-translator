"""
Ejecutor de Benchmark: Evaluación comparativa de 3 métodos con agy:
1. agy_compact: agy con andamiaje morfo-semántico compacto (-L)
2. agy_full: agy con andamiaje morfo-semántico completo
3. agy_pure: agy directo (zero-shot, sin andamiaje, sin herramientas ni skills)

Mide con precisión el tiempo de ejecución (latencia en segundos) de cada método.
"""

import os
import sys
import json
import time
import subprocess
import argparse
from typing import Dict, Any, List

# Asegurar path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.translation.orchestrator import QuechuaTranslator


def run_agy_pure(quechua_text: str) -> Dict[str, Any]:
    """
    Ejecuta traducción pura con agy sin andamiaje morfológico.
    Fuerza el no uso de herramientas ni habilidades externas.
    """
    prompt = (
        "REGLA ESTRICTA DE MODO PURO:\n"
        "Eres un traductor experto en la variante Quechua Collao (Cusco-Collao / Quechua Sureño).\n"
        "NO uses ninguna herramienta externa ni ejecutes comandos en terminal.\n"
        "NO invoques segmentación ni busques en la web.\n"
        "Traduce directamente desde tus pesos y memoria interna la siguiente oración quechua collao al español.\n\n"
        f"Oración en Quechua Collao: \"{quechua_text}\"\n\n"
        "Responde ÚNICAMENTE con la traducción en español, sin explicaciones, comillas ni texto adicional."
    )
    cmd = [
        "agy",
        "--dangerously-skip-permissions",
        "--disable-slash-commands",
        "--effort", "low",
        "-p", prompt
    ]

    t0 = time.time()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        elapsed = round(time.time() - t0, 2)
        if proc.returncode == 0:
            text = proc.stdout.strip().strip('"').strip("'")
            return {"traduccion_es": text, "tiempo_segundos": elapsed}
        return {"traduccion_es": f"[ERROR {proc.returncode}]: {proc.stderr.strip()}", "tiempo_segundos": elapsed}
    except Exception as e:
        elapsed = round(time.time() - t0, 2)
        return {"traduccion_es": f"[EXCEPTION]: {e}", "tiempo_segundos": elapsed}


def evaluate_single_item(item: Dict[str, Any], translator: QuechuaTranslator) -> Dict[str, Any]:
    """Evalúa un item bajo los tres métodos y cronometra cada uno."""
    idx = item["id"]
    spanish_ref = item["spanish"]
    quechua_src = item["quechua"]

    print(f"[*] Evaluando #{idx:03d}: '{quechua_src}'...")

    # 1. agy -L (con andamiaje compacto)
    t0 = time.time()
    try:
        res_compact = translator.translate(quechua_src, long_mode=True)
        time_compact = round(time.time() - t0, 2)
        trans_compact = res_compact.get("traduccion_es", "")
        evid_compact = res_compact.get("evidencialidad", "")
        clus_compact = res_compact.get("clusividad")
    except Exception as e:
        time_compact = round(time.time() - t0, 2)
        trans_compact = f"[ERROR]: {e}"
        evid_compact = ""
        clus_compact = None

    # 2. agy (con andamiaje completo)
    t0 = time.time()
    try:
        res_full = translator.translate(quechua_src, long_mode=False)
        time_full = round(time.time() - t0, 2)
        trans_full = res_full.get("traduccion_es", "")
        evid_full = res_full.get("evidencialidad", "")
        clus_full = res_full.get("clusividad")
    except Exception as e:
        time_full = round(time.time() - t0, 2)
        trans_full = f"[ERROR]: {e}"
        evid_full = ""
        clus_full = None

    # 3. agy puro (sin andamiaje ni herramientas)
    pure_res = run_agy_pure(quechua_src)
    trans_pure = pure_res.get("traduccion_es", "")
    time_pure = pure_res.get("tiempo_segundos", 0.0)

    print(f"    [#{idx:03d}] Compact: {time_compact}s | Full: {time_full}s | Pure: {time_pure}s")

    return {
        "id": idx,
        "spanish_reference": spanish_ref,
        "quechua_source": quechua_src,
        "agy_compact": {
            "traduccion_es": trans_compact,
            "tiempo_segundos": time_compact,
            "evidencialidad": evid_compact,
            "clusividad": clus_compact
        },
        "agy_full": {
            "traduccion_es": trans_full,
            "tiempo_segundos": time_full,
            "evidencialidad": evid_full,
            "clusividad": clus_full
        },
        "agy_pure": {
            "traduccion_es": trans_pure,
            "tiempo_segundos": time_pure
        }
    }


def main():
    parser = argparse.ArgumentParser(description="Runner de benchmark comparativo agy")
    parser.add_argument("--start", type=int, default=0, help="Índice inicial (0-indexed)")
    parser.add_argument("--end", type=int, default=100, help="Índice final exclusivo")
    parser.add_argument("--dataset", type=str, default="benchmark/dataset.json", help="Ruta al dataset")
    parser.add_argument("--output", type=str, default="data/benchmark_results/results.json", help="Ruta salida")
    args = parser.parse_args()

    with open(args.dataset, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    sub_dataset = dataset[args.start:args.end]
    print(f"[+] Iniciando evaluación de {len(sub_dataset)} oraciones (del índice {args.start} al {args.end-1})...")

    translator = QuechuaTranslator(use_agy=True)
    results = []

    for it in sub_dataset:
        try:
            res = evaluate_single_item(it, translator)
            results.append(res)
            # Guardar progresivamente tras cada item para no perder datos si hay interrupción
            os.makedirs(os.path.dirname(args.output), exist_ok=True)
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[!] Error inesperado en #{it['id']}: {e}")

    print(f"[✓] Shard completado ({len(results)} items). Guardado en {args.output}")


if __name__ == "__main__":
    main()
