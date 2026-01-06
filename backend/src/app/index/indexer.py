from typing import Dict, List
from bs4 import BeautifulSoup
import os
import json
import re
from urllib.parse import urljoin

from app.core.textproc import normalize_text, tokenize_text, remove_stopwords
from app.core.crawler import extract_links, normalize_url
from .storage import get_connection


def extract_visible_text(html: str) -> str:
    """
    Extrae el texto más relevante de HTML genérico.
    - Elimina scripts, estilos y bloques no útiles.
    - Prioriza varios selectores comunes.
    - Filtra duplicados y ruido.
    """

    soup = BeautifulSoup(html, "html.parser")

    # --- Eliminar etiquetas que no aportan texto semántico ---
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside", "form"]):
        tag.decompose()

    seen = set()
    text_blocks = []

    # --- Posibles etiquetas de contenido útiles ---
    selectors = ["p", "div", "article", "main", "section", "h1", "h2", "h3", "h4", "li", "dd", "dt"]
    for sel in selectors:
        for element in soup.find_all(sel):
            block_text = element.get_text(" ", strip=True)
            block_text = re.sub(r"\s+", " ", block_text)

            if not block_text:
                continue

            # Evitar duplicaciones exactas
            if block_text in seen:
                continue

            seen.add(block_text)
            text_blocks.append(block_text)

    # --- Fallback: si está vacío, tomar todo el texto visible ---
    if not text_blocks:
        fallback_text = soup.get_text(" ", strip=True)
        fallback_text = re.sub(r"\s+", " ", fallback_text)
        if fallback_text:
            text_blocks.append(fallback_text)

    return " ".join(text_blocks).strip()

def extract_visible_text_wikipedia(html: str) -> str:
    """
    Extrae texto principal de una página de Wikipedia.
    - Se centra en <div id='mw-content-text'>, que contiene el artículo.
    - Elimina ruido común (tablas, referencias, navegación, etc.).
    - Extrae párrafos, listas, encabezados y definiciones relevantes.
    """

    soup = BeautifulSoup(html, "html.parser")

    # --- Contenedor principal de contenido en Wikipedia ---
    main_content = soup.find("div", id="mw-content-text")
    if not main_content:
        # Fallback si no existiera (página atípica)
        return ""

    # Eliminar ruido común de Wikipedia
    for tag in main_content(["script", "style", "noscript", "table", "sup", "aside", "figure", "nav"]):
        tag.decompose()

    # Eliminar bloques con clases no relevantes
    NON_CONTENT_CLASSES = [
        "mw-editsection", "reference", "reflist",
        "toc", "navbox", "infobox", "metadata"
    ]
    for cls in NON_CONTENT_CLASSES:
        for el in main_content.find_all(class_=cls):
            el.decompose()

    text_parts = []
    seen = set()
    MAX_BLOCKS = 400  # Límite para no sacar articulos demasiado largos

    # --- Extraer encabezados de sección para contexto semántico ---
    for el in main_content.find_all(["h2", "h3"]):
        if len(text_parts) >= MAX_BLOCKS:
            break

        txt = el.get_text(" ", strip=True)
        txt = re.sub(r"\s+", " ", txt)

        if not txt or len(txt.split()) < 2 or len(txt.split()) > 15:
            continue

        if txt not in seen:
            seen.add(txt)
            text_parts.append(txt)

    # --- Extraer texto útil de párrafos y listas ---
    for el in main_content.find_all(["p", "li", "dd", "dt"]):
        if len(text_parts) >= MAX_BLOCKS:
            break

        txt = el.get_text(" ", strip=True)
        txt = re.sub(r"\s+", " ", txt)

        if not txt or len(txt.split()) < 3:
            continue

        if txt not in seen:
            seen.add(txt)
            text_parts.append(txt)

    # --- Devolver la concatenación de partes relevantes ---
    return " ".join(text_parts).strip()

def index_documents(raw_dir: str):
    """
    Indexa todos los .txt en raw_dir.
    Guarda en tables: docs, postings, df, links y meta.
    """

    con = get_connection()
    cursor = con.cursor()

    # --- borrar índice viejo (solo datos), pero no estructura de tablas ---
    cursor.executescript("""
        DELETE FROM docs;
        DELETE FROM postings;
        DELETE FROM df;
        DELETE FROM links;
        DELETE FROM meta;
    """)
    con.commit()

    # Contadores globales
    N = 0
    total_len = 0

    # df_counts: cuenta en cuántos documentos aparece cada término
    df_counts: Dict[str, int] = {}

    # Mapas de armonización URL ↔ doc_id
    url_to_docid: Dict[str, int] = {}
    docid_to_url: Dict[int, str] = {}

    # --- Recorrer todos los .txt en raw_dir y sus subdirectorios ---
    print(">>> Recorriendo raw_dir recursivamente:", raw_dir)

    txt_files = []
    for root, _, files in os.walk(raw_dir):
        for f in files:
            if f.lower().endswith(".txt"):
                txt_files.append(os.path.join(root, f))

    txt_files = sorted(txt_files)
    print(">>> Archivos .txt encontrados:", txt_files)

    # Guardamos HTML crudo para extraer luego enlaces
    raw_html_store: Dict[int, str] = {}

    # --- Primera pasada: indexar docs y postings ---
    for path in txt_files:

        # Nombre simple para depuración
        filename = os.path.basename(path)

        # Evita indexar archivos vacíos
        try:
            if os.path.getsize(path) == 0:
                print(f"[index_documents] Archivo vacío, omitiendo: {filename}")
                continue
        except Exception as e:
            print(f"[index_documents] No se pudo verificar tamaño de {filename}: {e}")
            continue

        # --- Leer HTML bruto ---
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                raw_text = f.read()
        except Exception as e:
            print(f"[index_documents] Error leyendo {filename}: {e}")
            continue

        print(f">>> Encontrado TXT: {path}")

        # --- Leer metadatos si existen ---
        meta = {}
        meta_file = path.replace(".txt", ".meta.json")
        if os.path.exists(meta_file):
            try:
                with open(meta_file, "r", encoding="utf-8") as mf:
                    meta = json.load(mf)
            except json.JSONDecodeError:
                meta = {}
            except Exception as e:
                print(f"[index_documents] JSON inválido en {meta_file}: {e}")

        original_url = meta.get("url", "").strip()
        if not original_url:
            # Si no existe en meta, usamos filename (fallback no ideal)
            original_url = filename

        normalized_doc_url = normalize_url(original_url)

        # --- Extraer texto visible ---
        if "wikipedia.org" in normalized_doc_url:
            visible_text = extract_visible_text_wikipedia(raw_text)
        else:
            visible_text = extract_visible_text(raw_text)

        # --- DEBUG: información de texto visible ---
        print(f"\n[DEBUG] Doc URL: {normalized_doc_url}")
        print(f"[DEBUG] Visible text preview (200 chars): {visible_text[:200]}...")
        print(f"[DEBUG] Visible text word count: {len(visible_text.split())}")

        # --- Construir y normalizar texto completo para indexar ---
        title = meta.get("title", "")
        h1 = meta.get("h1", "")
        description = meta.get("description", "")
        full_text_to_index = f"{title} {h1} {description} {visible_text}"

        normalized = normalize_text(full_text_to_index)
        tokens = tokenize_text(normalized)

        # --- DEBUG: tokens antes y después de filtrar ---
        print(f"[DEBUG] Normalized tokens (first 20): {tokens[:20]}")
        filtered = remove_stopwords(tokens)
        print(f"[DEBUG] Filtered tokens count: {len(filtered)}")
        print(f"[DEBUG] Filtered tokens (first 20): {filtered[:20]}\n")

        if not filtered:
            print(f"[index_documents] Sin tokens útiles en: {filename}")
            continue

        # --- Asignar doc_id ---
        doc_id = N + 1
        url_to_docid[normalized_doc_url] = doc_id
        docid_to_url[doc_id] = normalized_doc_url
        raw_html_store[doc_id] = raw_text

        # --- Guardar en docs ---
        doc_title = title if title else filename
        cursor.execute(
            "INSERT INTO docs(doc_id, url, title, path, length) VALUES (?, ?, ?, ?, ?)",
            (doc_id, normalized_doc_url, doc_title, path, len(filtered))
        )
        print(f">>> Indexando doc_id={doc_id} ({filename})")

        # --- Guardar postings y contar DF ---
        tf: Dict[str, int] = {}
        for term in filtered:
            tf[term] = tf.get(term, 0) + 1

        for term, freq in tf.items():
            cursor.execute(
                "INSERT INTO postings(term, doc_id, tf) VALUES (?, ?, ?)",
                (term, doc_id, freq)
            )
            df_counts[term] = df_counts.get(term, 0) + 1

        N += 1
        total_len += len(filtered)

    # ----------------------------------------------------------------
    # Segunda pasada: extraer enlaces y guardarlos en links
    # ----------------------------------------------------------------

    for doc_id, raw_html in raw_html_store.items():
        base_url = docid_to_url[doc_id]
        for href in extract_links(raw_html, base_url):
            try:
                normalized_link = normalize_url(urljoin(base_url, href))
            except Exception:
                continue

            if normalized_link in url_to_docid:
                to_doc_id = url_to_docid[normalized_link]
                cursor.execute(
                    "INSERT INTO links(from_doc_id, to_doc_id) VALUES (?, ?)",
                    (doc_id, to_doc_id)
                )

    # ----------------------------------------------------------------
    # Finalmente: insertar DF y estadísticas meta (N y avgdl)
    # ----------------------------------------------------------------

    for term, df_val in df_counts.items():
        cursor.execute(
            "INSERT OR REPLACE INTO df(term, doc_freq) VALUES (?, ?)",
            (term, df_val)
        )

    avgdl = (total_len / N) if N > 0 else 0.0
    cursor.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
        ("N", N)
    )
    cursor.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
        ("avgdl", avgdl)
    )

    # --- Commit final y consolidar WAL ---
    con.commit()
    con.execute("PRAGMA wal_checkpoint(FULL);")
    con.close()

    return {"indexed_docs": N, "avgdl": avgdl}