import math
from typing import List, Dict, Tuple
from .storage import get_connection

def bm25_score(query_terms: List[str], k1=1.5, b=0.75, topk=10) -> List[Tuple[int,float]]:
    con = get_connection()
    cur = con.cursor()

    # leer variables globales
    row = cur.execute("SELECT value FROM meta WHERE key='N'").fetchone()
    N = row[0] if row else 0
    row = cur.execute("SELECT value FROM meta WHERE key='avgdl'").fetchone()
    avgdl = row[0] if row else 1

    qtf: Dict[str,int] = {}
    for t in query_terms:
        qtf[t] = qtf.get(t, 0) + 1

    scores: Dict[int,float] = {}

    for term in qtf.keys():
        row = cur.execute("SELECT doc_freq FROM df WHERE term=?", (term,)).fetchone()
        if not row:
            continue
        df = float(row[0])
        idf = math.log(1 + (N - df + 0.5)/(df + 0.5))

        for doc_id, tf in cur.execute("SELECT doc_id, tf FROM postings WHERE term=?", (term,)):
            row = cur.execute("SELECT length FROM docs WHERE doc_id=?", (doc_id,)).fetchone()
            dl = row[0] if row else 0.0

            denom = tf + k1 * (1 - b + b * (dl / avgdl))
            score = idf * ((tf * (k1 + 1)) / denom if denom > 0 else 0)
            scores[doc_id] = scores.get(doc_id, 0.0) + score

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:topk]
    con.close()
    return ranked