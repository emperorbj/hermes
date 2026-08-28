from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_current_user
from app.models import User
from app.schemas.query import QueryRequest, QueryResponse, SourceOut
from app.services.graph import run_query_graph
from app.services.guardrails import GuardrailViolation

router = APIRouter(prefix="/query", tags=["query"])


@router.post("/", response_model=QueryResponse)
def query(payload: QueryRequest, current_user: User = Depends(get_current_user)):
    try:
        result = run_query_graph(payload.question)
    except GuardrailViolation as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    context_chunks = result["context_chunks"]
    chunks_by_key = {(chunk["document_id"], chunk["chunk_index"]): chunk for chunk in context_chunks}
    sources = [
        SourceOut(
            document_id=citation.document_id,
            chunk_index=citation.chunk_index,
            filename=chunks_by_key[(citation.document_id, citation.chunk_index)]["filename"],
            relevance_score=chunks_by_key[(citation.document_id, citation.chunk_index)]["relevance_score"],
        )
        for citation in result["citations"]
    ]

    return QueryResponse(answer=result["answer"], sources=sources)
