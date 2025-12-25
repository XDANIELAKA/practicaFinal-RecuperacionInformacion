from fastapi import FastAPI
from app.api import routes_crawl
from app.api import routes_preprocess

app = FastAPI(title="Practica Final RI")

app.include_router(routes_crawl.router)

app.include_router(routes_preprocess.router)

@app.get("/")
def root():
    return {"status": "ok", "message": "FastAPI funcionando"}

@app.get("/ping")
def ping():
    return {"pong": True}
