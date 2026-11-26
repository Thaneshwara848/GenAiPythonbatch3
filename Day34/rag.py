import hashlib
import io
from pathlib import Path

import chromadb
import fitz
from docx import Document as DocxDocument
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from openai import OpenAI, OpenAIError
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import Document, User
from security import admin_user

router = APIRouter(prefix="/api")
MAX_BYTES = 5 * 1024 * 1024


def ai_client():
    if not settings().openai_api_key:
        raise HTTPException(503, "OpenAI API key is not configured")
    return OpenAI(api_key=settings().openai_api_key, timeout=30, max_retries=1)


def collection():
    return chromadb.PersistentClient(path=settings().chroma_path).get_or_create_collection(
        name="travel_policies", metadata={"hnsw:space": "cosine"})


def extract(filename: str, data: bytes):
    extension = Path(filename).suffix.lower()
    if extension == ".txt":
        try:
            return [(1, data.decode("utf-8"))]
        except UnicodeDecodeError:
            raise HTTPException(422, "TXT files must use UTF-8")
    if extension == ".pdf":
        try:
            with fitz.open(stream=data, filetype="pdf") as doc:
                return [(i + 1, page.get_text()) for i, page in enumerate(doc)]
        except (RuntimeError, ValueError):
            raise HTTPException(422, "Invalid PDF document")
    if extension == ".docx":
        try:
            return [(1, "\n".join(p.text for p in DocxDocument(io.BytesIO(data)).paragraphs))]
        except (ValueError, KeyError, OSError):
            raise HTTPException(422, "Invalid DOCX document")
    raise HTTPException(415, "Only PDF, DOCX and TXT are supported")


def chunk_text(text: str):
    text = " ".join(text.split())
    return [text[i:i + 800] for i in range(0, len(text), 700) if text[i:i + 800].strip()]


@router.post("/documents", status_code=201)
async def upload_document(file: UploadFile = File(...), admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    filename = Path((file.filename or "").replace("\\", "/")).name
    if not filename or len(filename) > 255:
        raise HTTPException(422, "Invalid filename")
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Document exceeds 5 MB")
    pages = extract(filename, data)
    chunks = [(page, text) for page, content in pages for text in chunk_text(content)]
    if not chunks or len(chunks) > 500:
        raise HTTPException(422, "Document has no text or exceeds 500 chunks")
    previous = db.scalars(select(Document).where(Document.filename == filename).order_by(Document.version.desc())).all()
    document = Document(filename=filename, sha256=hashlib.sha256(data).hexdigest(),
                        version=(previous[0].version + 1 if previous else 1), status="INDEXING", uploaded_by=admin.id)
    db.add(document)
    db.commit()
    try:
        embeddings = ai_client().embeddings.create(model="text-embedding-3-small", input=[text for _, text in chunks])
        collection().add(ids=[f"{document.id}-{i}" for i in range(len(chunks))],
                         embeddings=[entry.embedding for entry in embeddings.data],
                         documents=[text for _, text in chunks],
                         metadatas=[{"document_id": document.id, "filename": filename, "page": page, "version": document.version} for page, _ in chunks])
    except (OpenAIError, HTTPException, ValueError, RuntimeError) as exc:
        document.status = "FAILED"
        db.commit()
        raise HTTPException(503, "Document indexing failed; check AI and vector database configuration") from exc
    for old in previous:
        if old.status == "ACTIVE":
            old.status = "SUPERSEDED"
    document.status = "ACTIVE"
    db.commit()
    return {"id": document.id, "filename": filename, "version": document.version, "chunks": len(chunks)}


def retrieve(question: str, db: Session):
    active = db.scalars(select(Document.id).where(Document.status == "ACTIVE")).all()
    if not active:
        return []
    try:
        embedding = ai_client().embeddings.create(model="text-embedding-3-small", input=question).data[0].embedding
        result = collection().query(query_embeddings=[embedding], n_results=4,
                                    where={"document_id": {"$in": active}},
                                    include=["documents", "metadatas", "distances"])
    except (OpenAIError, ValueError, RuntimeError) as exc:
        raise HTTPException(503, "Policy retrieval is temporarily unavailable") from exc
    return [
        {"text": text, "filename": meta["filename"], "page": meta["page"], "version": meta["version"], "chunk_id": chunk_id}
        for text, meta, chunk_id, distance in zip(result["documents"][0], result["metadatas"][0], result["ids"][0], result["distances"][0])
        if distance <= 0.6
    ]
