"""
Pruebas de validación para el pipeline de corpus (Fase 2) y el índice invertido (Fase 3).
"""

import os
import json
import unittest

from src.indexer.inverted_index import QuechuaCorpusSearcher


class TestCorpusPipelineAndInvertedIndex(unittest.TestCase):
    """Verifica la integridad de corpus_tokenized.json e inverted_index.json."""

    @classmethod
    def setUpClass(cls):
        cls.repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cls.corpus_json = os.path.join(cls.repo_root, "data", "processed", "corpus_tokenized.json")
        cls.index_json = os.path.join(cls.repo_root, "data", "processed", "inverted_index.json")
        cls.media_catalog_json = os.path.join(cls.repo_root, "data", "processed", "media_catalog.json")

    def test_corpus_tokenized_file_integrity(self):
        """Verifica que el archivo de corpus tokenizado exista y tenga la estructura esperada."""
        self.assertTrue(os.path.exists(self.corpus_json), "corpus_tokenized.json debe existir")
        with open(self.corpus_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertIn("corpus_info", data)
        self.assertIn("documents", data)

        info = data["corpus_info"]
        self.assertEqual(info["transcribed_rows_count"], 1222)
        self.assertGreaterEqual(info["total_words_count"], 20000)
        self.assertGreaterEqual(info["lexical_coverage_pct"], 80.0)

        # Verificar primer documento
        doc0 = data["documents"][0]
        self.assertIn("audio_id", doc0)
        self.assertIn("audio_file", doc0)
        self.assertIn("transcription", doc0)
        self.assertIn("sentences", doc0)
        self.assertGreater(len(doc0["sentences"]), 0)

        # Validar offsets exactos de caracteres
        trans = doc0["transcription"]
        for sent in doc0["sentences"]:
            for tok in sent["tokens"]:
                start, end = tok["char_span"]
                self.assertEqual(trans[start:end], tok["surface"])
                self.assertIn("morphology", tok)
                self.assertIn("syntactic_enrichment", tok)

    def test_inverted_index_integrity(self):
        """Verifica que el índice invertido y el catálogo multimedia estén separados limpiamente."""
        self.assertTrue(os.path.exists(self.index_json), "inverted_index.json debe existir")
        self.assertTrue(os.path.exists(self.media_catalog_json), "media_catalog.json debe existir")

        with open(self.index_json, "r", encoding="utf-8") as f:
            idx_data = json.load(f)

        self.assertIn("index_info", idx_data)
        self.assertIn("words_index", idx_data)
        self.assertIn("lemmas_index", idx_data)
        self.assertIn("syntax_index", idx_data)
        self.assertNotIn("media_catalog", idx_data, "media_catalog debe estar desacoplado de inverted_index.json")

        self.assertGreater(len(idx_data["words_index"]), 5000)
        self.assertGreater(len(idx_data["lemmas_index"]), 2000)

        with open(self.media_catalog_json, "r", encoding="utf-8") as f:
            cat_data = json.load(f)

        self.assertIn("catalog_info", cat_data)
        self.assertIn("clips", cat_data)
        self.assertEqual(len(cat_data["clips"]), 1222)

    def test_search_by_surface_and_syntactic_enrichment(self):
        """Verifica que la búsqueda por palabra devuelva el enriquecimiento sintáctico y los clips."""
        searcher = QuechuaCorpusSearcher(self.index_json)
        self.assertEqual(len(searcher.media_catalog), 1222)
        clip = searcher.get_clip_metadata("34189")
        self.assertIsNotNone(clip)
        self.assertEqual(clip["audio_file"], "spontaneous-speech-qxp-34189.mp3")
        result = searcher.search("Taytayqa")

        self.assertEqual(result["match_type"], "surface")
        self.assertEqual(result["lemma"], "tayta")
        self.assertIn("syntactic_enrichment", result)

        syntax = result["syntactic_enrichment"]
        self.assertEqual(syntax["case"], "nominativo")
        self.assertIn("tópico (-qa)", syntax["pragmatics"])

        # Verificar postings
        postings = result["postings"]
        self.assertGreater(len(postings), 0)
        p0 = postings[0]
        self.assertEqual(p0["audio_id"], "34189")
        self.assertEqual(p0["audio_file"], "spontaneous-speech-qxp-34189.mp3")
        self.assertIn("approx_time_ms", p0)
        self.assertIn("Taytayqa", p0["context_snippet"])

    def test_search_by_lemma(self):
        """Verifica que la búsqueda por lema recupere todas sus variantes flexionadas y sus clips."""
        searcher = QuechuaCorpusSearcher(self.index_json)
        result = searcher.search_by_lemma("wasi")

        self.assertEqual(result["match_type"], "lemma")
        self.assertEqual(result["lemma"], "wasi")
        self.assertGreater(len(result["surface_forms"]), 1)
        self.assertGreater(len(result["postings"]), 0)


if __name__ == "__main__":
    unittest.main()
