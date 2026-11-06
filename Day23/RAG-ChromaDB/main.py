
from pathlib import Path
import hashlib

import pymupdf
from docx import Document
import tiktoken
import chromadb
from openai import OpenAI
from dotenv import load_dotenv


# LOAD OPENAI API KEY
load_dotenv()
openai_client = OpenAI()


# STEP 1: DOCUMENT TO TEXT
def extract_text(filename):

    ext = Path(filename).suffix.lower()

    if ext == ".txt":
        with open(filename, "r", encoding="utf-8") as file:
            return file.read()

    elif ext == ".pdf":
        with pymupdf.open(filename) as pdf:
            return "\n".join(page.get_text() for page in pdf)

    elif ext == ".docx":
        doc = Document(filename)
        return "\n".join(p.text for p in doc.paragraphs)

    else:
        raise ValueError("Only PDF, DOCX and TXT supported")

# STEP 2: TEXT TO CHUNKS
def split_text(text):

    words = text.split()
    chunks = []

    CHUNK_SIZE = 10

    for i in range(0, len(words), CHUNK_SIZE):
        chunk = " ".join(words[i:i + CHUNK_SIZE])
        chunks.append(chunk)

    return chunks

# STEP 3: CHUNK TO TOKENS
def tokenize(chunk):

    encoder = tiktoken.get_encoding("cl100k_base")
    tokens = encoder.encode(chunk)

    return tokens

# STEP 4: CHUNK TO EMBEDDINGS
def get_embedding(chunk):

    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=chunk
    )

    return response.data[0].embedding


# STEP 5: CREATE CHROMADB
chroma_client = chromadb.PersistentClient(
    path="./chroma_db"
)

collection = chroma_client.get_or_create_collection(
    name="rag_documents"
)


# STEP 6: MAIN PROGRAM
filename = input("Enter file name: ").strip()

# Document to text
text = extract_text(filename)

print("\n===== EXTRACTED TEXT =====")
print(text)

# Text to chunks
chunks = split_text(text)

if not chunks:
    raise ValueError("No text extracted from document")

# Unique document identifier
document_id = hashlib.sha256(
    Path(filename).resolve().as_posix().encode("utf-8")
).hexdigest()[:16]

# Process every chunk
for i, chunk in enumerate(chunks, start=1):

    print(f"\n========== CHUNK {i} ==========")
    print("TEXT:", chunk)

    # Chunk to tokens
    tokens = tokenize(chunk)

    print("\nTOKENS:", tokens)
    print("TOTAL TOKENS:", len(tokens))

    # Chunk to embeddings
    embedding = get_embedding(chunk)

    print("\nFULL EMBEDDING VECTOR:")
    print(embedding)

    print("\nVECTOR DIMENSIONS:", len(embedding))

    # Store in ChromaDB
    chunk_id = f"{document_id}_chunk_{i}"

    collection.upsert(
        ids=[chunk_id],
        documents=[chunk],
        embeddings=[embedding],
        metadatas=[{
            "source": Path(filename).name,
            "chunk_number": i
        }]
    )

    print("\nSTORED IN CHROMADB!")
    print("CHUNK ID:", chunk_id)


# STEP 7: VERIFY DATA IN CHROMADB
print("\n========== CHROMADB DATA ==========")

print("TOTAL STORED CHUNKS:", collection.count())

results = collection.get(
    include=["documents", "embeddings", "metadatas"]
)

for i, record_id in enumerate(results["ids"]):

    print("\nID:", record_id)

    print("TEXT:", results["documents"][i])

    print("METADATA:", results["metadatas"][i])

    print("STORED VECTOR:")
    print(results["embeddings"][i].tolist())

print("\n===== PROCESS COMPLETED =====")
