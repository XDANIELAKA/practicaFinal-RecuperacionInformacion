from typing import Dict
import os
from app.core.textproc import normalize_text, tokenize_text, remove_stopwords
from .storage import get_connection
from .storage import init_db

def init_db():
    con = get_connection()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS docs(
        doc_id INTEGER PRIMARY KEY,
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
    return con

def extract_title(raw_text: str) -> str:
    """
    Intenta extraer título usando un parseo simple.
    Si no hay título explícito, devolvemos las primeras palabras.
    """
    try:
        soup = BeautifulSoup(raw_text, "html.parser")
        if soup.title and soup.title.string:
            return soup.title.string.strip()
    except Exception:
        pass

    # fallback: primeras 8 palabras del texto normalizado
    words = normalize_text(raw_text).split()
    return " ".join(words[:8]) + "..."

def index_documents(raw_dir: str):
    con = init_db()

    # borrar índice viejo
    con.execute("DELETE FROM docs;")
    con.execute("DELETE FROM postings;")
    con.execute("DELETE FROM df;")
    con.execute("DELETE FROM meta;")
    con.commit()

    N = 0
    total_len = 0
    df_counts: Dict[str,int] = {}

    files = sorted(os.listdir(raw_dir))
    for filename in files:
        path = os.path.join(raw_dir, filename)
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            raw_text = f.read()

        # extraer título
        title = extract_title(raw_text)

        normalized = normalize_text(raw_text)
        tokens = tokenize_text(normalized)
        filtered = remove_stopwords(tokens)

        if not filtered:
            continue

        doc_id = N + 1
        con.execute(
            "INSERT INTO docs(doc_id, title, path, length) VALUES(?,?,?,?)",
            (doc_id, title, path, len(filtered))
        )

        tf: Dict[str,int] = {}
        for t in filtered:
            tf[t] = tf.get(t, 0) + 1

        for term, freq in tf.items():
            con.execute(
                "INSERT OR REPLACE INTO postings(term, doc_id, tf) VALUES(?,?,?)",
                (term, doc_id, freq)
            )
            df_counts[term] = df_counts.get(term, 0) + 1

        N += 1
        total_len += len(filtered)

    for term, df in df_counts.items():
        con.execute(
            "INSERT OR REPLACE INTO df(term, doc_freq) VALUES(?,?)",
            (term, df)
        )

    avgdl = (total_len / N) if N > 0 else 0.0
    con.execute("INSERT OR REPLACE INTO meta(key, value) VALUES(?,?)", ("N", N))
    con.execute("INSERT OR REPLACE INTO meta(key, value) VALUES(?,?)", ("avgdl", avgdl))

    con.commit()
    con.close()

    return {"indexed_docs": N, "avgdl": avgdl}