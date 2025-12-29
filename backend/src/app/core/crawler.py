import os
import requests
from bs4 import BeautifulSoup
from typing import List

def crawl_page(url: str) -> str:
    """
    Hace una petición HTTP a la URL dada, devuelve el texto
    extraído (limpio) del HTML o vacío en caso de error.
    """
    try:
        headers = {
            "User-Agent": "PracticaRI-CrawlerBot/1.0 (+https://github.com/XDANIELAKA)"
        }
        res = requests.get(url, headers=headers, timeout=5)
        res.raise_for_status()
        return res.text  # guardamos HTML completo
        
    except Exception as e:
        print(f"Crawl error en {url}:", e)
        return ""
    
def extract_metadata(html: str) -> dict:
    """
    Extrae título, h1 y meta-description de un HTML.
    """
    soup = BeautifulSoup(html, "html.parser")

    # --- Título ---
    title = soup.title.string.strip() if soup.title and soup.title.string else ""

    # --- H1 ---
    h1_tag = soup.find("h1")
    h1_text = h1_tag.get_text(strip=True) if h1_tag else ""

    # --- Meta Description (múltiples variantes) ---
    meta_desc = ""

    # 1) meta name="description"
    desc_tag = soup.find("meta", {"name": "description"})
    if desc_tag and desc_tag.get("content"):
        meta_desc = desc_tag["content"].strip()

    # 2) Open Graph description
    if not meta_desc:
        og_tag = soup.find("meta", {"property": "og:description"})
        if og_tag and og_tag.get("content"):
            meta_desc = og_tag["content"].strip()

    # 3) Twitter description
    if not meta_desc:
        twitter_tag = soup.find("meta", {"name": "twitter:description"})
        if twitter_tag and twitter_tag.get("content"):
            meta_desc = twitter_tag["content"].strip()

    # 4) Fallback: primeros párrafos visibles
    if not meta_desc:
        p_tag = soup.find("p")
        if p_tag:
            # tomamos solo los primeros 150–200 caracteres
            text = p_tag.get_text(strip=True)
            meta_desc = text[:200] + ("…" if len(text) > 200 else "")

    return {
        "title": title,
        "h1": h1_text,
        "description": meta_desc
    }

def save_document(n: int, text: str, raw_dir: str) -> str:
    """
    Guarda el texto en un fichero con nombre con ceros a la izquierda
    en la carpeta raw_dir del proyecto.
    Retorna la ruta absoluta al archivo creado.
    """
    filename = f"{n:06d}.txt"
    save_path = os.path.join(raw_dir, filename)

    try:
        with open(save_path, "w", encoding="utf-8", errors="ignore") as f:
            f.write(text)
    except Exception as e:
        print("Error al guardar documento:", e)

    return save_path

def simple_crawl(
    seed_urls: List[str],
    raw_dir: str,
    max_pages: int = 100,
    max_depth: int = 1
) -> List[str]:
    """
    Crawlea las URLs dadas con una cola básica (BFS),
    guarda cada documento en raw_dir y devuelve la lista
    de rutas de los archivos guardados.
    """
    visited = set()
    queue = [(url, 0) for url in seed_urls]
    count = 0
    saved_files = []

    while queue and count < max_pages:
        url, depth = queue.pop(0)

        if url in visited or depth > max_depth:
            continue

        visited.add(url)

        print(f"Crawling ({count+1}/{max_pages}): {url}")

        html_text = crawl_page(url)

        if html_text:
            # Extraemos metadatos del HTML
            metadata = extract_metadata(html_text)

            # Nombre base del documento (000001, 000002, etc.)
            filename = f"{count + 1:06d}"

            # Guardar metadatos en JSON
            meta_path = os.path.join(raw_dir, f"{filename}.meta.json")
            with open(meta_path, "w", encoding="utf-8") as mf:
                import json
                json.dump(metadata, mf, ensure_ascii=False, indent=2)

            # Guardar el HTML completo
            path = save_document(count + 1, html_text, raw_dir)
            saved_files.append(path)

            count += 1
            print(f"[CRAWL] Terminó: {url}")

        # Aquí podrías extraer enlaces y añadirlos a la cola
        # en función de max_depth, etc.

    return saved_files