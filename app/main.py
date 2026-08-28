from fastapi import FastAPI

from app.routers import auth, documents, query

app = FastAPI(title="Hermes AI RAG API", version="0.1.0")

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(query.router)


@app.get("/health")
def health():
    return {"status": "ok"}
