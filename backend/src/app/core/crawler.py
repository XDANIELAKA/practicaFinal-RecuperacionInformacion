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
        soup = BeautifulSoup(res.text, "html.parser")
        # Extraemos texto visible, puedes mejorar este limpiado:
        texts = soup.get_text(separator="\n", strip=True)
        return texts
    except Exception as e:
        print(f"Crawl error en {url}:", e)
        return ""

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

        text = crawl_page(url)

        print(f"[CRAWL] Terminó: {url}")

        if not text:
            continue

        # Guardamos el documento en raw_dir
        path = save_document(count + 1, text, raw_dir)
        saved_files.append(path)
        count += 1

        # Aquí podrías extraer enlaces y añadirlos a la cola
        # en función de max_depth, etc.

    return saved_files