# Plate & Pal — AI food ordering capstone

A fictional food-ordering application using FastAPI, MySQL, OpenAI and ChromaDB. Orders, inventory, conversations, action confirmations and tool audits persist in MySQL. There are no real payments or deliveries.

## Setup on Windows

1. Start MySQL 8 and create an empty `food_ai` database if it does not exist:
   ```sql
   CREATE DATABASE IF NOT EXISTS food_ai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```
2. From this directory, create and activate a virtual environment and install dependencies:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```
3. Configure `.env` using `.env.example` as a template. The provided local `.env` already points to localhost MySQL. Add your `OPENAI_API_KEY`; never commit `.env`. Set `OPENAI_MODEL` if needed. The OpenAI key is only used server-side.
4. Run:
   ```powershell
   python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
   ```
   Open `http://127.0.0.1:8000` for the app, `http://127.0.0.1:8000/docs` for Swagger, and `/health` for the health check. Keep `INTERNAL_API_BASE_URL` aligned with the listening port; it must be a localhost HTTP origin.

On first startup the app creates missing tables and seeds 10 menu items, three demo accounts and three fictional orders. Existing data is not reset. `migrations\001_initial.sql` is the frozen initial schema for an empty database; use it **instead of** automatic creation when manually provisioning the schema. `create_all` does not migrate existing tables; future schema changes need separate migrations.

### Demo accounts

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `admin123` |
| Customer | `alice` | `alice123` |
| Customer | `bob` | `bob123` |

These are intentionally public demo credentials, not production credentials. HTTP Basic must be protected by HTTPS outside localhost. Do not expose this demonstration server publicly or use it for real accounts.

## Using the application

- Browse or filter the live menu. Sign in, add items to the basket and place a simulated order. The server verifies prices and available portions; a cancellation restores capacity once.
- Sign in as admin to create, update or disable menu items, advance order statuses, or upload PDF, DOCX and UTF-8 TXT documents (5 MB maximum). Upload each of the five fictional starter documents in `knowledge_base` after adding the OpenAI key. Uploading indexes them with OpenAI embeddings; replacing a filename activates a new version. `/api/documents/{id}/reindex` re-indexes a stored document.
- Sign in as a customer and create a conversation. Ask about the menu, policies or orders. The assistant uses live APIs and retrieved document evidence. It proposes create/cancel operations but only the explicit **Confirm** button can execute them. Confirmation expires after 15 minutes; changed prices or availability require a new proposal. After a network interruption, retry a processing action to reconcile it safely.
- Conversation history and pending actions reload after refresh or restart. Source references identify the document, page/section and version. Documents are untrusted evidence, not instructions. Declared allergens are fictional and cross-contact cannot be ruled out.

Without an OpenAI key, browsing and manual ordering still work. Chat and document indexing return a safe 503 error. Prompts and uploaded document text are sent to OpenAI when AI features are used; Chroma vectors are stored under `CHROMA_PATH`, and uploaded document bytes under `uploads`. Both directories are ignored by Git. Back up these directories alongside MySQL if persistence is required.

## API and implementation

Use `/docs` to explore the public menu, protected order and chat routes, and admin endpoints. Protected endpoints use HTTP Basic. `POST /api/orders` requires an `Idempotency-Key` header. The API uses a stable error envelope (`code`, `message`, `request_id`). MySQL row locks protect inventory and cancellation; unit prices are snapshotted. Owner checks hide other users' orders and chat sessions. The chatbot's allowlisted tools call the same local REST API with the authenticated identity. AI output is not proof of an executed operation; the confirmed API result is authoritative.

`main.py` wires the app; `models.py`, `schemas.py`, `api.py`, `business.py`, `security.py`, `rag.py`, and `chat.py` separate persistence, validation, REST, business rules, authentication, retrieval and orchestration. The rate limiter is process-local and intended only for this demo.

## Tests

Tests modify a **separate** MySQL database. Create `food_ai_test` first, then set the connection string (replace the placeholder with your local password):

```powershell
$env:TEST_DATABASE_URL = 'mysql+pymysql://root:YOUR_PASSWORD@127.0.0.1:3306/food_ai_test'
python -m pytest -q tests
Remove-Item Env:TEST_DATABASE_URL
```

Tests cover authorization, validation, idempotency, cancellation, concurrent last-portion ordering, persisted chat errors, mocked agent confirmations and mocked document retrieval. They do not call OpenAI. After adding a key, manually upload the starter documents and try the example prompts in the case study; live AI output and model availability are not deterministic.

## Data and limitations

This is a localhost learning demo, not a production system. Chat and order history are retained indefinitely unless an administrator removes them directly from the database, along with related records in foreign-key order; there is no self-service deletion endpoint or automatic retention policy. The process-local rate limiter is not shared across workers. Passwords are bcrypt-hashed, but demo credentials, local HTTP, root database access and manual backups are unsuitable for production.
