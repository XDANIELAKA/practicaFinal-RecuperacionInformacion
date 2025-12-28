from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

# Importamos tu función real de crawling
from app.core.crawler import simple_crawl

# Importamos la función que nos da la ruta global de raw
from app.core.paths import data_raw_dir
router = APIRouter()

class CrawlRequest(BaseModel):
    seed_urls: List[str]
    max_pages: Optional[int] = 50
    max_depth: Optional[int] = 1

@router.post("/crawl")
def crawl_endpoint(req: CrawlRequest):
    """
    Ejemplo de body:
    {
        "seed_urls": ["https://es.wikipedia.org/wiki/Inteligencia_artificial"],
        "max_pages": 50,
        "max_depth": 1
    }
    """
    # Obtenemos la ruta global donde guardaremos los archivos
    raw_dir = data_raw_dir()

    # Llamamos a la función de crawling real pasando la carpeta de destino
    saved_files = simple_crawl(
        seed_urls=req.seed_urls,
        raw_dir=raw_dir,
        max_pages=req.max_pages,
        max_depth=req.max_depth
    )

    # Construimos y devolvemos un JSON fácil de interpretar
    return {
        "total_crawled": len(saved_files),
        "files": saved_files
    }