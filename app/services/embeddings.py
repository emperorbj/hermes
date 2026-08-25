import os

from dotenv import load_dotenv
from langchain_community.embeddings import JinaEmbeddings

load_dotenv()

EMBEDDING_MODEL = "jina-embeddings-v3"

embeddings_client = JinaEmbeddings(
    jina_api_key=os.environ["JINA_API_KEY"],
    model_name=EMBEDDING_MODEL,
)


def embed_texts(texts: list[str]) -> list[list[float]]:
    return embeddings_client.embed_documents(texts)


def embed_query(text: str) -> list[float]:
    return embeddings_client.embed_query(text)
