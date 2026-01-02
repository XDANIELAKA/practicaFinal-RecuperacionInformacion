from fastapi import APIRouter
from pydantic import BaseModel

from app.core.textproc import normalize_text, tokenize_text, remove_stopwords
from app.index.bm25 import bm25_score
from app.index.storage import get_connection

router = APIRouter()

class SearchRequest(BaseModel):
    query: str
    topk: int = 10     # número de documentos a considerar del ranking BM25
    page: int = 1      # página actual para paginación
    page_size: int = 5 # tamaño de página para paginación

def extract_snippets_bm25(text: str, query_terms: list, window: int = 15, max_snip: int = 3) -> str:
    """
    Extrae hasta max_snip snippets del texto, priorizando zonas con mayor densidad de query_terms.
    Luego resalta los términos de consulta con <b>…</b>.
    """
    words = text.split()
    positions = []

    # encontrar todas las posiciones donde aparezcan términos de consulta
    for i, w in enumerate(words):
        if w in query_terms:
            positions.append(i)

    # si no hay ocurrencias de términos
    if not positions:
        snippet = " ".join(words[:window * 2]) if len(words) > 0 else ""
        return "..." + snippet + "..."

    # agrupar posiciones cercanas
    segments = []
    current_seg = [positions[0]]

    for pos in positions[1:]:
        if pos - current_seg[-1] <= window:
            current_seg.append(pos)
        else:
            segments.append(current_seg)
            current_seg = [pos]
    segments.append(current_seg)

    # ordenar segmentos por número de términos
    segments.sort(key=lambda seg: len(seg), reverse=True)

    snippets = []
    for seg in segments[:max_snip]:
        idx_center = seg[len(seg) // 2]
        start = max(0, idx_center - window)
        end = min(len(words), idx_center + window)
        frag = words[start:end]

        # resaltar términos de consulta
        for j, wrd in enumerate(frag):
            if wrd in query_terms:
                frag[j] = f"<b>{wrd}</b>"

        snippet_text = " ".join(frag)
        snippets.append("…" + snippet_text + "…")

    return " ".join(snippets)

@router.post("/search")
def search_endpoint(req: SearchRequest):
    # normalizar y tokenizar la consulta
    text = normalize_text(req.query)
    tokens = tokenize_text(text)
    filtered_query_terms = remove_stopwords(tokens)

    # ranking BM25 con topk
    all_ranked = bm25_score(filtered_query_terms, topk=req.topk)

    # paginación sobre los topk
    start = (req.page - 1) * req.page_size
    end = req.page * req.page_size
    paged_ranked = all_ranked[start:end]

    results = []
    con = get_connection()

    # Calcular el valor máximo de PageRank una sola vez (para normalizar)
    max_pr_row = con.execute("SELECT MAX(rank) FROM pagerank").fetchone()
    max_pr = max_pr_row[0] if max_pr_row and max_pr_row[0] not in (None, 0) else 1.0

    # recorrer los documentos paginados
    for doc_id, score_bm25 in paged_ranked:

        # obtener título y path del documento
        row = con.execute(
            "SELECT title, path FROM docs WHERE doc_id=?", (doc_id,)
        ).fetchone()
        title = row[0] if row else ""
        path = row[1] if row else ""

        # leer el texto completo del documento para snippet
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                raw_text = f.read()
        except Exception:
            raw_text = ""

        # normalizar texto completo para buscar snippet
        normalized_doc_text = normalize_text(raw_text)

        # extraer snippet alrededor de los términos de consulta
        snippet = extract_snippets_bm25(normalized_doc_text, filtered_query_terms)

        # obtener PageRank si existe
        pr_row = con.execute(
            "SELECT rank FROM pagerank WHERE doc_id=?", (doc_id,)
        ).fetchone()

        # PageRank real sin normalizar
        raw_pr = pr_row[0] if pr_row else 0.0

        # Normalizar PageRank (0..1)
        pagerank_norm = raw_pr / max_pr

        # combinación lineal (ajusta alpha según necesidad)
        alpha = 0.7
        final_score = alpha * score_bm25 + (1 - alpha) * pagerank_norm

        # añadir resultado a la lista con todos los campos
        results.append({
            "doc_id": doc_id,
            "title": title,
            "score_bm25": score_bm25,
            "pagerank_raw": raw_pr,
            "pagerank_norm": pagerank_norm,
            "score": final_score,
            "path": path,
            "snippet": snippet
        })

    # opcional: ordenar por score (descendente)
    results.sort(key=lambda r: r["score"], reverse=True)

    con.close()

    return {
        "query_terms": filtered_query_terms,
        "page": req.page,
        "page_size": req.page_size,
        "total_results": len(all_ranked),
        "results": results
    }