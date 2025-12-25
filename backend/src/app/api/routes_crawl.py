from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from app.core.crawler import simple_crawl

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
    results = simple_crawl(
        seed_urls=req.seed_urls,
        max_pages=req.max_pages,
        max_depth=req.max_depth
    )
    return {"total_crawled": len(results), "results": results}