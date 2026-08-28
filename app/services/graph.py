from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.services.generation import Citation, generate_answer
from app.services.guardrails import check_query, redact_pii
from app.services.reranking import rerank_candidates
from app.services.retrieval import hybrid_retrieve


class QueryState(TypedDict):
    query: str
    candidates: list[dict]  # after hybrid retrieval (dense + lexical merged, not yet reranked)
    context_chunks: list[dict]  # after reranking — final context handed to generation
    answer: str
    citations: list[Citation]


def query_guardrail_node(state: QueryState) -> dict:
    check_query(state["query"])
    return {"query": redact_pii(state["query"])}


def retrieval_node(state: QueryState) -> dict:
    candidates = hybrid_retrieve(state["query"])
    return {"candidates": candidates}


def reranking_node(state: QueryState) -> dict:
    context_chunks = rerank_candidates(state["query"], state["candidates"])
    return {"context_chunks": context_chunks}


def generation_node(state: QueryState) -> dict:
    result = generate_answer(state["query"], state["context_chunks"])
    return {"answer": result.answer, "citations": result.citations}


def output_guardrail_node(state: QueryState) -> dict:
    return {"answer": redact_pii(state["answer"])}


graph_builder = StateGraph(QueryState)

graph_builder.add_node("query_guardrail", query_guardrail_node)
graph_builder.add_node("retrieval", retrieval_node)
graph_builder.add_node("reranking", reranking_node)
graph_builder.add_node("generation", generation_node)
graph_builder.add_node("output_guardrail", output_guardrail_node)

graph_builder.add_edge(START, "query_guardrail")
graph_builder.add_edge("query_guardrail", "retrieval")
graph_builder.add_edge("retrieval", "reranking")
graph_builder.add_edge("reranking", "generation")
graph_builder.add_edge("generation", "output_guardrail")
graph_builder.add_edge("output_guardrail", END)

query_graph = graph_builder.compile()


def run_query_graph(query: str) -> QueryState:
    return query_graph.invoke({"query": query})
