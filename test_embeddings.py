import time

from app.services.embeddings import embed_texts

if __name__ == "__main__":
    texts = ["The quick brown fox jumps over the lazy dog.", "Hermes is a RAG agent."]

    start = time.perf_counter()
    vectors = embed_texts(texts)
    elapsed = time.perf_counter() - start

    print(f"Got {len(vectors)} vectors in {elapsed:.3f}s.")
    for i, vector in enumerate(vectors):
        print(f"Vector {i}: dimension={len(vector)}, first 5 values={vector[:5]}")
