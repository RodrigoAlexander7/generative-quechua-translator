"""
Pipeline de traducción masiva concurrente para el corpus Quechua.
Utiliza AgyAdapter ('agy' CLI con esfuerzo 'low') o adaptadores configurados
para procesar en paralelo las 1,222 oraciones del corpus, con checkpoints automáticos,
reintentos y reporte de progreso en tiempo real (x/1222).
"""

import os
import json
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Dict, Any, List, Optional, Tuple

from src.translation.orchestrator import QuechuaTranslator
from src.translation.adapters.agy_adapter import AgyAdapter
from src.translation.adapters.fallback_adapter import FallbackAdapter


class CorpusTranslationPipeline:
    """Pipeline de traducción masiva concurrente con persistencia de checkpoints."""

    def __init__(
        self,
        corpus_path: Optional[str] = None,
        output_path: Optional[str] = None,
        checkpoint_path: Optional[str] = None,
        provider: str = "agy",
        effort: str = "low",
        concurrency: int = 4,
        timeout: int = 90
    ):
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.corpus_path = corpus_path or os.path.join(repo_root, "data", "processed", "corpus_tokenized.json")
        self.output_path = output_path or os.path.join(repo_root, "data", "processed", "corpus_translated.json")
        self.media_catalog_path = os.path.join(repo_root, "data", "processed", "media_catalog.json")
        self.checkpoint_path = checkpoint_path or os.path.join(repo_root, "data", "processed", ".translation_checkpoint.json")

        self.provider = provider
        self.effort = effort
        self.concurrency = concurrency
        self.timeout = timeout
        self.lock = Lock()

    def _load_checkpoint(self) -> Dict[str, Any]:
        """Carga las traducciones ya guardadas previamente si existen."""
        if os.path.exists(self.checkpoint_path):
            try:
                with open(self.checkpoint_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_checkpoint(self, cache: Dict[str, Any]):
        """Persiste atómicamente el progreso actual en disco."""
        tmp_path = self.checkpoint_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.checkpoint_path)

    def _translate_single_doc(
        self,
        doc: Dict[str, Any],
        translator: QuechuaTranslator
    ) -> Dict[str, Any]:
        """Traduce la transcripción completa de un clip usando el orquestador."""
        text = doc.get("transcription", "").strip()
        if not text:
            return {
                "traduccion_es": "",
                "traduccion_literal_glosada": "",
                "evidencialidad": "No especificado",
                "clusividad": None,
                "justificacion_semantica": "Sin texto",
                "backend": translator.adapter.name,
                "model_name": translator.adapter.model_name
            }

        res = translator.translate(text, long_mode=True, effort=self.effort, timeout=self.timeout)
        return {
            "traduccion_es": res.get("traduccion_es", "").strip(),
            "traduccion_literal_glosada": res.get("traduccion_literal_glosada", "").strip(),
            "evidencialidad": res.get("evidencialidad"),
            "clusividad": res.get("clusividad"),
            "justificacion_semantica": res.get("justificacion_semantica", ""),
            "backend": res.get("backend", translator.adapter.name),
            "model_name": res.get("model_name", translator.adapter.model_name),
            "translated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }

    def run(self, max_items: Optional[int] = None) -> Dict[str, Any]:
        """Ejecuta la granja de traducción sobre el corpus."""
        if not os.path.exists(self.corpus_path):
            raise FileNotFoundError(f"Corpus no encontrado en: {self.corpus_path}")

        print(f"[*] Cargando corpus tokenizado: {self.corpus_path}")
        with open(self.corpus_path, "r", encoding="utf-8") as f:
            corpus_data = json.load(f)

        documents = corpus_data.get("documents", [])
        total_docs = len(documents)
        if max_items:
            documents = documents[:max_items]
            total_docs = len(documents)

        print(f"[*] Documentos a procesar: {total_docs} | Concurrencia (workers): {self.concurrency}")
        print(f"[*] Proveedor: '{self.provider}' (esfuerzo: '{self.effort}', timeout: {self.timeout}s)")

        # Cargar checkpoint existente
        cache = self._load_checkpoint()
        completed_count = len([d for d in documents if d["audio_id"] in cache])
        print(f"[*] Checkpoint inicial: {completed_count}/{total_docs} ya traducidos.")

        pending_docs = [d for d in documents if d["audio_id"] not in cache]
        t0 = time.time()

        if pending_docs:
            print(f"[*] Lanzando {min(self.concurrency, len(pending_docs))} agentes de traducción...")

            def worker_fn(doc_item: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
                # Cada hilo instancia su propio QuechuaTranslator para aislamiento
                if self.provider == "agy":
                    adapter = AgyAdapter(effort=self.effort, timeout=self.timeout)
                elif self.provider == "fallback":
                    adapter = FallbackAdapter()
                else:
                    adapter = None

                translator = QuechuaTranslator(
                    adapter=adapter,
                    provider=self.provider if not adapter else None
                )
                trans_res = self._translate_single_doc(doc_item, translator)
                return doc_item["audio_id"], trans_res

            with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
                futures = {executor.submit(worker_fn, d): d for d in pending_docs}

                for future in as_completed(futures):
                    audio_id, trans_res = future.result()
                    with self.lock:
                        cache[audio_id] = trans_res
                        completed_count += 1
                        # Guardar checkpoint cada 5 items o al final
                        if completed_count % 5 == 0 or completed_count == total_docs:
                            self._save_checkpoint(cache)

                        pct = (completed_count / total_docs) * 100
                        print(f"[{completed_count}/{total_docs}] ({pct:.1f}%) Clip {audio_id}: {trans_res.get('traduccion_es')[:65]}...")

        # Ensamblar corpus_translated.json
        print(f"[*] Consolidando resultados en: {self.output_path}")
        translated_documents = []
        for doc in documents:
            doc_copy = dict(doc)
            doc_id = doc["audio_id"]
            doc_copy["translation"] = cache.get(doc_id, {
                "traduccion_es": "",
                "traduccion_literal_glosada": "",
                "evidencialidad": "Pendiente",
                "clusividad": None,
                "justificacion_semantica": "",
                "backend": "none"
            })
            translated_documents.append(doc_copy)

        output_data = {
            "corpus_info": {
                **corpus_data.get("corpus_info", {}),
                "translated_rows_count": completed_count,
                "translation_provider": self.provider,
                "translation_effort": self.effort,
                "translated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "pipeline_duration_sec": round(time.time() - t0, 2)
            },
            "documents": translated_documents
        }

        with open(self.output_path, "w", encoding="utf-8") as f_out:
            json.dump(output_data, f_out, ensure_ascii=False, indent=2)

        # Actualizar media_catalog.json si existe
        if os.path.exists(self.media_catalog_path):
            print(f"[*] Enriqueciendo catálogo multimedia: {self.media_catalog_path}")
            try:
                with open(self.media_catalog_path, "r", encoding="utf-8") as f_cat:
                    cat_data = json.load(f_cat)
                clips = cat_data.get("clips", {})
                for doc_id, trans_res in cache.items():
                    if doc_id in clips:
                        clips[doc_id]["traduccion_es"] = trans_res.get("traduccion_es", "")
                        clips[doc_id]["traduccion_literal_glosada"] = trans_res.get("traduccion_literal_glosada", "")
                        clips[doc_id]["evidencialidad"] = trans_res.get("evidencialidad")
                        clips[doc_id]["clusividad"] = trans_res.get("clusividad")
                with open(self.media_catalog_path, "w", encoding="utf-8") as f_cat:
                    json.dump(cat_data, f_cat, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"[!] Advertencia al actualizar media_catalog.json: {e}")

        total_sec = round(time.time() - t0, 2)
        print(f"[✓] Proceso completado exitosamente: {completed_count}/{total_docs} en {total_sec}s.")
        return output_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Traducción paralela del corpus quechua")
    parser.add_argument("--provider", default="agy", choices=["agy", "fallback", "gemini", "ollama", "openai"])
    parser.add_argument("--effort", default="low", choices=["low", "medium", "high"])
    parser.add_argument("--workers", type=int, default=4, help="Número de agentes en paralelo")
    parser.add_argument("--limit", type=int, default=None, help="Límite de documentos a procesar para pruebas")
    parser.add_argument("--timeout", type=int, default=90, help="Timeout en segundos por llamada a agy")
    args = parser.parse_args()

    pipeline = CorpusTranslationPipeline(
        provider=args.provider,
        effort=args.effort,
        concurrency=args.workers,
        timeout=args.timeout
    )
    pipeline.run(max_items=args.limit)
