from fastapi import FastAPI

app = FastAPI(title="Practica Final RI")

@app.get("/")
def root():
    return {"status": "ok", "message": "FastAPI funcionando"}

@app.get("/ping")
def ping():
    return {"pong": True}
