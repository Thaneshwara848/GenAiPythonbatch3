# AI Personal Knowledge Assistant

## Technology

Python, FastAPI, OpenAI, Sentence Transformers,
ChromaDB, MySQL, SQLite, HTML, CSS and JavaScript.

## Installation

Create a virtual environment:

```bash
python -m venv venv
```

Activate the virtual environment on Windows:

```powershell
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a MySQL database:

```sql
CREATE DATABASE knowledge_assistant
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
```

Create a `.env` file and configure `OPENAI_API_KEY` and the MySQL connection:

```dotenv
OPENAI_API_KEY=your_openai_api_key
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=your_mysql_user
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=knowledge_assistant
```

The application creates the MySQL `chat_history` table at startup. Existing
chat history in `data/knowledge.db` is imported to MySQL idempotently;
SQLite continues to store document metadata.

## Run Application

```bash
uvicorn main:app --reload
```

## URLs

Frontend: http://127.0.0.1:8000

Swagger: http://127.0.0.1:8000/docs

## Features

- Upload PDF, DOCX and TXT documents
- Extract text
- Overlapping chunking
- Local embedding generation
- Persistent ChromaDB
- RAG question answering
- Single AI Agent
- Manual tool calling
- Source references
- MySQL chat history

## Agent Tools

- list_documents
- search_documents
- answer_from_documents

## Testing

Upload sample_documents/HR_Policy.txt.

Ask: How many casual leaves are allowed?

Expected: 12 casual leaves per year.

## Limitations

Designed for local single-user demonstration.
Scanned PDFs require optional OCR.
Do not expose publicly without authentication.