from pathlib import Path
from uuid import uuid4
from contextlib import asynccontextmanager

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException
)

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from database import (
    init_db,
    save_document,
    list_documents,
    save_chat,
    get_chat_history
)

from document_processor import (
    extract_text,
    create_chunks
)

from rag import (
    collection,
    store_chunks,
    answer_from_documents
)

from agent import run_agent


BASE_DIR = Path(__file__).resolve().parent

MAX_FILE_SIZE = 10 * 1024 * 1024

ALLOWED_TYPES = {".pdf", ".docx", ".txt"}


# Initialize database

@asynccontextmanager
async def lifespan(app: FastAPI):

    init_db()

    yield


app = FastAPI(
    title="AI Personal Knowledge Assistant",
    description="FastAPI + RAG + ChromaDB + AI Agent",
    version="1.0",
    lifespan=lifespan
)


# Mount frontend files

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "frontend"),
    name="static"
)


# Request model

class QuestionRequest(BaseModel):

    question: str = Field(
        min_length=2,
        max_length=2000
    )


# Home page

@app.get("/", include_in_schema=False)
def home():

    return FileResponse(
        BASE_DIR / "frontend" / "index.html"
    )


# API 1: Upload document

@app.post("/documents/upload", status_code=201)
def upload_document(file: UploadFile = File(...)):

    filename = Path(file.filename or "").name

    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_TYPES:

        raise HTTPException(
            status_code=400,
            detail="Only PDF, DOCX and TXT files are allowed"
        )

    content = file.file.read(MAX_FILE_SIZE + 1)

    if not content:

        raise HTTPException(
            status_code=400,
            detail="File is empty"
        )

    if len(content) > MAX_FILE_SIZE:

        raise HTTPException(
            status_code=413,
            detail="Maximum file size is 10 MB"
        )

    try:

        pages = extract_text(filename, content)

        chunks = create_chunks(pages)

    except Exception:

        raise HTTPException(
            status_code=400,
            detail="Unable to read the document"
        )

    if not chunks:

        raise HTTPException(
            status_code=400,
            detail="No readable text found in the document"
        )

    doc_id = str(uuid4())

    try:

        total_chunks = store_chunks(
            doc_id,
            filename,
            chunks
        )

        save_document(
            doc_id,
            filename,
            total_chunks
        )

    except Exception:

        # Remove vectors if upload fails

        try:
            collection.delete(
                where={"document_id": doc_id}
            )
        except Exception:
            pass

        raise HTTPException(
            status_code=500,
            detail="Document storage failed"
        )

    return {
        "message": "Document uploaded successfully",
        "document_id": doc_id,
        "filename": filename,
        "total_chunks": total_chunks,
        "embedding_dimensions": 384
    }


# API 2: List documents

@app.get("/documents")
def get_documents():

    documents = list_documents()

    return {
        "total_documents": len(documents),
        "documents": documents
    }


# API 3: Direct RAG question answering

@app.post("/chat/ask")
def ask_question(request: QuestionRequest):

    question = request.question.strip()

    if not question:

        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty"
        )

    try:

        result = answer_from_documents(question)

        save_chat(
            question,
            result["answer"],
            "RAG"
        )

        return result

    except Exception:

        raise HTTPException(
            status_code=502,
            detail="Unable to generate answer. Check server configuration."
        )


# API 4: Agent chat

@app.post("/agent/chat")
def agent_chat(request: QuestionRequest):

    question = request.question.strip()

    if not question:

        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty"
        )

    try:

        result = run_agent(question)

        save_chat(
            question,
            result["answer"],
            "AGENT"
        )

        return result

    except Exception:

        raise HTTPException(
            status_code=502,
            detail="Agent execution failed. Check server configuration."
        )


# API 5: Chat history

@app.get("/chat/history")
def chat_history():

    return {
        "history": get_chat_history()
    }