from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, documents, query, tts

app = FastAPI(title="Hermes AI RAG API", version="0.1.0")

# Wildcard CORS — allows requests from any frontend origin. Note: per the CORS
# spec, a wildcard origin ("*") cannot be combined with allow_credentials=True
# (browsers/Starlette both enforce this) — not an issue here since auth is a
# Bearer token attached manually in JS, not a cookie the browser sends automatically.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(query.router)
app.include_router(tts.router)


@app.get("/health")
def health():
    return {"status": "ok"}
