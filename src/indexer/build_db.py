"""
Constructor principal de la base de datos de conocimiento quechua (ETAPA 0).
Ingesta entradas lematizadas y sufijos en data/quechua_knowledge.db.
"""

import os
import sys
import time
from src.storage.db import QuechuaDB
from src.indexer.entry_parser import load_and_group_entries
from src.indexer.suffix_parser import parse_suffixes_csv


def build_database(db_path: str = None) -> QuechuaDB:
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if db_path is None:
        db_path = os.path.join(repo_root, "data", "quechua_knowledge.db")

    print(f"[*] Base de datos destino: {db_path}")
    db = QuechuaDB(db_path)
    db.init_schema()

    conn = db.get_connection()
    cur = conn.cursor()

    # 1. Registrar fuentes bibliográficas
    print("[*] Registrando fuentes...")
    cur.execute("""
        INSERT OR REPLACE INTO sources (source_id, title, author, year, notes)
        VALUES 
        ('amlq_cuzco', 'Diccionario Quechua - Español - Quechua, Simi Taqe', 'Academia Mayor de la Lengua Quechua de Cusco', 2005, 'Ortografía cuzqueña pentavocálica con consonantes complejas.'),
        ('calvo_perez_2022', 'Nuevo Diccionario Español - Quechua / Quechua - Español Vol 1', 'Julio Calvo Pérez', 2022, 'Proyecto Lexi-Calvo, Universidad de San Martín de Porres.'),
        ('suffixes_v3', 'Inventario y Gramática de Sufijos Quechuas V3.0', 'Corpus Lingüístico', 2024, 'Inventario taxonómico de sufijos dependientes e independientes.')
    """)
    conn.commit()

    # 2. Ingestar sufijos
    suffixes_csv = os.path.join(repo_root, "input", "sufix", "suffixes - V3.0.csv")
    if os.path.exists(suffixes_csv):
        print(f"[*] Ingestando sufijos desde {suffixes_csv}...")
        parsed_suffixes = parse_suffixes_csv(suffixes_csv)
        for s in parsed_suffixes:
            cur.execute("""
                INSERT INTO suffixes (morpheme, morpheme_clean, type, subtype, category, subcategory, slot_order, definition, raw_examples)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                s["morpheme"], s["morpheme_clean"], s["type"], s["subtype"],
                s["category"], s["subcategory"], s["slot_order"], s["definition"],
                s["raw_examples"]
            ))
            suffix_id = cur.lastrowid
            for allo in s["allomorphs"]:
                cur.execute("""
                    INSERT INTO suffix_allomorphs (suffix_id, surface_form, context_condition)
                    VALUES (?, ?, ?)
                """, (suffix_id, allo, "alomorfo estándar"))
        conn.commit()
        print(f"[✓] {len(parsed_suffixes)} sufijos indexados.")
    else:
        print(f"[!] Archivo de sufijos no encontrado: {suffixes_csv}")

    # 3. Ingestar entradas del diccionario (entries.json)
    entries_json = os.path.join(repo_root, "input", "paqocha-fst", "data", "entries.json")
    if os.path.exists(entries_json):
        print(f"[*] Ingestando diccionario desde {entries_json}...")
        start_time = time.time()
        grouped_lemmas = load_and_group_entries(entries_json)
        
        cur.execute("BEGIN TRANSACTION;")
        total_senses = 0
        for lemma in grouped_lemmas:
            cur.execute("""
                INSERT INTO lemmas (headword, headword_normalized, headword_phonetic, pos, source_id)
                VALUES (?, ?, ?, ?, ?)
            """, (
                lemma["headword"], lemma["headword_normalized"],
                lemma["headword_phonetic"], lemma["pos"], lemma["source_id"]
            ))
            lemma_id = cur.lastrowid
            
            def_preview = []
            for s in lemma["senses"]:
                cur.execute("""
                    INSERT INTO senses (lemma_id, sense_index, definition_es, semantic_domain, synonyms, dialect_variants)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    lemma_id, s["sense_index"], s["definition_es"],
                    s.get("semantic_domain"), s.get("synonyms"), s.get("dialect_variants")
                ))
                def_preview.append(s["definition_es"])
                total_senses += 1

            # Insertar en FTS5
            cur.execute("""
                INSERT INTO lemmas_fts (rowid, headword, headword_normalized, pos, definitions)
                VALUES (?, ?, ?, ?, ?)
            """, (
                lemma_id, lemma["headword"], lemma["headword_normalized"],
                lemma["pos"], " | ".join(def_preview)
            ))

        conn.commit()
        elapsed = time.time() - start_time
        print(f"[✓] {len(grouped_lemmas)} lemas y {total_senses} acepciones indexadas en {elapsed:.2f}s.")
    else:
        print(f"[!] Archivo de entradas no encontrado: {entries_json}")

    return db


if __name__ == "__main__":
    db = build_database()
    print("\n--- Verificación rápida de consultas ---")
    test_words = ["wasi", "allpaqa", "yachay", "runa"]
    for w in test_words:
        res = db.get_lemma(w)
        if res:
            print(f"Lema '{w}' -> POS: {res['pos']}, Acepciones: {len(res['senses'])}")
            for s in res["senses"][:2]:
                print(f"   [{s['sense_index']}] {s['definition_es'][:70]}...")
        else:
            print(f"Lema '{w}' -> NO encontrado")

    test_suffixes = ["kuna", "man", "mi", "y"]
    for s in test_suffixes:
        res = db.get_suffix(s)
        if res:
            print(f"Sufijo '-{s}' -> Categoría: {res['category']}, Slot: {res['slot_order']}, Def: {res['definition'][:50]}...")
        else:
            print(f"Sufijo '-{s}' -> NO encontrado")
    db.close()
