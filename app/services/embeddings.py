import os

from dotenv import load_dotenv
from langchain_community.embeddings import JinaEmbeddings

from app.services.cache import get_cached, make_cache_key, set_cached

load_dotenv()

EMBEDDING_MODEL = "jina-embeddings-v3"
EMBEDDING_CACHE_TTL_SECONDS = 60 * 60 * 24 * 30

embeddings_client = JinaEmbeddings(
    jina_api_key=os.environ["JINA_API_KEY"],
    model_name=EMBEDDING_MODEL,
)


def embed_texts(texts: list[str]) -> list[list[float]]:
    keys = [make_cache_key("embedding", EMBEDDING_MODEL, "document", text) for text in texts]
    results = [get_cached(key) for key in keys]

    missing_indices = [i for i, cached in enumerate(results) if cached is None]

    if missing_indices:
        missing_texts = [texts[i] for i in missing_indices]
        fresh_vectors = embeddings_client.embed_documents(missing_texts)

        for i, vector in zip(missing_indices, fresh_vectors):
            results[i] = vector
            set_cached(keys[i], vector, ttl_seconds=EMBEDDING_CACHE_TTL_SECONDS)

    return results


def embed_query(text: str) -> list[float]:
    key = make_cache_key("embedding", EMBEDDING_MODEL, "query", text)
    cached = get_cached(key)
    if cached is not None:
        return cached

    vector = embeddings_client.embed_query(text)
    set_cached(key, vector, ttl_seconds=EMBEDDING_CACHE_TTL_SECONDS)
    return vector
