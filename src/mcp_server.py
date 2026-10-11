"""
Servidor MCP Nativo (Model Context Protocol) para Quechua Translator.
Transporte: Stdio (compatible con Antigravity / Claude Desktop / Cursor).
Expone las herramientas:
- quechua_segment
- quechua_lookup
- quechua_suffix
- quechua_translate
"""

import sys
import os
import json
import traceback
from typing import Dict, Any, Optional

# Asegurar que el directorio raíz del proyecto esté en PYTHONPATH
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.translation.orchestrator import QuechuaTranslator


# Definición de herramientas MCP
TOOLS_DEFINITIONS = [
    {
        "name": "quechua_segment",
        "description": (
            "Segmenta morfológicamente una oración o palabra en quechua, identificando "
            "raíces léxicas normalizadas, sufijos divididos por ranura morfotáctica y glosas gramaticales."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Oración o palabra en quechua para analizar."
                }
            },
            "required": ["text"]
        }
    },
    {
        "name": "quechua_lookup",
        "description": (
            "Busca un lema en los diccionarios de quechua indexados (AMLQ y Calvo Pérez), "
            "retornando todas sus acepciones semánticas, dominios y ejemplos contextuales bilingües."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "word": {
                    "type": "string",
                    "description": "Lema o raíz en quechua a consultar (ej: wasi, allpaqa, tiyay)."
                }
            },
            "required": ["word"]
        }
    },
    {
        "name": "quechua_suffix",
        "description": (
            "Consulta información taxonómica de un sufijo en el catálogo de 245 sufijos quechua: "
            "alomorfos, ranura morfotáctica (slot), categoría (flexivo/derivacional), definición y ejemplos."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "suffix": {
                    "type": "string",
                    "description": "Sufijo quechua (ej: kuna, manta, mi, sha, nchis)."
                }
            },
            "required": ["suffix"]
        }
    },
    {
        "name": "quechua_translate",
        "description": (
            "Traduce una oración en quechua al español empleando el andamiaje morfo-semántico, "
            "respetando rigurosamente evidenciales (-mi, -si, -chá) y clusividad (-nchis, -yku)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Oración en quechua a traducir."
                },
                "provider": {
                    "type": "string",
                    "description": "Proveedor/adaptador generativo opcional ('auto', 'agy', 'gemini', 'openai', 'ollama', 'fallback').",
                    "enum": ["auto", "agy", "gemini", "gemini_api", "openai", "ollama", "fallback"]
                },
                "model": {
                    "type": "string",
                    "description": "Nombre específico del modelo LLM (ej: 'llama3.2:3b-instruct-q4_K_M', 'gemini-2.5-flash', 'gpt-4o-mini')."
                }
            },
            "required": ["text"]
        }
    }
]


# Instancia perezosa del traductor
_translator_instance: Optional[QuechuaTranslator] = None

def get_translator() -> QuechuaTranslator:
    global _translator_instance
    if _translator_instance is None:
        _translator_instance = QuechuaTranslator()
    return _translator_instance


# ---------------------------------------------------------------------------
# Implementación de las herramientas
# ---------------------------------------------------------------------------

def execute_segment(args: Dict[str, Any]) -> str:
    text = args.get("text", "").strip()
    if not text:
        return json.dumps({"error": "Parámetro 'text' es obligatorio."}, ensure_ascii=False)
    translator = get_translator()
    scaffold = translator._get_scaffold(text)
    return json.dumps(scaffold, indent=2, ensure_ascii=False)


def execute_lookup(args: Dict[str, Any]) -> str:
    word = args.get("word", "").strip().lower()
    if not word:
        return json.dumps({"error": "Parámetro 'word' es obligatorio."}, ensure_ascii=False)

    from src.cli import handle_lookup
    # Reutilizar lógica de consulta de lemas
    db_path = os.environ.get("QUECHUA_DB_PATH")
    found = []

    try:
        from src.storage.db import QuechuaDB
        db = QuechuaDB(db_path) if db_path else QuechuaDB()
        res = db.get_lemma(word)
        if res:
            found.append(res)
        else:
            s_res = db.search_lemmas(word)
            if s_res:
                found.extend(s_res[:5])
    except Exception:
        pass

    # Fallback a JSON si no hay DB
    if not found:
        json_path = os.path.join(PROJECT_ROOT, "input", "paqocha-fst", "data", "entries.json")
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    entries = json.load(f)
                matches = [e for e in entries if e.get("palabra", "").lower() == word]
                if matches:
                    senses = [{"index": i, "definition": m.get("definicion", "")} for i, m in enumerate(matches, 1)]
                    found.append({
                        "headword": matches[0]["palabra"],
                        "pos": matches[0].get("categoria", "s."),
                        "senses": senses
                    })
            except Exception:
                pass

    if not found:
        return json.dumps({"word": word, "found": False, "message": f"No se encontró '{word}' en el diccionario."}, ensure_ascii=False)

    return json.dumps({"word": word, "found": True, "results": found}, indent=2, ensure_ascii=False)


def execute_suffix(args: Dict[str, Any]) -> str:
    suffix = args.get("suffix", "").strip().lstrip("-").lower()
    if not suffix:
        return json.dumps({"error": "Parámetro 'suffix' es obligatorio."}, ensure_ascii=False)

    db_path = os.environ.get("QUECHUA_DB_PATH")
    found = []

    try:
        from src.storage.db import QuechuaDB
        db = QuechuaDB(db_path) if db_path else QuechuaDB()
        res = db.get_suffix(suffix)
        if res:
            found = res if isinstance(res, list) else [res]
    except Exception:
        pass

    if not found:
        # Fallback al CSV
        csv_path = os.path.join(PROJECT_ROOT, "input", "sufix", "suffixes - V3.0.csv")
        if os.path.exists(csv_path):
            import csv, re
            try:
                with open(csv_path, "r", encoding="utf-8") as f:
                    for row in csv.DictReader(f):
                        m = row.get("SUFIJO", "").strip()
                        parts = [p.strip().lower() for p in re.split(r"[/,]", m)]
                        if suffix in parts or m.lower() == suffix:
                            found.append({
                                "morpheme": m,
                                "type": row.get("TIPO", ""),
                                "subtype": row.get("SUBTIPO", ""),
                                "category": row.get("CATEGORIA", ""),
                                "subcategory": row.get("SUBCATEGORIA", ""),
                                "definition": row.get("DEFINICION", ""),
                                "examples": row.get("EJEMPLOS", "")
                            })
            except Exception:
                pass

    if not found:
        return json.dumps({"suffix": suffix, "found": False, "message": f"No se encontró el sufijo '-{suffix}'."}, ensure_ascii=False)

    return json.dumps({"suffix": suffix, "found": True, "results": found}, indent=2, ensure_ascii=False)


def execute_translate(args: Dict[str, Any]) -> str:
    text = args.get("text", "").strip()
    if not text:
        return json.dumps({"error": "Parámetro 'text' es obligatorio."}, ensure_ascii=False)

    provider = args.get("provider")
    model = args.get("model")
    if provider or model:
        translator = QuechuaTranslator(provider=provider, model_name=model)
    else:
        translator = get_translator()

    res = translator.translate(text)
    return json.dumps(res, indent=2, ensure_ascii=False)


# Despachador de herramientas
TOOL_HANDLERS = {
    "quechua_segment": execute_segment,
    "quechua_lookup": execute_lookup,
    "quechua_suffix": execute_suffix,
    "quechua_translate": execute_translate,
}


# ---------------------------------------------------------------------------
# Bucle de procesamiento JSON-RPC 2.0 Stdio
# ---------------------------------------------------------------------------

def send_response(response: Dict[str, Any]):
    """Envía un mensaje JSON-RPC formateado a stdout."""
    payload = json.dumps(response, ensure_ascii=False)
    sys.stdout.write(payload + "\n")
    sys.stdout.flush()


def run_stdio_server():
    """Servidor MCP por transporte Stdio."""
    # Desactivar buffering si es posible
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")

    while True:
        line = sys.stdin.readline()
        if not line:
            break

        line = line.strip()
        if not line:
            continue

        # Soporte para Content-Length framing si se detecta
        if line.lower().startswith("content-length:"):
            try:
                length = int(line.split(":", 1)[1].strip())
                # Leer línea vacía separadora
                sys.stdin.readline()
                raw_body = sys.stdin.read(length)
                request = json.loads(raw_body)
            except Exception as e:
                continue
        else:
            try:
                request = json.loads(line)
            except Exception:
                continue

        req_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        # 1. initialize
        if method == "initialize":
            send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {
                            "listChanged": False
                        }
                    },
                    "serverInfo": {
                        "name": "quechua-engine",
                        "version": "1.0.0"
                    }
                }
            })

        # 2. notifications/initialized o notificaciones en general
        elif method == "notifications/initialized" or req_id is None:
            # Notificación sin id: no responder
            continue

        # 3. ping
        elif method == "ping":
            send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {}
            })

        # 4. tools/list
        elif method == "tools/list":
            send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": TOOLS_DEFINITIONS
                }
            })

        # 5. tools/call
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if tool_name not in TOOL_HANDLERS:
                send_response({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32601,
                        "message": f"Herramienta desconocida: {tool_name}"
                    }
                })
            else:
                try:
                    handler = TOOL_HANDLERS[tool_name]
                    result_text = handler(arguments)
                    send_response({
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": result_text
                                }
                            ],
                            "isError": False
                        }
                    })
                except Exception as e:
                    send_response({
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"Error ejecutando {tool_name}: {str(e)}\n{traceback.format_exc()}"
                                }
                            ],
                            "isError": True
                        }
                    })

        else:
            # Método desconocido
            if req_id is not None:
                send_response({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32601,
                        "message": f"Método no soportado: {method}"
                    }
                })


if __name__ == "__main__":
    run_stdio_server()
