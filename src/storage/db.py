"""
Módulo de almacenamiento y consulta para el conocimiento léxico y morfológico del quechua.
Implementa acceso relacional y de texto completo con SQLite FTS5.
"""

import sqlite3
import os
import re
from typing import List, Dict, Any, Optional, Set, Tuple


SCHEMA_SQL = """
-- 1. Fuentes bibliográficas
CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    edition TEXT,
    notes TEXT
);

-- 2. Lemas (Headwords) del quechua
CREATE TABLE IF NOT EXISTS lemmas (
    lemma_id INTEGER PRIMARY KEY AUTOINCREMENT,
    headword TEXT NOT NULL,
    headword_normalized TEXT NOT NULL,
    headword_phonetic TEXT NOT NULL,
    pos TEXT NOT NULL,
    dialect_origin TEXT DEFAULT 'cuz',
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    page_number INTEGER
);

CREATE INDEX IF NOT EXISTS idx_lemmas_hw ON lemmas(headword);
CREATE INDEX IF NOT EXISTS idx_lemmas_norm ON lemmas(headword_normalized);
CREATE INDEX IF NOT EXISTS idx_lemmas_phon ON lemmas(headword_phonetic);

-- 3. Acepciones (Senses) por lema (resuelve la polisemia)
CREATE TABLE IF NOT EXISTS senses (
    sense_id INTEGER PRIMARY KEY AUTOINCREMENT,
    lemma_id INTEGER NOT NULL REFERENCES lemmas(lemma_id) ON DELETE CASCADE,
    sense_index INTEGER NOT NULL,
    definition_es TEXT NOT NULL,
    semantic_domain TEXT,
    register_level TEXT,
    synonyms TEXT,
    dialect_variants TEXT
);

CREATE INDEX IF NOT EXISTS idx_senses_lemma ON senses(lemma_id);

-- 4. Ejemplos bilingües
CREATE TABLE IF NOT EXISTS examples (
    example_id INTEGER PRIMARY KEY AUTOINCREMENT,
    lemma_id INTEGER REFERENCES lemmas(lemma_id) ON DELETE CASCADE,
    phrase_qu TEXT NOT NULL,
    translation_es TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_examples_lemma ON examples(lemma_id);

-- 5. Catálogo de sufijos y morfología
CREATE TABLE IF NOT EXISTS suffixes (
    suffix_id INTEGER PRIMARY KEY AUTOINCREMENT,
    morpheme TEXT NOT NULL,
    morpheme_clean TEXT NOT NULL,
    type TEXT NOT NULL,
    subtype TEXT,
    category TEXT,
    subcategory TEXT,
    slot_order INTEGER DEFAULT 5,
    definition TEXT,
    raw_examples TEXT
);

CREATE INDEX IF NOT EXISTS idx_suffixes_clean ON suffixes(morpheme_clean);

-- 6. Alomorfos de sufijos
CREATE TABLE IF NOT EXISTS suffix_allomorphs (
    allomorph_id INTEGER PRIMARY KEY AUTOINCREMENT,
    suffix_id INTEGER NOT NULL REFERENCES suffixes(suffix_id) ON DELETE CASCADE,
    surface_form TEXT NOT NULL,
    context_condition TEXT
);

CREATE INDEX IF NOT EXISTS idx_allomorphs_form ON suffix_allomorphs(surface_form);

-- 7. FTS5 para búsqueda rápida de texto completo
CREATE VIRTUAL TABLE IF NOT EXISTS lemmas_fts USING fts5(
    headword,
    headword_normalized,
    pos,
    definitions,
    content='lemmas',
    content_rowid='lemma_id'
);
"""


class QuechuaDB:
    """Manejador de la base de datos de conocimiento quechua."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            db_path = os.path.join(repo_root, "data", "quechua_knowledge.db")
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None

    def get_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON;")
            self._conn.execute("PRAGMA journal_mode = WAL;")
        return self._conn

    def init_schema(self):
        conn = self.get_connection()
        conn.executescript(SCHEMA_SQL)
        conn.commit()

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    # -----------------------------------------------------------------------
    # Consultas de Lemas
    # -----------------------------------------------------------------------

    def get_lemma(self, word: str) -> Optional[Dict[str, Any]]:
        """Busca un lema por su forma exacta o normalizada (trivocálica)."""
        conn = self.get_connection()
        cur = conn.cursor()
        
        w_lower = word.lower().strip()
        w_norm = self.normalize_trivocalic(w_lower)

        # 1. Búsqueda exacta
        cur.execute(
            "SELECT * FROM lemmas WHERE headword = ? OR headword_normalized = ? LIMIT 1",
            (w_lower, w_norm)
        )
        row = cur.fetchone()
        if not row:
            # 2. Búsqueda fonética secundaria
            cur.execute(
                "SELECT * FROM lemmas WHERE headword_phonetic = ? LIMIT 1",
                (self.to_phonetic(w_norm),)
            )
            row = cur.fetchone()

        if not row:
            return None

        lemma_dict = dict(row)
        lemma_id = lemma_dict["lemma_id"]

        # Recuperar todas las acepciones
        cur.execute(
            "SELECT * FROM senses WHERE lemma_id = ? ORDER BY sense_index ASC",
            (lemma_id,)
        )
        lemma_dict["senses"] = [dict(s) for s in cur.fetchall()]

        # Recuperar ejemplos
        cur.execute(
            "SELECT * FROM examples WHERE lemma_id = ?",
            (lemma_id,)
        )
        lemma_dict["examples"] = [dict(e) for e in cur.fetchall()]

        return lemma_dict

    def search_lemmas(self, query: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Búsqueda por prefijo y FTS5 para autocompletado en terminal."""
        conn = self.get_connection()
        cur = conn.cursor()
        q_lower = query.lower().strip()
        q_norm = self.normalize_trivocalic(q_lower)

        results = []
        seen_ids = set()

        # Prefijo exacto
        cur.execute(
            "SELECT * FROM lemmas WHERE headword_normalized LIKE ? OR headword LIKE ? LIMIT ?",
            (f"{q_norm}%", f"{q_lower}%", limit)
        )
        for row in cur.fetchall():
            d = dict(row)
            if d["lemma_id"] not in seen_ids:
                seen_ids.add(d["lemma_id"])
                cur.execute(
                    "SELECT definition_es FROM senses WHERE lemma_id = ? ORDER BY sense_index ASC LIMIT 2",
                    (d["lemma_id"],)
                )
                d["definitions"] = [s["definition_es"] for s in cur.fetchall()]
                results.append(d)

        # Si faltan resultados, buscar en FTS
        if len(results) < limit:
            try:
                cur.execute(
                    """SELECT rowid AS lemma_id, headword, headword_normalized, pos
                       FROM lemmas_fts WHERE lemmas_fts MATCH ? LIMIT ?""",
                    (f"{q_norm}*", limit - len(results))
                )
                for row in cur.fetchall():
                    d = dict(row)
                    if d["lemma_id"] not in seen_ids:
                        seen_ids.add(d["lemma_id"])
                        cur.execute(
                            "SELECT definition_es FROM senses WHERE lemma_id = ? ORDER BY sense_index ASC LIMIT 2",
                            (d["lemma_id"],)
                        )
                        d["definitions"] = [s["definition_es"] for s in cur.fetchall()]
                        results.append(d)
            except sqlite3.OperationalError:
                pass

        return results

    def get_all_lemma_keys(self) -> Set[str]:
        """Devuelve el conjunto en memoria de todas las raíces conocidas."""
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT headword_normalized FROM lemmas")
        keys = set(row[0] for row in cur.fetchall())
        cur.execute("SELECT headword FROM lemmas")
        keys.update(row[0] for row in cur.fetchall())
        return keys

    # -----------------------------------------------------------------------
    # Consultas de Sufijos
    # -----------------------------------------------------------------------

    def get_suffix(self, suffix_form: str) -> Optional[Dict[str, Any]]:
        """Busca un sufijo por su forma superficial o por sus alomorfos."""
        conn = self.get_connection()
        cur = conn.cursor()
        s_clean = suffix_form.lower().lstrip("-").strip()

        # Búsqueda por morfema principal
        cur.execute(
            "SELECT * FROM suffixes WHERE morpheme_clean = ? LIMIT 1",
            (s_clean,)
        )
        row = cur.fetchone()
        if not row:
            # Búsqueda por alomorfo
            cur.execute(
                """SELECT s.* FROM suffixes s
                   JOIN suffix_allomorphs a ON s.suffix_id = a.suffix_id
                   WHERE a.surface_form = ? LIMIT 1""",
                (s_clean,)
            )
            row = cur.fetchone()

        if row:
            d = dict(row)
            cur.execute(
                "SELECT surface_form, context_condition FROM suffix_allomorphs WHERE suffix_id = ?",
                (d["suffix_id"],)
            )
            d["allomorphs"] = [dict(a) for a in cur.fetchall()]
            return d
        return None

    def get_all_suffixes(self) -> List[Dict[str, Any]]:
        """Devuelve todos los sufijos indexados con sus alomorfos."""
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM suffixes ORDER BY slot_order ASC, length(morpheme_clean) DESC")
        suffixes = [dict(r) for r in cur.fetchall()]
        for s in suffixes:
            cur.execute(
                "SELECT surface_form, context_condition FROM suffix_allomorphs WHERE suffix_id = ?",
                (s["suffix_id"],)
            )
            s["allomorphs"] = [dict(a) for a in cur.fetchall()]
        return suffixes

    # -----------------------------------------------------------------------
    # Utilidades fonológicas
    # -----------------------------------------------------------------------

    @staticmethod
    def normalize_trivocalic(text: str) -> str:
        """Convierte variantes pentavocálicas a trivocálicas canónicas (e->i, o->u) y mp->np."""
        t = text.lower()
        t = t.replace("e", "i").replace("o", "u")
        t = t.replace("mp", "np")
        return t

    @staticmethod
    def to_phonetic(text: str) -> str:
        """Neutraliza oclusivas complejas (aspiradas y glotales) para búsqueda tolerante."""
        t = text.lower()
        t = t.replace("'", "").replace("’", "")
        t = re.sub(r"([ptckq])h", r"\1", t)
        return t
