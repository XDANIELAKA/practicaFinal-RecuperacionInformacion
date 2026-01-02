import os
import time
import requests
import json
import urllib.robotparser
from urllib.parse import urlparse, urljoin, urlunparse, parse_qsl, urlencode
from bs4 import BeautifulSoup
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import deque
import threading


MAX_HTML_SIZE = 5 * 1024 * 1024  # 5 MB
BUCKET_SIZE = 1000
MAX_TOTAL_BYTES = 10 * 1024 * 1024 * 1024  # 10 GB
robots_cache = {}
MAX_WORKERS = 5
visited_lock = threading.Lock()
quota_lock = threading.Lock()


def normalize_url(url: str) -> str:
    """
    Normaliza una URL para evitar duplicados semánticos.
    - Convierte esquema y host a minúsculas
    - Elimina 'www.'
    - Elimina fragmentos (#)
    - Ordena parámetros query
    - Elimina barra final innecesaria
    """
    try:
        parsed = urlparse(url)

        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()

        # Eliminar www. solo si está al inicio
        if netloc.startswith("www."):
            netloc = netloc[4:]

        # Normalizar path
        path = parsed.path or "/"
        path = path.rstrip("/")
        if not path:
            path = "/"

        # Ordenar parámetros query
        query_params = parse_qsl(parsed.query, keep_blank_values=True)
        query_params.sort()
        query = urlencode(query_params)

        normalized = urlunparse((
            scheme,
            netloc,
            path,
            "",      # params (obsoletos)
            query,
            ""       # fragment eliminado
        ))

        return normalized

    except Exception:
        # En caso de URL malformada, devolver la original
        return url
    
def get_bucket_dir(doc_id: int, base_dir: str) -> str:
    """
    Devuelve el directorio correspondiente al rango de IDs del documento.
    Ejemplo: 1234 -> base_dir/001000-001999
    """
    start = (doc_id // BUCKET_SIZE) * BUCKET_SIZE
    end = start + BUCKET_SIZE - 1
    bucket_name = f"{start:06d}-{end:06d}"
    return os.path.join(base_dir, bucket_name)

def crawl_page(
    url: str,
    user_agent: str = "PracticaRI-CrawlerBot/1.0 (+https://github.com/XDANIELAKA)"
) -> str:
    """
    Hace una petición HTTP a la URL dada y devuelve
    el HTML completo de la página si está permitido
    por robots.txt o vacío en caso de error.
    """
    try:
        # --- Preparar el parser de robots.txt para ese dominio ---
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"

        if domain not in robots_cache:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(f"{domain}/robots.txt")
            rp.read()
            robots_cache[domain] = rp
        else:
            rp = robots_cache[domain]

        # --- Comprobar si la URL está permitida por robots.txt ---
        if not rp.can_fetch(user_agent, url):
            print(f"[robots.txt] Acceso denegado para {url}")
            return ""

        # --- Respetar posible crawl-delay ---
        delay = rp.crawl_delay(user_agent)
        if delay:
            print(f"[robots.txt] Crawl-delay de {delay} s para {domain}")
            time.sleep(delay)

        # --- Realizar la petición HTTP ---
        headers = {"User-Agent": user_agent}
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()

        # --- Devolver el HTML completo ---
        return res.text

    except Exception as e:
        print(f"Crawl error en {url}:", e)
        return ""

def extract_metadata(html: str) -> dict:
    """
    Extrae título, h1 y descripción de un HTML dado.
    Esta versión es más robusta y maneja casos como páginas de tags o autores.
    """
    soup = BeautifulSoup(html, "html.parser")

    # --- Título ---
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    # --- H1 ---
    h1 = ""
    first_h1 = soup.find("h1")
    if first_h1:
        # A veces el h1 incluye espacios extra, newlines, etc.
        h1 = first_h1.get_text(" ", strip=True)

    # --- Meta description ---
    description = ""

    # Probar meta description estándar
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag and meta_tag.get("content"):
        description = meta_tag.get("content").strip()

    # Probar OpenGraph si no hay
    if not description:
        og_desc = soup.find("meta", attrs={"property": "og:description"})
        if og_desc and og_desc.get("content"):
            description = og_desc.get("content").strip()

    # Probar Twitter description si aún no hay
    if not description:
        twitter_desc = soup.find("meta", attrs={"name": "twitter:description"})
        if twitter_desc and twitter_desc.get("content"):
            description = twitter_desc.get("content").strip()

    # Fallback: si no hay ninguna meta, tomar los primeros 2 párrafos
    if not description:
        p_tags = soup.find_all("p")
        if p_tags:
            # concatenar 2 párrafos para una descripción que no sea solo texto plano
            text_parts = [p.get_text(" ", strip=True) for p in p_tags[:2]]
            description = " ".join(text_parts)

    # Fallback final: usar h1 como título si no existe <title>
    if not title and h1:
        title = h1

    # Fallback final de descripción
    if not description and title:
        description = f"Contenido sobre {title}"

    return {
        "title": title,
        "h1": h1,
        "description": description
    }

def save_document(n: int, text: str, raw_dir: str) -> str:
    """
    Guarda el texto en un fichero con nombre con ceros a la izquierda
    en la carpeta raw_dir del proyecto.
    Retorna la ruta absoluta al archivo creado.
    """
    # Asegurar que el directorio existe
    bucket_dir = get_bucket_dir(n, raw_dir)
    os.makedirs(bucket_dir, exist_ok=True)

    filename = f"{n:06d}.txt"
    save_path = os.path.join(bucket_dir, filename)

    try:
        with open(save_path, "w", encoding="utf-8", errors="ignore") as f:
            f.write(text)
    except Exception as e:
        print("Error al guardar documento:", e)

    return save_path

def extract_links(html: str, base_url: str) -> List[str]:
    """
    Extrae todas las URLs de <a href> y las normaliza
    """
    links = []
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()

        # Normaliza URLs relativas
        url = urljoin(base_url, href)
        normalized = normalize_url(url)
        links.append(normalized)


    return links

def simple_crawl(
    seed_urls: List[str],
    raw_dir: str,
    max_pages: int = 100,
    max_depth: int = 1
) -> List[str]:
    """
    Crawlea las URLs dadas con una cola recursiva (BFS),
    siguiendo enlaces internos dentro de cada dominio,
    respeta robots.txt, guarda cada documento y sus metadatos,
    y devuelve la lista de rutas de los archivos guardados.
    """

    # --- 1) Calcular numeración continua según los .txt existentes ---
    existing_txts = []
    for root, _, files in os.walk(raw_dir):
        for f in files:
            if f.lower().endswith(".txt") and f.split(".")[0].isdigit():
                existing_txts.append(f)

    if existing_txts:
        nums = sorted(
            int(f.split(".")[0])
            for f in existing_txts
            if f.split(".")[0].isdigit()
        )
        start_index = nums[-1]
    else:
        start_index = 0

    # --- Comprobar tamaño total actual en bytes ---
    current_total_bytes = 0
    for root, _, files in os.walk(raw_dir):
        for f in files:
            file_path = os.path.join(root, f)
            try:
                current_total_bytes += os.path.getsize(file_path)
            except OSError:
                pass

    # --- 2) BFS con concurrencia, profundidad y robots.txt ---
    visited = set()
    queue = deque((normalize_url(url), 0) for url in seed_urls)
    saved_files: List[str] = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {}

        while queue and len(saved_files) < max_pages:

            # --- Enviar nuevas tareas al executor ---
            while queue and len(futures) < MAX_WORKERS and len(saved_files) + len(futures) < max_pages:
                url, depth = queue.popleft()

                with visited_lock:
                    if url in visited:
                        continue
                    visited.add(url)

                # Encolamos tarea sin imprimir todavía
                future = executor.submit(crawl_page, url)
                futures[future] = (url, depth)

            # --- Procesar tareas completadas ---
            for future in as_completed(list(futures)):
                url, depth = futures.pop(future)

                try:
                    html_text = future.result()
                except Exception as e:
                    print(f"[ERROR] Descargando {url}: {e}")
                    continue

                # Si no hay HTML o está vacío → ignorar
                if not html_text:
                    continue

                # Si HTML demasiado grande → ignorar
                if len(html_text) > MAX_HTML_SIZE:
                    print(f"[SKIP] HTML demasiado grande: {url}")
                    continue

                # Tamaño en bytes del documento
                doc_bytes = len(html_text.encode("utf-8"))

                with quota_lock:
                    if current_total_bytes + doc_bytes > MAX_TOTAL_BYTES:
                        print("[STOP] Cuota máxima de 10GB alcanzada")
                        return saved_files

                # --- Guardar documento y metadatos ---
                new_idx = start_index + len(saved_files) + 1

                # Guardar metadatos
                metadata = extract_metadata(html_text)
                metadata["url"] = normalize_url(url)
                bucket_dir = get_bucket_dir(new_idx, raw_dir)
                os.makedirs(bucket_dir, exist_ok=True)

                meta_path = os.path.join(bucket_dir, f"{new_idx:06d}.meta.json")
                with open(meta_path, "w", encoding="utf-8") as mf:
                    json.dump(metadata, mf, ensure_ascii=False, indent=2)

                # Guardar HTML
                html_path = os.path.join(bucket_dir, f"{new_idx:06d}.txt")
                with open(html_path, "w", encoding="utf-8", errors="ignore") as f:
                    f.write(html_text)

                saved_files.append(html_path)

                with quota_lock:
                    current_total_bytes += doc_bytes

                # Nuevo print con número real de guardado
                doc_number = len(saved_files)
                print(f"[CRAWL] Guardado ({doc_number}/{max_pages}): {url}")

                # --- Extraer enlaces y encolar si hay profundidad ---
                if depth < max_depth:
                    links = extract_links(html_text, url)
                    parsed = urlparse(url)
                    base_domain = f"{parsed.scheme}://{parsed.netloc}"

                    for link in links:
                        normalized_link = normalize_url(link)
                        if normalized_link.startswith(base_domain):
                            with visited_lock:
                                if normalized_link not in visited:
                                    queue.append((normalized_link, depth + 1))

            # Fin del for as_completed

        # Fin del while queue


    return saved_files