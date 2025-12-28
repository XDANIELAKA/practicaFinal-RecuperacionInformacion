import os
from fastapi import APIRouter
from pydantic import BaseModel

from app.index.indexer import index_documents
from app.core.paths import get_project_root

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
    """
    project_root = get_project_root()

    # Convertir raw_dir relativo en absoluto
    abs_raw_dir = os.path.join(project_root, req.raw_dir)

    # Llamada al indexador con la ruta absoluta
    stats = index_documents(abs_raw_dir)

    return stats