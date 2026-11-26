import hashlib
import io
from pathlib import Path

import chromadb
import pymupdf
from docx import Document as DocxDocument
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import get_settings
from database import get_db
from models import Document, User
from security import admin_user

router = APIRouter(prefix="/api")
MAX_BYTES = 5 * 1024 * 1024
UPLOAD_DIR = Path("uploads")


def client():
    settings = get_settings()
    if not settings.openai_api_key:
        raise HTTPException(503, "OpenAI API key is not configured")
    return OpenAI(api_key=settings.openai_api_key, timeout=30, max_retries=1)


def collection():
    return chromadb.PersistentClient(path=get_settings().chroma_path).get_or_create_collection(
        name="food_policies", metadata={"hnsw:space": "cosine"}
    )


def extract(filename: str, data: bytes):
    extension = Path(filename).suffix.lower()
    if extension == ".pdf":
        with pymupdf.open(stream=data, filetype="pdf") as pdf:
            return [(str(index + 1), page.get_text()) for index, page in enumerate(pdf)]
    if extension == ".docx":
        doc = DocxDocument(io.BytesIO(data))
        return [("1", "\n".join(p.text for p in doc.paragraphs))]
    if extension == ".txt":
        return [("1", data.decode("utf-8"))]
    raise HTTPException(422, "Only PDF, DOCX and UTF-8 TXT files are supported")


def chunks(pages):
    result = []
    for page, text in pages:
        text = text.strip()
        start = 0
        while start < len(text):
            part = text[start:start + 800]
            if part.strip():
                result.append((page, part))
            if start + 800 >= len(text):
                break
            start += 700
    return result


def index_document(db: Session, document: Document, data: bytes):
    previous_status = document.status
    try:
        parts = chunks(extract(document.filename, data))
        if not parts:
            raise HTTPException(422, "Document contains no extractable text")
        embeddings = client().embeddings.create(model="text-embedding-3-small", input=[text for _, text in parts])
        ids = [f"{document.id}-{i}" for i in range(len(parts))]
        collection().upsert(
            ids=ids,
            embeddings=[item.embedding for item in embeddings.data],
            documents=[text for _, text in parts],
            metadatas=[{"document_id": document.id, "filename": document.filename, "page": page,
                        "version": document.version, "chunk_id": ids[i]} for i, (page, _) in enumerate(parts)],
        )
        old = db.scalars(select(Document).where(Document.filename == document.filename,
                         Document.status == "ACTIVE", Document.id != document.id).with_for_update()).all()
        for item in old:
            item.status = "SUPERSEDED"
        document.status = "ACTIVE"
        db.commit()
    except Exception:
        db.rollback()
        document = db.get(Document, document.id)
        document.status = "ACTIVE" if previous_status == "ACTIVE" else "FAILED"
        db.commit()
        raise


def retrieve(db: Session, question: str):
    active = db.scalars(select(Document.id).where(Document.status == "ACTIVE")).all()
    if not active:
        return []
    vector = client().embeddings.create(model="text-embedding-3-small", input=[question]).data[0].embedding
    result = collection().query(query_embeddings=[vector], n_results=4,
                                where={"document_id": {"$in": active}})
    return [
        {"text": text, "filename": meta["filename"], "page": meta["page"],
         "version": meta["version"], "chunk_id": meta["chunk_id"]}
        for text, meta, distance in zip(result["documents"][0], result["metadatas"][0], result["distances"][0])
        if distance <= 0.5
    ]


@router.post("/documents", status_code=201)
async def upload_document(file: UploadFile = File(...), admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    filename = Path((file.filename or "").replace("\\", "/")).name
    if not filename or len(filename) > 255 or Path(filename).suffix.lower() not in {".pdf", ".docx", ".txt"}:
        raise HTTPException(422, "Invalid document filename or type")
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Document exceeds 5 MB")
    try:
        parts = chunks(extract(filename, data))
    except (ValueError, UnicodeDecodeError, RuntimeError, OSError) as exc:
        raise HTTPException(422, "Document could not be read") from exc
    if not parts:
        raise HTTPException(422, "Document contains no extractable text")
    version = (db.scalar(select(Document.version).where(Document.filename == filename).order_by(Document.version.desc()).limit(1)) or 0) + 1
    document = Document(filename=filename, sha256=hashlib.sha256(data).hexdigest(),
                        version=version, status="INDEXING", uploaded_by=admin.id)
    db.add(document)
    db.commit()
    UPLOAD_DIR.mkdir(exist_ok=True)
    (UPLOAD_DIR / str(document.id)).write_bytes(data)
    try:
        index_document(db, document, data)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, "Document indexing is temporarily unavailable") from exc
    return {"id": document.id, "filename": filename, "version": version, "status": document.status}


@router.post("/documents/{document_id}/reindex")
def reindex_document(document_id: int, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(404, "Document not found")
    if document.status == "SUPERSEDED":
        raise HTTPException(409, "Upload a new version instead of re-indexing a superseded document")
    path = UPLOAD_DIR / str(document.id)
    if not path.is_file():
        raise HTTPException(404, "Stored document not found")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != document.sha256:
        raise HTTPException(409, "Stored document checksum does not match")
    try:
        index_document(db, document, data)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, "Document indexing is temporarily unavailable") from exc
    return {"id": document.id, "status": document.status}
