import os

def get_project_root() -> str:
    """
    Devuelve la ruta absoluta a la raíz del proyecto:
    .../martinez_infantes_daniel_pFinal
    """
    # THIS_FILE: .../backend/src/app/core/paths.py
    THIS_FILE = os.path.abspath(__file__)

    # 1) Subimos desde 'app/core' → backend/src
    base_src = os.path.dirname(os.path.dirname(os.path.dirname(THIS_FILE)))

    # 2) Subimos desde 'backend/src' → backend
    backend_dir = os.path.dirname(base_src)

    # 3) Subimos desde 'backend' → raíz del proyecto
    project_root = os.path.dirname(backend_dir)

    return project_root

def data_raw_dir() -> str:
    """
    Devuelve la ruta absoluta de `data/raw` en la raíz del proyecto.
    Crea la carpeta si no existe.
    """
    root = get_project_root()
    raw_dir = os.path.join(root, "data", "raw")
    os.makedirs(raw_dir, exist_ok=True)
    return raw_dir

def data_index_dir() -> str:
    """
    Devuelve la ruta absoluta de `data/index` en la raíz del proyecto.
    Crea la carpeta si no existe.
    """
    root = get_project_root()
    index_dir = os.path.join(root, "data", "index")
    os.makedirs(index_dir, exist_ok=True)
    return index_dir