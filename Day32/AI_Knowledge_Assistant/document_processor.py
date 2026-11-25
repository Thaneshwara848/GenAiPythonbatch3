import os
from io import BytesIO
from pathlib import Path

from dotenv import load_dotenv
from pypdf import PdfReader
from docx import Document

load_dotenv()

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 150))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 30))

if not 0 <= CHUNK_OVERLAP < CHUNK_SIZE:
    raise ValueError("Invalid chunk size or overlap")


# STEP 1: Extract text

def extract_text(filename, content):

    extension = Path(filename).suffix.lower()

    pages = []

    if extension == ".pdf":

        reader = PdfReader(BytesIO(content))

        for index, page in enumerate(reader.pages):

            text = page.extract_text() or ""

            pages.append({
                "text": text,
                "page": index + 1
            })

    elif extension == ".docx":

        document = Document(BytesIO(content))

        text = "\n".join(
            paragraph.text
            for paragraph in document.paragraphs
        )

        pages.append({
            "text": text,
            "page": 0
        })

    elif extension == ".txt":

        text = content.decode("utf-8-sig")

        pages.append({
            "text": text,
            "page": 0
        })

    else:
        raise ValueError("Unsupported file type")

    return pages


# STEP 2: Create overlapping chunks

def create_chunks(pages):

    chunks = []

    for page in pages:

        words = page["text"].split()

        start = 0

        while start < len(words):

            end = start + CHUNK_SIZE

            chunk_text = " ".join(words[start:end])

            chunks.append({
                "text": chunk_text,
                "page": page["page"]
            })

            if end >= len(words):
                break

            start += CHUNK_SIZE - CHUNK_OVERLAP

    return chunks