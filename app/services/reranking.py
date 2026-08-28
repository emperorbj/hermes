import os

from dotenv import load_dotenv
from langchain_community.document_compressors import JinaRerank

load_dotenv()

reranker = JinaRerank(jina_api_key=os.environ["JINA_API_KEY"])


def rerank_candidates(query: str, candidates: list[dict], top_n: int = 5) -> list[dict]:
    if not candidates:
        return []

    texts = [candidate["text"] for candidate in candidates]
    results = reranker.rerank(texts, query, top_n=top_n)

    return [{**candidates[result["index"]], "relevance_score": result["relevance_score"]} for result in results]
