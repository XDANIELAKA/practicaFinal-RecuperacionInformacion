import os
import sys

# Obtener la ruta raíz del proyecto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Construir la ruta al directorio backend/src
SRC_PATH = os.path.join(BASE_DIR, "backend", "src")

# Asegurarse de que backend/src está en el PYTHONPATH
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

# Arrancar Uvicorn
import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)