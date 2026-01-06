from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_crawl
from app.api import routes_preprocess
from app.api import routes_index
from app.api import routes_search
from app.index.storage import init_db

app = FastAPI(title="Practica Final RI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # para desarrollo; más adelante restringe
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar base de datos al arrancar
init_db()

app.include_router(routes_crawl.router)
app.include_router(routes_preprocess.router)
app.include_router(routes_index.router)
app.include_router(routes_search.router)

@app.get("/")
def root():
    return {"status": "ok", "message": "FastAPI funcionando"}

@app.get("/ping")
def ping():
    return {"pong": True}