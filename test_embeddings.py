from app.services.embeddings import embed_texts

if __name__ == "__main__":
    texts = ["The quick brown fox jumps over the lazy dog.", "Hermes is a RAG agent."]
    vectors = embed_texts(texts)

    print(f"Got {len(vectors)} vectors.")
    for i, vector in enumerate(vectors):
        print(f"Vector {i}: dimension={len(vector)}, first 5 values={vector[:5]}")
