import os
from fastapi import APIRouter
from fastapi import HTTPException
from pydantic import BaseModel

from app.index.indexer import index_documents
from app.core.paths import get_project_root

# Importar PageRank para ejecutarlo después de indexar
from app.index.pagerank import run_pagerank

router = APIRouter()

class IndexRequest(BaseModel):
    raw_dir: str

@router.post("/index")
def index_endpoint(req: IndexRequest):
    """
    Ejemplo de body:
    {
      "raw_dir": "data/raw"
    }

    Esta función:
    - Combina la ruta relativa con la raíz real del proyecto,
      independientemente de dónde se arranque el servidor.
    - Llama al indexador
    - Ejecuta PageRank después de indexar
    """

    project_root = get_project_root()

    # Convertir raw_dir relativo en absoluto
    abs_raw_dir = os.path.join(project_root, req.raw_dir)

    # Verificar que existe la carpeta raw
    if not os.path.isdir(abs_raw_dir):
        raise HTTPException(status_code=400, detail=f"Directorio raw no existe: {abs_raw_dir}")

    # Llamada al indexador con la ruta absoluta
    stats = index_documents(abs_raw_dir)

    # Ejecutar PageRank tras indexar
    try:
        run_pagerank(verbose=True)  # verbose=True para que imprima logs en consola
    except Exception as e:
        # No bloqueamos la respuesta si PageRank falla,
        # pero mostramos el error en consola
        print("Error al calcular PageRank tras indexar:", e)

    return {
        "indexed": stats,
        "pagerank": "calculado"
    }