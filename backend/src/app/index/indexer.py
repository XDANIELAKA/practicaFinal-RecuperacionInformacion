from typing import Dict
from bs4 import BeautifulSoup
import os
import json

from app.core.textproc import normalize_text, tokenize_text, remove_stopwords
from app.core.crawler import extract_links, normalize_url, extract_metadata
from .storage import get_connection

def extract_visible_text(html: str) -> str:
    """
    Devuelve sólo el texto visible de un HTML limpio.
    """
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator=" ", strip=True)

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
    """
    Indexa todos los .txt en raw_dir.
    Guarda en docs, postings, df, meta y links.
    """

    con = get_connection()

    # --- borrar índice viejo excepto estructura de tablas ---
    con.execute("DELETE FROM docs;")
    con.execute("DELETE FROM postings;")
    con.execute("DELETE FROM df;")
    con.execute("DELETE FROM meta;")
    con.execute("DELETE FROM links;")
    con.commit()

    N = 0
    total_len = 0
    df_counts: Dict[str,int] = {}

    files = sorted(os.listdir(raw_dir))

    for filename in files:
        if not filename.lower().endswith(".txt"):
            continue

        path = os.path.join(raw_dir, filename)

        # 1) Leemos HTML bruto
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            raw_text = f.read()

        # 2) Leemos metadatos si existen
        meta = {}
        meta_file = path.replace(".txt", ".meta.json")
        title = ""
        description = ""
        h1 = ""
        original_url = ""
        if os.path.exists(meta_file):
            with open(meta_file, "r", encoding="utf-8") as mf:
                meta = json.load(mf)
                title       = meta.get("title", "")
                description = meta.get("description", "")
                h1          = meta.get("h1", "")
                original_url= meta.get("url", "")  # si lo guardas en meta

        # Si no hay URL en metadatos, inferir desde filename (fallback)
        # (mejor si crawler guarda original URL en el .meta.json)
        if not original_url:
            original_url = filename  # o dejar vacío si no hay

        # Normalizar URL para usar como clave de enlace
        normalized_doc_url = normalize_url(original_url)

        # 3) Construimos texto visible del HTML para indexar
        visible_text = extract_visible_text(raw_text)

        # 4) Construimos texto completo a indexar
        #    concatenando titulo, h1, descripción y cuerpo
        full_text_to_index = f"{title} {h1} {description} {visible_text}"

        # 5) Normalizar y tokenizar texto completo
        normalized = normalize_text(full_text_to_index)
        tokens = tokenize_text(normalized)
        filtered = remove_stopwords(tokens)

        if not filtered:
            # documento sin tokens útiles → saltar
            continue

        # 6) Asignar doc_id
        doc_id = N + 1

        # 7) Insertar documento en tabla docs con URL
        doc_title = title if title else os.path.basename(path)
        con.execute(
            "INSERT INTO docs(doc_id, url, title, path, length) VALUES(?,?,?,?,?)",
            (doc_id, normalized_doc_url, doc_title, path, len(filtered))
        )

        # 8) Guardar enlaces en tabla links
        #    extraer enlaces desde HTML bruto
        links = extract_links(raw_text, normalized_doc_url)
        for link in links:
            # Normalizar cada enlace
            normalized_link = normalize_url(link)

            # Consultar si existe target en docs (podría indexarse ya o después)
            row = con.execute(
                "SELECT doc_id FROM docs WHERE url=?",
                (normalized_link,)
            ).fetchone()

            if row:
                to_doc_id = row[0]
                con.execute(
                    "INSERT INTO links(from_doc_id, to_doc_id) VALUES(?,?)",
                    (doc_id, to_doc_id)
                )

        # 9) Construir postings y df
        tf: Dict[str,int] = {}
        for t in filtered:
            tf[t] = tf.get(t, 0) + 1

        for term, freq in tf.items():
            con.execute(
                "INSERT OR REPLACE INTO postings(term, doc_id, tf) VALUES(?,?,?)",
                (term, doc_id, freq)
            )
            df_counts[term] = df_counts.get(term, 0) + 1

        # 10) Actualizar contadores globales
        N += 1
        total_len += len(filtered)

    # --- fuera del bucle: actualizar df y meta ---
    for term, df in df_counts.items():
        con.execute(
            "INSERT OR REPLACE INTO df(term, doc_freq) VALUES(?,?)",
            (term, df)
        )

    # calcular avgdl
    avgdl = (total_len / N) if N > 0 else 0.0
    con.execute("INSERT OR REPLACE INTO meta(key, value) VALUES(?,?)", ("N", N))
    con.execute("INSERT OR REPLACE INTO meta(key, value) VALUES(?,?)", ("avgdl", avgdl))

    con.commit()
    con.close()

    return {"indexed_docs": N, "avgdl": avgdl}