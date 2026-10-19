"""
Generador del Índice Invertido y Motor de Búsqueda Morfosintáctico para el Corpus Quechua.
Lee data/processed/corpus_tokenized.json y genera data/processed/inverted_index.json.
Permite buscar palabras o raíces en audios/videos, obteniendo instantáneamente:
1. Su enriquecimiento sintáctico y morfológico completo.
2. Los videos/audios en los que aparecen con offsets de caracteres, timestamps estimados y snippets.
"""

import os
import json
import time
from typing import Dict, Any, List, Optional
from collections import defaultdict


class InvertedIndexBuilder:
    """Construye un índice invertido multi-nivel a partir del corpus tokenizado."""

    def __init__(self, tokenized_corpus_path: Optional[str] = None):
        if tokenized_corpus_path is None:
            repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            tokenized_corpus_path = os.path.join(repo_root, "data", "processed", "corpus_tokenized.json")
        self.corpus_path = tokenized_corpus_path

    def _build_context_snippet(self, text: str, start: int, end: int, window: int = 40) -> str:
        """Extrae un fragmento de texto centrado en la palabra encontrada."""
        left = max(0, start - window)
        right = min(len(text), end + window)
        snippet = text[left:right].strip()
        prefix = "..." if left > 0 else ""
        suffix = "..." if right < len(text) else ""
        return f"{prefix}{snippet}{suffix}"

    def build(self, output_path: Optional[str] = None, media_catalog_path: Optional[str] = None) -> Dict[str, Any]:
        """Procesa el corpus tokenizado y genera el índice invertido estructurado."""
        if output_path is None:
            repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            output_path = os.path.join(repo_root, "data", "processed", "inverted_index.json")

        print(f"[*] Cargando corpus tokenizado desde: {self.corpus_path}...")
        t0 = time.time()
        with open(self.corpus_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        documents = data.get("documents", [])
        print(f"[*] Documentos a indexar: {len(documents)}")

        media_catalog: Dict[str, Dict[str, Any]] = {}
        words_postings = defaultdict(list)
        words_metadata: Dict[str, Dict[str, Any]] = {}
        lemmas_postings = defaultdict(list)
        lemmas_metadata: Dict[str, Dict[str, Any]] = {}

        syntax_by_case = defaultdict(set)
        syntax_by_evidential = defaultdict(set)
        syntax_by_clusivity = defaultdict(set)
        syntax_by_pragmatic = defaultdict(set)

        for doc in documents:
            audio_id = doc["audio_id"]
            audio_file = doc["audio_file"]
            transcription = doc["transcription"]
            duration_ms = doc.get("duration_ms", 0)

            media_catalog[audio_id] = {
                "audio_id": audio_id,
                "audio_file": audio_file,
                "media_rel_path": doc.get("media_rel_path", ""),
                "duration_ms": duration_ms,
                "split": doc.get("split", ""),
                "speaker": doc.get("speaker", {}),
                "prompt": doc.get("prompt", {}),
                "transcription": transcription,
                "linguistic_summary": doc.get("linguistic_summary", {})
            }

            for sent in doc.get("sentences", []):
                sent_idx = sent["sentence_index"]
                sent_text = sent["text"]

                for tok in sent.get("tokens", []):
                    if tok.get("is_punct", False):
                        continue

                    surface = tok["surface"]
                    surface_norm = tok["surface_normalized"]
                    char_span = tok["char_span"]
                    time_span = tok["approx_time_ms"]
                    morph = tok.get("morphology", {})
                    syntax = tok.get("syntactic_enrichment", {})

                    lemma = morph.get("canonical_lemma", morph.get("root", surface_norm)).lower()

                    snippet = self._build_context_snippet(transcription, char_span[0], char_span[1])

                    occurrence = {
                        "audio_id": audio_id,
                        "audio_file": audio_file,
                        "sentence_index": sent_idx,
                        "token_index": tok["token_index"],
                        "char_span": char_span,
                        "approx_time_ms": time_span,
                        "surface": surface,
                        "context_snippet": snippet
                    }

                    # 1. Índice por palabra superficial
                    words_postings[surface_norm].append(occurrence)
                    if surface_norm not in words_metadata:
                        words_metadata[surface_norm] = {
                            "surface_representative": surface,
                            "surface_normalized": surface_norm,
                            "lemma": lemma,
                            "pos": morph.get("pos", "desconocido"),
                            "morphology": morph,
                            "syntactic_enrichment": syntax
                        }

                    # 2. Índice por lema canónico
                    lemmas_postings[lemma].append(occurrence)
                    if lemma not in lemmas_metadata:
                        senses_clean = [
                            s.get("definition") for s in morph.get("senses", []) if s.get("definition")
                        ]
                        lemmas_metadata[lemma] = {
                            "lemma": lemma,
                            "pos": morph.get("pos", "desconocido"),
                            "definitions": senses_clean[:3],
                            "surface_forms": set()
                        }
                    lemmas_metadata[lemma]["surface_forms"].add(surface_norm)

                    # 3. Índice sintáctico
                    c = syntax.get("case")
                    if c:
                        syntax_by_case[c].add(surface_norm)
                    ev = syntax.get("evidentiality")
                    if ev:
                        syntax_by_evidential[ev].add(surface_norm)
                    cl = syntax.get("clusivity")
                    if cl:
                        syntax_by_clusivity[cl].add(surface_norm)
                    for pr in syntax.get("pragmatics", []):
                        syntax_by_pragmatic[pr].add(surface_norm)

        # Empaquetar words_index
        words_index: Dict[str, Any] = {}
        for s_norm, postings in words_postings.items():
            meta = words_metadata[s_norm]
            doc_ids = set(p["audio_id"] for p in postings)
            words_index[s_norm] = {
                "surface": meta["surface_representative"],
                "surface_normalized": s_norm,
                "lemma": meta["lemma"],
                "pos": meta["pos"],
                "morphology": meta["morphology"],
                "syntactic_enrichment": meta["syntactic_enrichment"],
                "doc_frequency": len(doc_ids),
                "total_occurrences": len(postings),
                "postings": postings
            }

        # Empaquetar lemmas_index
        lemmas_index: Dict[str, Any] = {}
        for l_norm, postings in lemmas_postings.items():
            meta = lemmas_metadata[l_norm]
            doc_ids = set(p["audio_id"] for p in postings)
            lemmas_index[l_norm] = {
                "lemma": l_norm,
                "pos": meta["pos"],
                "definitions": meta["definitions"],
                "surface_forms": sorted(list(meta["surface_forms"])),
                "doc_frequency": len(doc_ids),
                "total_occurrences": len(postings),
                "postings": postings
            }

        syntax_index = {
            "by_case": {k: sorted(list(v)) for k, v in syntax_by_case.items()},
            "by_evidentiality": {k: sorted(list(v)) for k, v in syntax_by_evidential.items()},
            "by_clusivity": {k: sorted(list(v)) for k, v in syntax_by_clusivity.items()},
            "by_pragmatics": {k: sorted(list(v)) for k, v in syntax_by_pragmatic.items()}
        }

        # Empaquetar catálogo multimedia independiente
        if media_catalog_path is None:
            media_catalog_path = os.path.join(os.path.dirname(output_path), "media_catalog.json")

        media_catalog_output = {
            "catalog_info": {
                "corpus_id": "sps-corpus-5.0-2026-09-11-qxp",
                "total_media_clips": len(media_catalog),
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            },
            "clips": media_catalog
        }

        os.makedirs(os.path.dirname(os.path.abspath(media_catalog_path)), exist_ok=True)
        print(f"[*] Guardando catálogo multimedia en: {media_catalog_path}...")
        with open(media_catalog_path, "w", encoding="utf-8") as f_cat:
            json.dump(media_catalog_output, f_cat, ensure_ascii=False, indent=2)

        # Empaquetar índice invertido puro (términos y postings)
        output_data = {
            "index_info": {
                "corpus_id": "sps-corpus-5.0-2026-09-11-qxp",
                "indexed_audios_count": len(media_catalog),
                "unique_surface_words_count": len(words_index),
                "unique_lemmas_count": len(lemmas_index),
                "media_catalog_file": os.path.basename(media_catalog_path),
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "build_time_sec": round(time.time() - t0, 2)
            },
            "words_index": words_index,
            "lemmas_index": lemmas_index,
            "syntax_index": syntax_index
        }

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        print(f"[*] Guardando índice invertido en: {output_path}...")
        with open(output_path, "w", encoding="utf-8") as f_out:
            json.dump(output_data, f_out, ensure_ascii=False, indent=2)

        file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
        cat_size_mb = os.path.getsize(media_catalog_path) / (1024 * 1024)
        print(f"[✓] Índice invertido completado en {output_data['index_info']['build_time_sec']}s.")
        print(f"[✓] Índice de términos: {output_path} ({file_size_mb:.2f} MB)")
        print(f"[✓] Catálogo multimedia: {media_catalog_path} ({cat_size_mb:.2f} MB)")
        print(f"[✓] Palabras únicas: {len(words_index)}, Lemas únicos: {len(lemmas_index)}")

        return output_data


class QuechuaCorpusSearcher:
    """Motor de búsqueda morfosintáctico para consultar palabras y audios en el corpus."""

    def __init__(self, index_path: Optional[str] = None, media_catalog_path: Optional[str] = None):
        if index_path is None:
            repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            index_path = os.path.join(repo_root, "data", "processed", "inverted_index.json")
        self.index_path = index_path
        if media_catalog_path is None:
            media_catalog_path = os.path.join(os.path.dirname(index_path), "media_catalog.json")
        self.media_catalog_path = media_catalog_path
        self._loaded_data: Optional[Dict[str, Any]] = None
        self._loaded_media_catalog: Optional[Dict[str, Any]] = None

    def _ensure_loaded(self):
        if self._loaded_data is None:
            if not os.path.exists(self.index_path):
                raise FileNotFoundError(f"El índice invertido no existe en: {self.index_path}. Ejecuta el indexador primero.")
            with open(self.index_path, "r", encoding="utf-8") as f:
                self._loaded_data = json.load(f)

    @property
    def words_index(self) -> Dict[str, Any]:
        self._ensure_loaded()
        return self._loaded_data["words_index"]

    @property
    def lemmas_index(self) -> Dict[str, Any]:
        self._ensure_loaded()
        return self._loaded_data["lemmas_index"]

    @property
    def media_catalog(self) -> Dict[str, Any]:
        if self._loaded_media_catalog is None:
            if os.path.exists(self.media_catalog_path):
                with open(self.media_catalog_path, "r", encoding="utf-8") as f:
                    cat_data = json.load(f)
                    self._loaded_media_catalog = cat_data.get("clips", cat_data)
            else:
                self._ensure_loaded()
                self._loaded_media_catalog = self._loaded_data.get("media_catalog", {})
        return self._loaded_media_catalog

    @property
    def syntax_index(self) -> Dict[str, Any]:
        self._ensure_loaded()
        return self._loaded_data["syntax_index"]

    def get_clip_metadata(self, audio_id: str) -> Optional[Dict[str, Any]]:
        """Recupera los metadatos completos de un clip multimedia por su ID."""
        return self.media_catalog.get(audio_id)

    def search(self, query: str, search_type: str = "auto") -> Dict[str, Any]:
        """
        Busca un término en el índice invertido.
        search_type puede ser 'auto', 'surface' o 'lemma'.
        Retorna la ficha morfosintáctica y los clips de video/audio donde aparece.
        """
        self._ensure_loaded()
        q_clean = query.strip().lower()

        # 1. Búsqueda por superficie exacta o normalizada
        if search_type in ("auto", "surface") and q_clean in self.words_index:
            entry = self.words_index[q_clean]
            return {
                "match_type": "surface",
                "query": query,
                "surface": entry["surface"],
                "lemma": entry["lemma"],
                "pos": entry["pos"],
                "morphology": entry["morphology"],
                "syntactic_enrichment": entry["syntactic_enrichment"],
                "doc_frequency": entry["doc_frequency"],
                "total_occurrences": entry["total_occurrences"],
                "postings": entry["postings"]
            }

        # 2. Búsqueda por lema / raíz
        if search_type in ("auto", "lemma") and q_clean in self.lemmas_index:
            entry = self.lemmas_index[q_clean]
            return {
                "match_type": "lemma",
                "query": query,
                "lemma": entry["lemma"],
                "pos": entry["pos"],
                "definitions": entry["definitions"],
                "surface_forms": entry["surface_forms"],
                "doc_frequency": entry["doc_frequency"],
                "total_occurrences": entry["total_occurrences"],
                "postings": entry["postings"]
            }

        # Búsqueda difusa / prefijo en lemas si no hay coincidencia exacta
        matching_lemmas = [l for l in self.lemmas_index if l.startswith(q_clean)]
        if matching_lemmas:
            primary_lemma = matching_lemmas[0]
            entry = self.lemmas_index[primary_lemma]
            return {
                "match_type": "lemma_prefix",
                "query": query,
                "matched_lemma": primary_lemma,
                "lemma": entry["lemma"],
                "pos": entry["pos"],
                "definitions": entry["definitions"],
                "surface_forms": entry["surface_forms"],
                "doc_frequency": entry["doc_frequency"],
                "total_occurrences": entry["total_occurrences"],
                "postings": entry["postings"]
            }

        return {
            "match_type": "none",
            "query": query,
            "message": f"No se encontraron ocurrencias para '{query}' en el corpus transcrito."
        }

    def search_by_surface(self, word: str) -> Dict[str, Any]:
        """Busca específicamente por forma superficial de la palabra."""
        return self.search(word, search_type="surface")

    def search_by_lemma(self, lemma: str) -> Dict[str, Any]:
        """Busca específicamente por raíz o lema canónico."""
        return self.search(lemma, search_type="lemma")

    def search_by_syntax(self, filter_type: str, filter_val: str) -> List[str]:
        """
        Consulta el índice sintáctico.
        filter_type: 'case', 'evidentiality', 'clusivity', o 'pragmatics'.
        """
        self._ensure_loaded()
        category = f"by_{filter_type}"
        return self.syntax_index.get(category, {}).get(filter_val, [])


if __name__ == "__main__":
    builder = InvertedIndexBuilder()
    builder.build()
