"""
Pipeline de procesamiento morfo-semántico del corpus de Quechua Puno (qxp).
Lee data/raw/sps-corpus-5.0-2026-09-11-qxp/ss-corpus-qxp.tsv, filtra las oraciones
con transcripción, realiza la descomposición morfológica y enriquecimiento
sintáctico por ranura y genera el archivo data/processed/corpus_tokenized.json.
"""

import os
import re
import csv
import json
import time
from typing import Dict, Any, List, Optional, Tuple

from src.storage.db import QuechuaDB
from src.segmentation.scaffold import ScaffoldBuilder
from src.segmentation.normalizer import QuechuaNormalizer
from src.indexer.syntactic_enricher import SyntacticEnricher


# Lexicón complementario de clases cerradas (pronombres, partículas, interrogativos, variantes Collao/Puno)
# para enriquecer tokens no presentes en diccionarios tradicionales de lemas abiertos (sustantivos/verbos).
CLOSED_CLASS_LEXICON = {
    "nuqa": {"lemma": "ñoqa", "pos": "pron.", "def": "Pronombre 1SG (yo). Variante regional Collao/Puno."},
    "ñoqa": {"lemma": "ñoqa", "pos": "pron.", "def": "Pronombre 1SG (yo)."},
    "qan": {"lemma": "qan", "pos": "pron.", "def": "Pronombre 2SG (tú)."},
    "qam": {"lemma": "qan", "pos": "pron.", "def": "Pronombre 2SG (tú)."},
    "pay": {"lemma": "pay", "pos": "pron.", "def": "Pronombre 3SG (él/ella)."},
    "nuqanchis": {"lemma": "ñoqanchis", "pos": "pron.", "def": "Pronombre 1PL.INCL (nosotros incluyente: tú y yo)."},
    "ñoqanchis": {"lemma": "ñoqanchis", "pos": "pron.", "def": "Pronombre 1PL.INCL (nosotros incluyente: tú y yo)."},
    "nuqayku": {"lemma": "ñoqayku", "pos": "pron.", "def": "Pronombre 1PL.EXCL (nosotros excluyente: nosotros sin ti)."},
    "ñoqayku": {"lemma": "ñoqayku", "pos": "pron.", "def": "Pronombre 1PL.EXCL (nosotros excluyente: nosotros sin ti)."},
    "qankuna": {"lemma": "qankuna", "pos": "pron.", "def": "Pronombre 2PL (ustedes)."},
    "paykuna": {"lemma": "paykuna", "pos": "pron.", "def": "Pronombre 3PL (ellos/ellas)."},
    "mana": {"lemma": "mana", "pos": "adv.", "def": "Partícula de negación (no)."},
    "ama": {"lemma": "ama", "pos": "adv.", "def": "Partícula prohibitiva (no, no hagas)."},
    "arí": {"lemma": "arí", "pos": "adv.", "def": "Partícula afirmativa (sí)."},
    "ima": {"lemma": "ima", "pos": "pron. / adv.", "def": "¿Qué?, qué, algo."},
    "pi": {"lemma": "pi", "pos": "pron.", "def": "¿Quién?, quién, alguien."},
    "may": {"lemma": "may", "pos": "adv.", "def": "¿Dónde?, dónde."},
    "mayqan": {"lemma": "mayqan", "pos": "pron.", "def": "¿Cuál?, cuál."},
    "hayk'a": {"lemma": "hayk'a", "pos": "adv.", "def": "¿Cuánto?, cuánto."},
    "imayna": {"lemma": "imayna", "pos": "adv.", "def": "¿Cómo?, cómo."},
    "icha": {"lemma": "icha", "pos": "conj.", "def": "O, quizás, tal vez."},
    "ichaqa": {"lemma": "ichaqa", "pos": "conj.", "def": "Pero, sin embargo, en cambio."},
    "aswan": {"lemma": "aswan", "pos": "adv.", "def": "Más, antes bien, mejor."},
    "ashwan": {"lemma": "aswan", "pos": "adv.", "def": "Más, antes bien (variante Puno)."},
    "ancha": {"lemma": "ancha", "pos": "adv.", "def": "Muy, bastante, sumamente."},
    "hina": {"lemma": "hina", "pos": "adv.", "def": "Así, como, tal como."},
    "hinaqa": {"lemma": "hinaqa", "pos": "adv. / conj.", "def": "Entonces, siendo así."},
    "chaymanta": {"lemma": "chaymanta", "pos": "adv.", "def": "Luego, después, de allí."},
    "chaymi": {"lemma": "chaymi", "pos": "adv. / conj.", "def": "Por eso, es que."},
    "ña": {"lemma": "ña", "pos": "adv.", "def": "Ya (partícula aspectual)."},
    "kunan": {"lemma": "kunan", "pos": "adv. / s.", "def": "Ahora, hoy."},
    "huq": {"lemma": "huk", "pos": "adj. / pron.", "def": "Uno, un, otro (variante fonética Collao)."},
    "uq": {"lemma": "huk", "pos": "adj. / pron.", "def": "Uno, un, otro (variante fonética Collao)."},
    "ishkay": {"lemma": "iskay", "pos": "adj.", "def": "Dos (variante Puno de iskay)."},
    "qhichwa": {"lemma": "qheswa", "pos": "s. / adj.", "def": "Quechua, lengua quechua, zona geográfica."},
    "qichwa": {"lemma": "qheswa", "pos": "s. / adj.", "def": "Quechua, lengua quechua."},
    "punu": {"lemma": "puno", "pos": "prop.", "def": "Puno (topónimo / región altiplánica)."},
    "ashkha": {"lemma": "askha", "pos": "adj.", "def": "Mucho, bastante (variante de askha)."},
    "pasaq": {"lemma": "pasaq", "pos": "adv.", "def": "Completamente, mucho, continuo."},
    "pasaqta": {"lemma": "pasaqta", "pos": "adv.", "def": "Completamente, intensamente."}
}


class CorpusPipeline:
    """Pipeline de extracción, segmentación y enriquecimiento sintáctico del corpus."""

    def __init__(self, db: Optional[QuechuaDB] = None, db_path: Optional[str] = None):
        self.scaffold_builder = ScaffoldBuilder(db=db, db_path=db_path)
        self.db = self.scaffold_builder.db

    def split_sentences_with_spans(self, text: str) -> List[Tuple[int, int, str]]:
        """
        Divide un texto en oraciones respetando delimitadores (.!?), retornando
        tuplas de (start_offset, end_offset, texto_oracion).
        """
        sent_spans = []
        start = 0
        for m in re.finditer(r'([.!?]+(?:\s+|$))', text):
            end = m.end()
            sent_text = text[start:end].strip()
            if sent_text:
                sent_spans.append((start, start + len(sent_text), sent_text))
            start = end
        if start < len(text) and text[start:].strip():
            sent_spans.append((start, len(text), text[start:].strip()))
        return sent_spans if sent_spans else [(0, len(text), text.strip())]

    def extract_tokens_with_spans(self, sentence_text: str, sentence_start: int) -> List[Tuple[int, int, str]]:
        """
        Extrae tokens de palabras y signos ortográficos con sus índices de caracteres globales.
        """
        pattern = r"([A-Za-zÁÉÍÓÚáéíóúÑñ'’`]+|[.,;:!?¿¡\"()«»—-])"
        tokens = []
        for m in re.finditer(pattern, sentence_text):
            tok_str = m.group(0)
            t_start = sentence_start + m.start()
            t_end = sentence_start + m.end()
            tokens.append((t_start, t_end, tok_str))
        return tokens

    def enrich_word(self, word: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Descompone una palabra usando ScaffoldBuilder y enriquece morfosintácticamente.
        Aplica fallback de clases cerradas si no se encontró en el diccionario léxico.
        """
        raw_scaffold = self.scaffold_builder.build_word_scaffold(word)
        is_punct = raw_scaffold.get("is_punct", False)

        root = raw_scaffold.get("root", word)
        canonical_lemma = raw_scaffold.get("canonical_lemma", root)
        pos = raw_scaffold.get("pos", "desconocido")
        found = raw_scaffold.get("found_in_dict", False)
        senses = raw_scaffold.get("senses", [])
        suffixes = raw_scaffold.get("suffixes", [])

        # Fallback para clases cerradas y variantes dialectales frecuentes
        if not found and not is_punct:
            w_lower = word.lower().replace("’", "'").replace("`", "'")
            # Probar coincidencia exacta o de prefijo con CLOSED_CLASS_LEXICON
            for stem, info in CLOSED_CLASS_LEXICON.items():
                if w_lower == stem:
                    root = stem
                    canonical_lemma = info["lemma"]
                    pos = info["pos"]
                    found = True
                    senses = [{"sense_index": 1, "definition": info["def"], "pos": info["pos"]}]
                    suffixes = []
                    break
                elif w_lower.startswith(stem) and len(w_lower) > len(stem):
                    rem = w_lower[len(stem):]
                    # Si el resto es una cadena de sufijos reconocibles
                    peeled_rem = self.scaffold_builder.peeler._peel_fallback(rem) or ("", [f"-{rem}"])
                    cand_suffixes = []
                    for s in peeled_rem[1]:
                        clean_s = s.lstrip("-").rstrip("-")
                        suff_data = self.db.get_suffix(clean_s)
                        if suff_data:
                            cand_suffixes.append({
                                "morpheme": f"-{clean_s}",
                                "name": suff_data["subcategory"] or suff_data["category"] or suff_data["type"],
                                "slot": suff_data["slot_order"],
                                "category": suff_data["category"],
                                "role": suff_data["definition"]
                            })
                        else:
                            cand_suffixes.append({
                                "morpheme": f"-{clean_s}",
                                "name": "Sufijo Gramatical",
                                "slot": 5,
                                "category": "DESCONOCIDO",
                                "role": f"Sufijo morfológico -{clean_s}"
                            })
                    root = stem
                    canonical_lemma = info["lemma"]
                    pos = info["pos"]
                    found = True
                    senses = [{"sense_index": 1, "definition": info["def"], "pos": info["pos"]}]
                    suffixes = cand_suffixes
                    break

        # Construir desglose ordenado de morfemas
        morpheme_chain = [root]
        for s in suffixes:
            morpheme_chain.append(s["morpheme"])

        # Enriquecimiento sintáctico detallado
        syntactic_info = SyntacticEnricher.enrich_token(
            surface=word,
            root=root,
            pos=pos,
            suffixes=suffixes,
            is_punct=is_punct
        )

        morphology = {
            "root": root,
            "canonical_lemma": canonical_lemma,
            "pos": pos,
            "found_in_dict": found,
            "is_compound": raw_scaffold.get("is_compound", False),
            "morpheme_chain": morpheme_chain,
            "senses": senses,
            "suffixes": suffixes
        }

        return morphology, syntactic_info

    def process_record(self, row: Dict[str, str], global_token_counter: int) -> Dict[str, Any]:
        """Procesa una fila completa del TSV de Common Voice."""
        audio_id = row.get("audio_id", "").strip()
        audio_file = row.get("audio_file", "").strip()
        duration_ms = int(row.get("duration_ms", "0") or "0")
        prompt_id = row.get("prompt_id", "").strip()
        prompt_text = row.get("prompt", "").strip()
        transcription = row.get("transcription", "").strip()
        split = row.get("split", "").strip()
        client_id = row.get("client_id", "").strip()
        age = row.get("age", "").strip()
        gender = row.get("gender", "").strip()
        accents = row.get("accents", "").strip()
        quality_tags = [t.strip() for t in row.get("quality_tags", "").split("|") if t.strip()]

        total_chars = max(len(transcription), 1)

        # Segmentar en oraciones con sus rangos de caracteres
        sentence_spans = self.split_sentences_with_spans(transcription)

        processed_sentences = []
        doc_tokens = []
        evidentials_doc = set()
        clusivity_doc = set()
        word_count = 0

        for sent_idx, (s_start, s_end, s_text) in enumerate(sentence_spans):
            token_tuples = self.extract_tokens_with_spans(s_text, s_start)
            sent_token_objects = []

            for t_idx, (t_start, t_end, t_surface) in enumerate(token_tuples):
                is_punct = bool(re.match(r"^[.,;:!?¿¡\"()«»—-]+$", t_surface))
                if not is_punct:
                    word_count += 1

                # Estimación temporal proporcional en milisegundos dentro del audio
                t_time_start_ms = int((t_start / total_chars) * duration_ms)
                t_time_end_ms = int((t_end / total_chars) * duration_ms)

                morphology, syntactic_info = self.enrich_word(t_surface)

                if syntactic_info.get("evidentiality"):
                    evidentials_doc.add(syntactic_info["evidentiality"])
                if syntactic_info.get("clusivity"):
                    clusivity_doc.add(syntactic_info["clusivity"])

                token_obj = {
                    "token_index": t_idx,
                    "global_token_index": global_token_counter,
                    "surface": t_surface,
                    "surface_normalized": QuechuaNormalizer.clean_token(t_surface).lower(),
                    "is_punct": is_punct,
                    "char_span": [t_start, t_end],
                    "approx_time_ms": [t_time_start_ms, t_time_end_ms],
                    "morphology": morphology,
                    "syntactic_enrichment": syntactic_info
                }

                global_token_counter += 1
                sent_token_objects.append(token_obj)
                doc_tokens.append(token_obj)

            processed_sentences.append({
                "sentence_index": sent_idx,
                "text": s_text,
                "char_span": [s_start, s_end],
                "tokens": sent_token_objects
            })

        doc = {
            "audio_id": audio_id,
            "audio_file": audio_file,
            "media_rel_path": os.path.join("data", "raw", "sps-corpus-5.0-2026-09-11-qxp", "audios", audio_file),
            "duration_ms": duration_ms,
            "split": split,
            "speaker": {
                "client_id": client_id,
                "age": age,
                "gender": gender,
                "accents": accents
            },
            "prompt": {
                "prompt_id": prompt_id,
                "text": prompt_text
            },
            "transcription": transcription,
            "quality_tags": quality_tags,
            "linguistic_summary": {
                "evidentials": sorted(list(evidentials_doc)),
                "clusivity": sorted(list(clusivity_doc)),
                "total_words": word_count,
                "total_tokens": len(doc_tokens)
            },
            "sentences": processed_sentences
        }

        return doc, global_token_counter

    def run(self, tsv_path: str, output_path: str) -> Dict[str, Any]:
        """Ejecuta el pipeline completo sobre el corpus TSV y guarda el JSON enriquecido."""
        print(f"[*] Iniciando pipeline de corpus: {tsv_path}")
        start_time = time.time()

        if not os.path.exists(tsv_path):
            raise FileNotFoundError(f"No se encontró el corpus en: {tsv_path}")

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        rows_with_transcription = []
        total_raw_rows = 0

        with open(tsv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for r in reader:
                total_raw_rows += 1
                trans = r.get("transcription", "").strip()
                if trans:
                    rows_with_transcription.append(r)

        print(f"[*] Filas totales en el corpus: {total_raw_rows}")
        print(f"[*] Filas con transcripción activa: {len(rows_with_transcription)}")

        documents = []
        global_token_counter = 0
        dict_found_words = 0
        total_words = 0

        for idx, row in enumerate(rows_with_transcription, start=1):
            doc, global_token_counter = self.process_record(row, global_token_counter)
            documents.append(doc)

            for s in doc["sentences"]:
                for t in s["tokens"]:
                    if not t["is_punct"]:
                        total_words += 1
                        if t["morphology"]["found_in_dict"]:
                            dict_found_words += 1

            if idx % 200 == 0 or idx == len(rows_with_transcription):
                pct = (idx / len(rows_with_transcription)) * 100
                cov = (dict_found_words / max(total_words, 1)) * 100
                print(f"    -> Procesados {idx}/{len(rows_with_transcription)} ({pct:.1f}%) | Cobertura léxica: {cov:.1f}%")

        coverage_pct = round((dict_found_words / max(total_words, 1)) * 100, 2)
        elapsed_sec = round(time.time() - start_time, 2)

        output_data = {
            "corpus_info": {
                "corpus_id": "sps-corpus-5.0-2026-09-11-qxp",
                "language": "Puno Quechua (qxp)",
                "source_file": tsv_path,
                "total_rows_in_raw": total_raw_rows,
                "transcribed_rows_count": len(rows_with_transcription),
                "untranscribed_rows_count": total_raw_rows - len(rows_with_transcription),
                "total_words_count": total_words,
                "total_tokens_count": global_token_counter,
                "lexical_coverage_pct": coverage_pct,
                "processing_time_sec": elapsed_sec,
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            },
            "documents": documents
        }

        print(f"[*] Guardando JSON estructurado en: {output_path}...")
        with open(output_path, "w", encoding="utf-8") as f_out:
            json.dump(output_data, f_out, ensure_ascii=False, indent=2)

        file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"[✓] Pipeline completado con éxito en {elapsed_sec}s.")
        print(f"[✓] Archivo generado: {output_path} ({file_size_mb:.2f} MB)")
        print(f"[✓] Total documentos: {len(documents)}, Total palabras: {total_words}, Cobertura: {coverage_pct}%")

        return output_data["corpus_info"]


if __name__ == "__main__":
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    tsv_file = os.path.join(repo_root, "data", "raw", "sps-corpus-5.0-2026-09-11-qxp", "ss-corpus-qxp.tsv")
    output_json = os.path.join(repo_root, "data", "processed", "corpus_tokenized.json")

    pipeline = CorpusPipeline()
    pipeline.run(tsv_file, output_json)
