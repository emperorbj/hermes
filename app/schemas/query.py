from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str


class SourceOut(BaseModel):
    document_id: str
    filename: str | None
    chunk_index: int
    relevance_score: float


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceOut]
