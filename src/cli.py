"""
Interfaz de línea de comandos (CLI) para Quechua Translator.
Proporciona comandos para:
- qtr index: Construcción e indexación de la base de datos de conocimiento.
- qtr lookup <palabra>: Búsqueda de lemas en el diccionario con acepciones y ejemplos.
- qtr suffix <sufijo>: Consulta de sufijos con taxonomía, definición y ejemplos.
- qtr segment "<oración>": Segmentación morfológica detallada por token.
- qtr translate "<oración>": Traducción generativa asistida por scaffold morfo-semántico.
"""

import sys
import os
import argparse
import json
import sqlite3
import csv
import re
from typing import Optional, List, Dict, Any

# Códigos de colores ANSI para la terminal
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
ITALIC = "\033[3m"
UNDERLINE = "\033[4m"

RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"

BRIGHT_GREEN = "\033[92m"
BRIGHT_YELLOW = "\033[93m"
BRIGHT_CYAN = "\033[96m"
BRIGHT_MAGENTA = "\033[95m"


def print_banner():
    banner = f"""{BOLD}{BRIGHT_CYAN}
   ___                  __                _____                      __      __            
  / _ \\ __ _____ ____ / /  __ _____ _    /_  __/______ ____  ___ ___/ /___ _/ /____  ____   
 / // // // / -_) __// _ \\/ // / _ `/     / / / __/ _ `/ _ \\(_-</ _  // _ `/ __/ _ \\/ __/   
 \\___\\_\\_,_/\\__/\\__//_//_/\\_,_/\\_,_/     /_/ /_/  \\_,_/_//_/___/\\_,_/ \\_,_/\\__/\\___/_/      
{RESET}{DIM}   Herramienta de Análisis Morfosintáctico y Traducción Generativa Quechua-Español{RESET}
"""
    print(banner)


def get_default_db_path() -> str:
    """Devuelve la ruta a la base de datos de conocimiento."""
    # Buscar en data/quechua_knowledge.db relativo a la raíz del repositorio
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_path = os.path.join(repo_root, "data", "quechua_knowledge.db")
    return os.environ.get("QUECHUA_DB_PATH", default_path)


# ---------------------------------------------------------------------------
# Comando: index
# ---------------------------------------------------------------------------

def handle_index(args):
    """Ejecuta el proceso de indexación de la base de datos."""
    print(f"\n{BOLD}{BRIGHT_CYAN}[*] Iniciando proceso de indexación de diccionarios y sufijos...{RESET}\n")

    # Intentar ejecutar build_db
    try:
        from src.indexer.build_db import build_database
        build_database()
        print(f"\n{BOLD}{BRIGHT_GREEN}[✓] Indexación completada exitosamente.{RESET}\n")
        return 0
    except ImportError:
        pass

    # Fallback: ejecutar script directo si existe
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    script_path = os.path.join(repo_root, "src", "indexer", "build_db.py")
    if os.path.exists(script_path):
        import subprocess
        res = subprocess.run([sys.executable, script_path], cwd=repo_root)
        return res.returncode
    else:
        print(f"{RED}[!] Error: No se encontró el script de indexación en src/indexer/build_db.py{RESET}")
        return 1


# ---------------------------------------------------------------------------
# Comando: lookup
# ---------------------------------------------------------------------------

def handle_lookup(args):
    """Busca una palabra en el diccionario y muestra acepciones y ejemplos."""
    word = args.word.strip().lower()
    if not word:
        print(f"{RED}[!] Debes especificar una palabra para buscar.{RESET}")
        return 1

    db_path = get_default_db_path()
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    found_entries = []

    # 1. Intentar buscar en QuechuaDB
    try:
        from src.storage.db import QuechuaDB
        db = QuechuaDB(db_path)
        lemma_data = db.get_lemma(word)
        if lemma_data:
            found_entries.append(lemma_data)
        else:
            # Búsqueda por prefijo o FTS
            search_results = db.search_lemmas(word)
            if search_results:
                found_entries.extend(search_results[:5])
    except Exception:
        # Fallback 1: SQLite directo si la base existe
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                cur.execute(
                    "SELECT lemma_id, headword, pos, dialect_origin FROM lemmas WHERE headword = ? OR headword_normalized = ?",
                    (word, word)
                )
                rows = cur.fetchall()
                for r in rows:
                    lemma_id, hw, pos, dialect = r
                    # sentidos
                    cur.execute("SELECT sense_index, definition_es, semantic_domain FROM senses WHERE lemma_id = ?", (lemma_id,))
                    senses = [{"index": s[0], "definition": s[1], "domain": s[2]} for s in cur.fetchall()]
                    # ejemplos
                    cur.execute("SELECT phrase_qu, translation_es FROM examples WHERE lemma_id = ?", (lemma_id,))
                    examples = [{"qu": ex[0], "es": ex[1]} for ex in cur.fetchall()]
                    found_entries.append({
                        "headword": hw,
                        "pos": pos,
                        "dialect": dialect,
                        "senses": senses,
                        "examples": examples
                    })
                conn.close()
            except Exception:
                pass

    # Fallback 2: Si no hay base de datos aún, consultar directamente entries.json
    if not found_entries:
        json_path = os.path.join(repo_root, "input", "paqocha-fst", "data", "entries.json")
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    all_entries = json.load(f)
                matches = [e for e in all_entries if e.get("palabra", "").lower() == word]
                if matches:
                    senses = []
                    for i, m in enumerate(matches, 1):
                        senses.append({
                            "index": i,
                            "definition": m.get("definicion", ""),
                            "domain": None
                        })
                    found_entries.append({
                        "headword": matches[0]["palabra"],
                        "pos": matches[0].get("categoria", "s."),
                        "dialect": "cuz",
                        "senses": senses,
                        "examples": []
                    })
            except Exception:
                pass

    if not found_entries:
        print(f"\n{YELLOW}[!] No se encontraron entradas para '{word}' en el diccionario.{RESET}")
        print(f"{DIM}Sugerencia: Ejecuta 'qtr index' para reconstruir el índice.{RESET}\n")
        return 0

    print(f"\n{BOLD}{BRIGHT_CYAN}=== Resultados de Búsqueda para '{word}' ==={RESET}\n")
    for entry in found_entries:
        hw = entry.get("headword", word)
        pos = entry.get("pos", "")
        dialect = entry.get("dialect", "cuz")
        senses = entry.get("senses", [])
        examples = entry.get("examples", [])
        synonyms = entry.get("synonyms", [])
        variants = entry.get("variants", [])

        print(f"{BOLD}{BRIGHT_GREEN}Lema:{RESET} {BOLD}{hw}{RESET}  [{BOLD}{MAGENTA}{pos}{RESET}]  {DIM}(Variante: {dialect}){RESET}")

        if synonyms:
            print(f"  {BOLD}{YELLOW}Sinónimos:{RESET} {', '.join(synonyms)}")
        if variants:
            var_str = ", ".join(f"{v.get('form', '')} ({v.get('dialect', '')})" if isinstance(v, dict) else str(v) for v in variants)
            print(f"  {BOLD}{YELLOW}Variantes dialectales:{RESET} {var_str}")

        print(f"  {BOLD}Acepciones ({len(senses)}):{RESET}")
        for s in senses:
            idx = s.get("index", 1)
            defn = s.get("definition", "") or s.get("definition_es", "")
            domain = s.get("domain") or s.get("semantic_domain")
            dom_str = f" {MAGENTA}[{domain}]{RESET}" if domain else ""
            print(f"    {BOLD}{idx}.{RESET}{dom_str} {defn}")

        if examples:
            print(f"  {BOLD}Ejemplos Registrados:{RESET}")
            for ex in examples:
                qu = ex.get("phrase_qu") or ex.get("qu", "")
                es = ex.get("translation_es") or ex.get("es", "")
                print(f"    {CYAN}• {qu}{RESET} → {ITALIC}{es}{RESET}")

        print("-" * 60)
    print()
    return 0


# ---------------------------------------------------------------------------
# Comando: suffix
# ---------------------------------------------------------------------------

def handle_suffix(args):
    """Muestra detalles taxonómicos, definición y ejemplos de un sufijo."""
    query_suff = args.suffix.strip().lstrip("-").lower()
    if not query_suff:
        print(f"{RED}[!] Debes especificar un sufijo.{RESET}")
        return 1

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = get_default_db_path()

    matched_suffixes = []

    # 1. Intentar consultar QuechuaDB
    try:
        from src.storage.db import QuechuaDB
        db = QuechuaDB(db_path)
        res = db.get_suffix(query_suff)
        if res:
            if isinstance(res, list):
                matched_suffixes.extend(res)
            else:
                matched_suffixes.append(res)
    except Exception:
        pass

    # 2. Fallback: Consultar directamente el CSV de sufijos
    if not matched_suffixes:
        csv_path = os.path.join(repo_root, "input", "sufix", "suffixes - V3.0.csv")
        if os.path.exists(csv_path):
            try:
                with open(csv_path, mode="r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        morpheme = row.get("SUFIJO", "").strip()
                        if not morpheme:
                            continue
                        # Extraer alomorfos
                        parts = [p.strip().lower() for p in re.split(r"[/,]", morpheme)]
                        if query_suff in parts or morpheme.lower() == query_suff:
                            matched_suffixes.append({
                                "morpheme": morpheme,
                                "type": row.get("TIPO", ""),
                                "subtype": row.get("SUBTIPO", ""),
                                "category": row.get("CATEGORIA", ""),
                                "subcategory": row.get("SUBCATEGORIA", ""),
                                "definition": row.get("DEFINICION", ""),
                                "examples": row.get("EJEMPLOS", "")
                            })
            except Exception:
                pass

    if not matched_suffixes:
        print(f"\n{YELLOW}[!] No se encontró el sufijo '-{query_suff}'.{RESET}\n")
        return 0

    print(f"\n{BOLD}{BRIGHT_CYAN}=== Información del Sufijo '-{query_suff}' ==={RESET}\n")
    for s in matched_suffixes:
        morpheme = s.get("morpheme", query_suff.upper())
        stype = s.get("type", "")
        subtype = s.get("subtype", "")
        cat = s.get("category", "")
        subcat = s.get("subcategory", "")
        slot = s.get("slot_order") or s.get("slot")
        defn = s.get("definition", "")
        raw_ex = s.get("examples") or s.get("raw_examples", "")

        print(f"{BOLD}{BRIGHT_YELLOW}Sufijo:{RESET} {BOLD}-{morpheme}{RESET}")
        if slot:
            print(f"  {BOLD}Ranura Morfotáctica:{RESET} {BOLD}{CYAN}Slot {slot}{RESET}")
        print(f"  {BOLD}Tipo:{RESET} {stype} {DIM}({subtype}){RESET}")
        print(f"  {BOLD}Categoría:{RESET} {MAGENTA}{cat}{RESET} - {subcat}")
        print(f"  {BOLD}Definición:{RESET} {defn}")

        if raw_ex:
            print(f"  {BOLD}Ejemplos Registrados:{RESET}")
            for line in raw_ex.split("\n"):
                line = line.strip()
                if line:
                    if "=" in line:
                        qu, es = line.split("=", 1)
                        print(f"    {CYAN}• {qu.strip()}{RESET} = {GREEN}{es.strip()}{RESET}")
                    else:
                        print(f"    • {line}")

        print("-" * 60)
    print()
    return 0


# ---------------------------------------------------------------------------
# Comando: segment
# ---------------------------------------------------------------------------

def handle_segment(args):
    """Segmenta morfológicamente una oración o palabra e imprime una tabla ANSI."""
    text = args.text.strip()
    if not text:
        print(f"{RED}[!] Debes ingresar una oración o palabra para segmentar.{RESET}")
        return 1

    print(f"\n{BOLD}{BRIGHT_CYAN}Analizando morfología:{RESET} \"{text}\"\n")

    # Obtener el scaffold
    from src.translation.orchestrator import QuechuaTranslator
    translator = QuechuaTranslator()
    scaffold = translator._get_scaffold(text)

    tokens = scaffold.get("tokens", [])
    if not tokens:
        print(f"{YELLOW}[!] No se pudieron extraer tokens.{RESET}\n")
        return 0

    # Imprimir tabla detallada
    header = f"{BOLD}{'Token':<18} | {'Raíz (Lema)':<18} | {'POS':<6} | {'Cadena de Sufijos':<25} | {'Glosas / Ranuras'}{RESET}"
    sep = "-" * 95
    print(header)
    print(sep)

    for tok in tokens:
        surface = tok.get("surface", "")
        stem = tok.get("stem", {})
        hw = stem.get("headword", surface)
        pos = stem.get("pos", "")
        affixes = tok.get("affixes", [])

        if affixes:
            suff_chain = "-".join([a.get("morpheme", "").lstrip("-") for a in affixes])
            slots_desc = ", ".join([
                f"{a.get('morpheme', '')} ({a.get('subcategory', a.get('category', ''))})"
                for a in affixes
            ])
        else:
            suff_chain = "(raíz pura)"
            slots_desc = "Raíz sin afijos"

        tok_colored = f"{WHITE}{surface:<18}{RESET}"
        hw_colored = f"{BRIGHT_CYAN}{hw:<18}{RESET}"
        pos_colored = f"{MAGENTA}{pos:<6}{RESET}"
        suff_colored = f"{BRIGHT_YELLOW}{suff_chain:<25}{RESET}"
        slots_colored = f"{GREEN}{slots_desc}{RESET}"

        print(f"{tok_colored} | {hw_colored} | {pos_colored} | {suff_colored} | {slots_colored}")

    print(sep)
    print()
    return 0


# ---------------------------------------------------------------------------
# Comando: analyze
# ---------------------------------------------------------------------------

def handle_analyze(args):
    """Analiza morfosintácticamente una frase o párrafo y produce salida estructurada."""
    text = args.text.strip()
    if not text:
        print(f"{RED}[!] Debes ingresar una frase, párrafo o palabra para analizar.{RESET}")
        return 1

    from src.segmentation.analyzer import MorphosyntacticAnalyzer
    analyzer = MorphosyntacticAnalyzer()
    result = analyzer.analyze(text)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    # Salida legible en terminal, agrupada por oración
    print(f"\n{BOLD}{BRIGHT_CYAN}Análisis Morfosintáctico{RESET}")
    print(f"{DIM}Oraciones: {result['num_oraciones']} | Tokens: {result['num_tokens']}{RESET}\n")

    for oracion in result["oraciones"]:
        print(f"{BOLD}{BRIGHT_YELLOW}[Oración {oracion['indice'] + 1}]{RESET} {ITALIC}{oracion['texto']}{RESET}")
        for tok in oracion["tokens"]:
            if tok["es_puntuacion"]:
                continue
            raiz = tok["raiz"]
            pos = tok["categoria_gramatical"]
            glosa = tok["glosa"]
            dict_mark = f"{BRIGHT_GREEN}✓{RESET}" if tok["encontrado_en_diccionario"] else f"{YELLOW}?{RESET}"

            print(f"  {BOLD}{WHITE}{tok['token']}{RESET} {DIM}[{dict_mark}{DIM} conf={tok['confianza']}]{RESET}")
            print(f"     {DIM}raíz:{RESET} {BRIGHT_CYAN}{raiz}{RESET}  {DIM}pos:{RESET} {MAGENTA}{pos}{RESET}  {DIM}glosa:{RESET} {GREEN}{glosa}{RESET}")

            if tok["acepciones"]:
                primera = tok["acepciones"][0].get("definicion", "")
                primera_corta = primera.split(".")[0][:70] if primera else ""
                if primera_corta:
                    print(f"     {DIM}def:{RESET} {primera_corta}")

            for s in tok["sufijos"]:
                print(f"       {BRIGHT_YELLOW}{s['morfema']:<8}{RESET} {DIM}slot {s['slot']}{RESET}  {CYAN}{s['glosa_corta']:<12}{RESET} {DIM}{s['funcion'][:50]}{RESET}")

            marc = tok["marcadores"]
            if marc["evidencialidad"]:
                print(f"     {DIM}evidencialidad:{RESET} {MAGENTA}{marc['evidencialidad']}{RESET}")
            if marc["clusividad"]:
                print(f"     {DIM}clusividad:{RESET} {YELLOW}{marc['clusividad']}{RESET}")
        print()

    return 0


# ---------------------------------------------------------------------------
# Comando: translate
# ---------------------------------------------------------------------------

def handle_translate(args):
    """Ejecuta el pipeline completo de traducción Quechua -> Español."""
    text = args.text.strip()
    if not text:
        print(f"{RED}[!] Debes ingresar una oración en quechua para traducir.{RESET}")
        return 1

    print(f"\n{BOLD}{BRIGHT_CYAN}[*] Procesando traducción generativa...{RESET}")
    print(f"{DIM}Oración Quechua:{RESET} {BOLD}\"{text}\"{RESET}\n")

    from src.translation.orchestrator import QuechuaTranslator
    use_agy_flag = getattr(args, "use_agy", None)
    long_mode = getattr(args, "long_mode", False)
    provider_arg = getattr(args, "provider", None)
    model_arg = getattr(args, "model", None)
    api_key_arg = getattr(args, "api_key", None)
    ollama_host_arg = getattr(args, "ollama_host", None)

    translator = QuechuaTranslator(
        provider=provider_arg,
        model_name=model_arg,
        api_key=api_key_arg,
        ollama_host=ollama_host_arg,
        use_agy=use_agy_flag
    )
    res = translator.translate(text, long_mode=long_mode)

    traduccion_es = res.get("traduccion_es", "")
    glosa = res.get("traduccion_literal_glosada", "")
    evidencialidad = res.get("evidencialidad", "No marcado")
    clusividad = res.get("clusividad")
    justificacion = res.get("justificacion_semantica", "")
    backend = res.get("backend", "fallback")
    model_name = res.get("model_name", "")
    motor_desc = f"{backend.upper()}" + (f" ({model_name})" if model_name else "")

    # Presentación estructurada
    print(f"{BOLD}{BRIGHT_GREEN}┌─ TRADUCCIÓN AL ESPAÑOL {DIM}[Motor: {motor_desc}]{RESET}")
    print(f"{BOLD}{BRIGHT_GREEN}│{RESET}  {BOLD}{WHITE}{traduccion_es}{RESET}")
    print(f"{BOLD}{BRIGHT_GREEN}└──────────────────────────────────────────────────────────{RESET}\n")

    print(f"{BOLD}Análisis Morfo-Semántico:{RESET}")
    if glosa:
        print(f"  {BOLD}• Glosa Interlineal:{RESET}   {CYAN}{glosa}{RESET}")
    print(f"  {BOLD}• Evidencialidad:{RESET}      {MAGENTA}{evidencialidad}{RESET}")
    if clusividad:
        print(f"  {BOLD}• Clusividad:{RESET}          {YELLOW}{clusividad}{RESET}")
    else:
        print(f"  {BOLD}• Clusividad:{RESET}          {DIM}No aplica (no interviene 1ra plural){RESET}")
    print(f"  {BOLD}• Justificación:{RESET}       {DIM}{justificacion}{RESET}\n")

    if args.json:
        print(f"{BOLD}Salida JSON:{RESET}")
        print(json.dumps(res, indent=2, ensure_ascii=False))
        print()

    return 0


# ---------------------------------------------------------------------------
# Entrypoint principal
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="qtr",
        description="Quechua Translator CLI - Análisis Morfológico y Traducción Generativa"
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Comandos disponibles")

    # index
    parser_index = subparsers.add_parser("index", help="Construye e indexa la base de datos SQLite FTS5")
    parser_index.set_defaults(func=handle_index)

    # lookup
    parser_lookup = subparsers.add_parser("lookup", help="Busca un lema en el diccionario")
    parser_lookup.add_argument("word", type=str, help="Palabra o raíz a consultar")
    parser_lookup.set_defaults(func=handle_lookup)

    # suffix
    parser_suffix = subparsers.add_parser("suffix", help="Consulta un sufijo en el catálogo taxonómico")
    parser_suffix.add_argument("suffix", type=str, help="Sufijo a consultar (ej: kuna, manta, mi)")
    parser_suffix.set_defaults(func=handle_suffix)

    # segment
    parser_segment = subparsers.add_parser("segment", help="Segmenta morfológicamente una oración")
    parser_segment.add_argument("text", type=str, help="Oración o token en quechua")
    parser_segment.set_defaults(func=handle_segment)

    # analyze
    parser_analyze = subparsers.add_parser("analyze", help="Analiza morfosintácticamente una frase o párrafo (salida estructurada)")
    parser_analyze.add_argument("text", type=str, help="Frase, párrafo o palabra en quechua")
    parser_analyze.add_argument("--json", action="store_true", help="Imprime el análisis completo en JSON estructurado")
    parser_analyze.set_defaults(func=handle_analyze)

    # translate
    parser_translate = subparsers.add_parser("translate", help="Traduce una oración quechua al español")
    parser_translate.add_argument("text", type=str, help="Oración en quechua")
    parser_translate.add_argument("--json", action="store_true", help="Imprime el resultado completo en JSON")
    parser_translate.add_argument("-L", "--long", dest="long_mode", action="store_true", help="Modo texto largo (hasta 1000 caracteres): scaffold compacto, esfuerzo bajo de pensamiento (--effort low) y máxima velocidad sin internet")
    parser_translate.add_argument("-p", "--provider", dest="provider", type=str, choices=["auto", "agy", "gemini", "gemini_api", "openai", "ollama", "fallback"], default=None, help="Motor/adaptador generativo (auto, agy, gemini, openai, ollama, fallback)")
    parser_translate.add_argument("-m", "--model", dest="model", type=str, default=None, help="Nombre del modelo (ej: llama3.2:3b-instruct-q4_K_M, gemini-2.5-flash, gpt-4o-mini)")
    parser_translate.add_argument("--ollama-host", dest="ollama_host", type=str, default=None, help="URL del servidor local Ollama (por defecto: http://localhost:11434)")
    parser_translate.add_argument("--api-key", dest="api_key", type=str, default=None, help="API Key para el proveedor seleccionado (Gemini u OpenAI)")
    parser_translate.add_argument("--agy", dest="use_agy", action="store_true", default=None, help="Usa Antigravity CLI (agy) para traducción generativa con Gemini")
    parser_translate.add_argument("--no-agy", dest="use_agy", action="store_false", help="Desactiva agy y usa API o fallback")
    parser_translate.set_defaults(func=handle_translate)

    if len(sys.argv) == 1:
        print_banner()
        parser.print_help()
        return 0

    args = parser.parse_args()
    if hasattr(args, "func"):
        return args.func(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
