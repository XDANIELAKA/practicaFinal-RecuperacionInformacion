import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os

# Directorio donde guardaremos txt
RAW_DIR = os.path.join(os.getcwd(), "data", "raw")
os.makedirs(RAW_DIR, exist_ok=True)

def is_valid_url(url):
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https")
    except:
        return False

def extract_text(html):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n", strip=True)
    return text

def get_links(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    result = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        full = urljoin(base_url, href)
        if is_valid_url(full):
            result.append(full)
    return result

def save_text_file(text, index):
    fname = f"{index:06d}.txt"
    path = os.path.join(RAW_DIR, fname)
    with open(path, "w", encoding="utf-8", errors="ignore") as f:
        f.write(text)
    return path

def simple_crawl(seed_urls, max_pages=100, max_depth=1):
    visited = set()
    to_crawl = [(u, 0) for u in seed_urls]
    results = []
    index = 1

    while to_crawl and index <= max_pages:
        url, depth = to_crawl.pop(0)

        if url in visited or depth > max_depth:
            continue

        try:
            headers = {
            "User-Agent": "PracticaRI-CrawlerBot/1.0 (+https://github.com/XDANIELAKA)"
            }
            res = requests.get(url, headers=headers, timeout=10)
            html = res.text
        except Exception as e:
            results.append({"url": url, "status": "error", "error": str(e)})
            visited.add(url)
            continue

        visited.add(url)

        text = extract_text(html)
        saved_path = save_text_file(text, index)
        results.append({"url": url, "saved": saved_path})

        index += 1

        if depth < max_depth:
            new_links = get_links(html, url)
            for link in new_links:
                if link not in visited:
                    to_crawl.append((link, depth + 1))

    return results