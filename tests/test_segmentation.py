"""
Pruebas unitarias para el motor de segmentación morfosintáctica y scaffold.
"""

import unittest
import os
import sys

# Asegurar importación de src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.storage.db import QuechuaDB
from src.segmentation.normalizer import QuechuaNormalizer
from src.segmentation.slots import MorphotacticValidator
from src.segmentation.peeler import MorphemePeeler
from src.segmentation.scaffold import ScaffoldBuilder


class TestQuechuaSegmentation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db = QuechuaDB()
        cls.peeler = MorphemePeeler(cls.db)
        cls.scaffold_builder = ScaffoldBuilder(cls.db)

    def test_normalizer(self):
        self.assertEqual(QuechuaNormalizer.to_trivocalic("qheswa"), "qhiswa")
        self.assertEqual(QuechuaNormalizer.to_trivocalic("orqo"), "urqu")
        self.assertEqual(QuechuaNormalizer.to_phonetic("k'aspi"), "kaspi")
        self.assertEqual(QuechuaNormalizer.to_phonetic("thanta"), "tanta")

    def test_slot_validator(self):
        # -kuna (4) -> -man (5) -> -mi (9) : Válido
        self.assertTrue(MorphotacticValidator.is_valid_sequence(["kuna", "man", "mi"]))
        # -mi (9) -> -kuna (4) : Inválido
        self.assertFalse(MorphotacticValidator.is_valid_sequence(["mi", "kuna"]))

    def test_direct_lemma(self):
        res = self.peeler.segment_word("wasi")
        self.assertEqual(res["root"], "wasi")
        self.assertEqual(res["suffixes"], [])
        self.assertTrue(res["found"])

    def test_regular_inflection_wasikunamanmi(self):
        res = self.peeler.segment_word("wasikunamanmi")
        self.assertEqual(res["root"], "wasi")
        self.assertEqual(res["suffixes"], ["kuna", "man", "mi"])
        self.assertTrue(res["found"])

    def test_euphonic_ni_yawarniy(self):
        res = self.peeler.segment_word("yawarniy")
        self.assertEqual(res["root"], "yawar")
        self.assertIn("-ni-", res["suffixes"])
        self.assertIn("y", res["suffixes"])
        self.assertTrue(res["found"])

    def test_case_allpaqamanta(self):
        res = self.peeler.segment_word("allpaqamanta")
        self.assertEqual(res["root"], "allpaqa")
        self.assertEqual(res["suffixes"], ["manta"])
        self.assertTrue(res["found"])

    def test_verbal_aspect_pukllashanchis(self):
        res = self.peeler.segment_word("pukllashanchis")
        self.assertIn("puklla", res["root"])
        self.assertIn("sha", res["suffixes"])
        self.assertIn("nchis", res["suffixes"])

    def test_compound_allpamayupi(self):
        res = self.peeler.segment_word("allpamayupi")
        self.assertTrue(res["is_compound"] or res["found"])
        self.assertIn("pi", res["suffixes"])

    def test_sentence_scaffold(self):
        sentence = "Taytayqa uywa hampiqmi."
        scaffold = self.scaffold_builder.build_sentence_scaffold(sentence)
        self.assertEqual(scaffold["tokens_count"], 4)  # Taytayqa, uywa, hampiqmi, .
        # Verificar que detecta evidencial directo
        self.assertTrue(any("DIRECTO" in ev for ev in scaffold["linguistic_markers"]["evidentials"]))


if __name__ == "__main__":
    unittest.main()
