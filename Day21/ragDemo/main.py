
import os
from pathlib import Path

import fitz
import tiktoken
import chromadb

from docx import Document
from dotenv import load_dotenv
from openai import OpenAI

# Load API key
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL = "text-embedding-3-small"
CHUNK_SIZE = 100

# STEP 1: Document
filename = input("Enter Document Path: ").strip().strip('"')

# STEP 2: Text Extraction
def extract_text(filename):
    ext = Path(filename).suffix.lower()

    if ext == ".txt":
        return Path(filename).read_text(encoding="utf-8-sig")

    elif ext == ".pdf":
        with fitz.open(filename) as pdf:
            return "\n".join(page.get_text() for page in pdf)

    elif ext == ".docx":
        doc = Document(filename)
        return "\n".join(p.text for p in doc.paragraphs)

    else:
        raise ValueError("Only PDF, DOCX, TXT supported")

text = extract_text(filename)

print("\n========== TEXT EXTRACTION ==========")
print(text)

# STEP 3: Tokenization
encoder = tiktoken.encoding_for_model(MODEL)
tokens = encoder.encode(text)

print("\n========== TOKENIZATION ==========")
print("Total Tokens:", len(tokens))
print("Token IDs:", tokens)

# STEP 4: Chunking
chunks = []

for i in range(0, len(tokens), CHUNK_SIZE):
    chunk = encoder.decode(tokens[i:i + CHUNK_SIZE])

    if chunk.strip():
        chunks.append(chunk)

if not chunks:
    raise ValueError("No extractable text found in document")

print("\n========== CHUNKING ==========")

for i, chunk in enumerate(chunks, 1):
    print(f"Chunk {i}: {chunk}")

# STEP 5: Embeddings
response = client.embeddings.create(
    model=MODEL,
    input=chunks
)

# STEP 6: Extract Vectors
vectors = [item.embedding for item in response.data]

print("\n========== VECTORS ==========")

for i, vector in enumerate(vectors, 1):
    print(f"Vector {i}: {vector[:5]} ...")
    print("Dimensions:", len(vector))

# STEP 7: Store in ChromaDB
db = chromadb.PersistentClient(path="./vector_db")

collection = db.get_or_create_collection(
    name="documents"
)

# Deterministic IDs per file and chunk
file_id = __import__("hashlib").sha256(
    str(Path(filename).resolve()).encode()
).hexdigest()[:16]

ids = [f"{file_id}_chunk_{i}" for i in range(len(chunks))]

# Replace previous chunks from the same file
old = collection.get(where={"file_id": file_id})
if old["ids"]:
    collection.delete(ids=old["ids"])

collection.upsert(
    ids=ids,
    documents=chunks,
    embeddings=vectors,
    metadatas=[
        {"source": Path(filename).name, "file_id": file_id}
        for _ in chunks
    ]
)

print("\n========== CHROMADB ==========")
print("Vectors stored successfully!")
print("Total Records:", collection.count())

# STEP 8: Similarity Search
question = input("\nAsk a Question: ").strip()

if question:
    query_response = client.embeddings.create(
        model=MODEL,
        input=question
    )

    query_vector = query_response.data[0].embedding

    results = collection.query(
        query_embeddings=[query_vector],
        n_results=min(2, collection.count())
    )

    print("\n========== SEARCH RESULTS ==========")

    for i, doc in enumerate(results["documents"][0], 1):
        print(f"\nMatch {i}: {doc}")
        print("Distance:", results["distances"][0][i - 1])
