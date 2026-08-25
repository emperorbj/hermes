import os

from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

load_dotenv()

PINECONE_API_KEY = os.environ["PINECONE_API_KEY"]
PINECONE_INDEX_NAME = os.environ["PINECONE_INDEX_NAME"]
EMBEDDING_DIMENSION = 1024

pc = Pinecone(api_key=PINECONE_API_KEY)

existing_indexes = [index.name for index in pc.list_indexes()]

if PINECONE_INDEX_NAME in existing_indexes:
    print(f"Index '{PINECONE_INDEX_NAME}' already exists, skipping creation.")
else:
    pc.create_index(
        name=PINECONE_INDEX_NAME,
        dimension=EMBEDDING_DIMENSION,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )
    print(f"Created index '{PINECONE_INDEX_NAME}'.")
