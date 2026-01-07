import sqlite3
import os

from app.core.paths import data_index_dir

# ===== DEFINICIÓN DE RUTA GLOBAL PARA LA BASE DE DATOS =====
# Usamos la función data_index_dir() para que siempre
# apunte a: martinez_infantes_daniel_pFinal/data/index
DATA_INDEX_DIRECTORY = data_index_dir()
DB_PATH = os.path.join(DATA_INDEX_DIRECTORY, "ri_index.db")
# ============================================================

def get_connection():
    """
    Devuelve una conexión SQLite a la base de datos
    ri_index.db en la ruta global de índice.
    """
    # Aseguramos que exista el directorio primero
    os.makedirs(DATA_INDEX_DIRECTORY, exist_ok=True)

    con = sqlite3.connect(DB_PATH)
    # Opciones de rendimiento
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")
    con.execute("PRAGMA foreign_keys=ON;")
    return con

def init_db():
    """
    Inicializa la base de datos creando todas las tablas
    necesarias para el sistema de recuperación de información.
    """
    con = get_connection()
    cur = con.cursor()

    # === Crear esquema base si no existe ===
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS docs(
        doc_id INTEGER PRIMARY KEY,
        url TEXT UNIQUE,
        title TEXT,
        path TEXT UNIQUE,
        length INTEGER
    );

    CREATE TABLE IF NOT EXISTS postings(
        term TEXT,
        doc_id INTEGER,
        tf INTEGER,
        PRIMARY KEY (term, doc_id)
    );

    CREATE TABLE IF NOT EXISTS df(
        term TEXT PRIMARY KEY,
        doc_freq INTEGER
    );

    CREATE TABLE IF NOT EXISTS meta(
        key TEXT PRIMARY KEY,
        value REAL
    );

    CREATE TABLE IF NOT EXISTS links(
        from_doc_id INTEGER,
        to_doc_id INTEGER,
        FOREIGN KEY(from_doc_id) REFERENCES docs(doc_id),
        FOREIGN KEY(to_doc_id)   REFERENCES docs(doc_id)
    );

    CREATE TABLE IF NOT EXISTS pagerank(
        doc_id INTEGER PRIMARY KEY,
        rank REAL,
        FOREIGN KEY(doc_id) REFERENCES docs(doc_id)
    );
    """)

    # === Índices para acelerar consultas sobre el grafo ===
    cur.executescript("""
    CREATE INDEX IF NOT EXISTS idx_links_from ON links(from_doc_id);
    CREATE INDEX IF NOT EXISTS idx_links_to   ON links(to_doc_id);
    CREATE INDEX IF NOT EXISTS idx_postings_term ON postings(term);
    CREATE INDEX IF NOT EXISTS idx_postings_doc  ON postings(doc_id);
    """)

    con.commit()

    # === Asegurar columnas adicionales si faltan ===
    ensure_columns(con)

    con.close()

def ensure_columns(con):
    """
    Comprueba columnas extras y las agrega si faltan.
    Esto puede ser útil cuando se actualiza el esquema.
    """
    cursor = con.cursor()

    # ---- Revisar columnas en docs ----
    cursor.execute("PRAGMA table_info(docs);")
    cols = [row[1] for row in cursor.fetchall()]

    # columnas que queremos garantizar
    required_cols = {
        "url": "TEXT",
        "title": "TEXT",
        "path": "TEXT",
        "length": "INTEGER"
    }

    for col, col_type in required_cols.items():
        if col not in cols:
            print(f">>> Agregando columna faltante '{col}' a docs")
            cursor.execute(f"ALTER TABLE docs ADD COLUMN {col} {col_type};")

    # ---- Revisar columnas en pagerank ----
    cursor.execute("PRAGMA table_info(pagerank);")
    pr_cols = [row[1] for row in cursor.fetchall()]

    if "rank" not in pr_cols:
        print(">>> Agregando columna 'rank' a pagerank")
        cursor.execute("ALTER TABLE pagerank ADD COLUMN rank REAL;")

    con.commit()

def reset_db():
    """
    Borra todas las tablas de la base de datos para un reinicio completo.
    (Útil durante desarrollo)
    """
    con = get_connection()
    cur = con.cursor()

    cur.executescript("""
    -- Primero las tablas dependientes
    DELETE FROM postings;
    DELETE FROM links;

    -- Luego las tablas independientes
    DELETE FROM docs;
    DELETE FROM df;
    DELETE FROM meta;
    """)

    con.commit()
    con.close()
    print("Base de datos reiniciada (todas las tablas borradas).")