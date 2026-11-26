# Wanderwise: AI Smart Travel Planner

A fictional travel-booking demo with a FastAPI API, MySQL, an HTML/JavaScript interface, a document knowledge base, and one OpenAI tool-calling assistant. No real bookings, payments, or refunds are made.

## Setup on Windows

1. Install Python 3.12 and MySQL 8. Create a database named `travel_ai` using your MySQL administration tool. The current workspace has already been initialized on localhost with the MySQL credentials you supplied.
2. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. Configure `.env` using `.env.example`. The local `.env` is ignored by Git; it contains the supplied local MySQL connection and a generated demo password in `DEMO_PASSWORD`. The three demo usernames are `admin`, `traveller1`, and `traveller2`. Read the local `.env` to obtain their shared demo password. Change these accounts before any non-local use.
4. On a new database, run `python seed.py`. Enter a demo password when prompted. The script creates the initial schema, 10 fictional packages, three users and three sample bookings without clearing existing data. It does not update passwords of existing users. For unattended setup, set the `DEMO_PASSWORD` environment variable before running it.
5. Start with `python -m uvicorn main:app --host 127.0.0.1 --port 8000`. Open `http://127.0.0.1:8000` or `http://127.0.0.1:8000/docs`.

Add your `OPENAI_API_KEY` to `.env` when available and restart the server. Until then, catalog and bookings work; chat and document indexing return an explicit 503. Set `OPENAI_MODEL` as needed. Keep `INTERNAL_API_BASE_URL` pointed at the same local server and port.

## Policies and AI

Sign in as admin and upload the fictional files in `knowledge_base` using the page or `POST /api/documents`. Indexing requires the OpenAI key. PDF, DOCX and UTF-8 TXT are accepted, up to 5 MB and 500 chunks per file. Uploading the same filename creates a new active version and supersedes the earlier one. The assistant retrieves only active versions and displays citations.

Chat sessions and messages are stored in MySQL. The assistant uses tools for live catalog and owned bookings; a booking or cancellation requested through chat is **only prepared** until the user presses Confirm. Terms are checked again by the business endpoint. Pending actions expire after 15 minutes; retrying a processing action uses the same booking idempotency key.

HTTP Basic credentials are retained only in browser memory. This demo binds to localhost; use HTTPS, production authentication, durable distributed rate limiting, appropriate retention/deletion controls, and a least-privilege database account before any real deployment. Documents are untrusted; do not upload sensitive information to a model provider without authorization.

## Tests

```powershell
python -m pytest -q
$env:TEST_MYSQL_CONCURRENCY = '1'
python -m pytest -q tests\test_mysql_concurrency.py
Remove-Item Env:\TEST_MYSQL_CONCURRENCY
```

The regular tests use isolated SQLite and mocked AI. The opt-in concurrency test writes and removes only its own uniquely named records in the configured MySQL database. A live AI test requires a key and separately indexed documents.

## Schema and limitations

The initial schema is created by SQLAlchemy `create_all`; there is currently no versioned schema migration. For an existing installation, back up data and manage schema upgrades separately. MySQL stores users, packages, bookings and price snapshots, chat messages, tool audit records, pending actions and document versions. ChromaDB stores document vectors in `CHROMA_PATH`. The service uses a local in-process rate limiter and is intended for a single demo server, not a multi-worker production deployment.
