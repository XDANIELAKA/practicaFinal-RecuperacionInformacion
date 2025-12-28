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
    con = sqlite3.connect(DB_PATH)
    # Opciones de rendimiento
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")
    return con

def init_db():
    """
    Inicializa la base de datos creando todas las tablas
    necesarias para el sistema de recuperación de información.
    """
    con = get_connection()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS docs(
        doc_id INTEGER PRIMARY KEY,
        title TEXT,
        path TEXT UNIQUE,
        length INTEGER
    );

    CREATE TABLE IF NOT EXISTS postings(
        term TEXT,
        doc_id INTEGER,
        tf INTEGER,
        PRIMARY KEY(term, doc_id)
    );

    CREATE TABLE IF NOT EXISTS df(
        term TEXT PRIMARY KEY,
        doc_freq INTEGER
    );

    CREATE TABLE IF NOT EXISTS meta(
        key TEXT PRIMARY KEY,
        value REAL
    );
    """)
    con.commit()

    # Aseguramos que columnas estén presentes
    ensure_columns(con)

    con.close()

def ensure_columns(con):
    """
    Comprueba columnas extras y las agrega si faltan.
    Evita ALTER TABLE si ya existe la columna.
    """
    cursor = con.cursor()

    # Recuperar info de columnas de docs
    cursor.execute("PRAGMA table_info(docs);")
    cols = [row[1] for row in cursor.fetchall()]

    # Lista de columnas necesarias
    required = {
        "title": "TEXT",
        # Agrega aquí otras futuras columnas
    }

    for col, col_type in required.items():
        if col not in cols:
            print(f">>> Agregando columna faltante '{col}' a docs")
            cursor.execute(f"ALTER TABLE docs ADD COLUMN {col} {col_type};")

    con.commit()