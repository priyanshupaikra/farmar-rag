# Flask + MongoDB + Gemini RAG (with Auth & History)

A minimal starter that lets a logged-in user ask questions about **their own data** stored in MongoDB collections. 
We build embeddings with Gemini, store chunked JSON in `rag_chunks`, retrieve top-k contexts, and answer with Gemini.

## Features
- Register/Login (JWT)
- Conversation history per user
- Ingest data from collections tied to `userId`
- RAG retrieval over JSON chunks (cosine similarity in Python)
- Simple endpoints you can call from any frontend
- External API endpoints for integration with other applications (e.g., Next.js)

## Collections used
- `users` (password hashed with bcrypt)
- `currentlocations` (user coordinates)
- `weathers` (current + forecast)
- `vegetationanalyses` (NDVI/EVI/MSI summaries)
- `rag_chunks` (created by /api/ingest)
- `conversations` (saved chat history)

## Setup

1) Create virtualenv and install deps
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2) Create `.env` from example and fill secrets
```bash
cp .env.example .env
# Put your real MONGODB_URI, GEMINI_API_KEY, JWT_SECRET_KEY
```

3) Run the server
```bash
python app.py
```

## API

### Register
`POST /api/register`
```json
{ "name": "Priyanshu", "email": "p@example.com", "password": "secret" }
```
=> `{ "userId": "…", "token": "JWT" }`

### Login
`POST /api/login`
```json
{ "email": "p@example.com", "password": "secret" }
```

### Ingest (build embeddings for the logged-in user)
`POST /api/ingest` with `Authorization: Bearer <JWT>`

### Ask a question
`POST /api/ask` with `Authorization: Bearer <JWT>`
```json
{ "question": "What was my latest vegetation assessment?", "top_k": 6, "history_id": "<optional>" }
```
=> returns `answer`, `contexts` (metadata only), and `history_id` for threading.

### Get history
`GET /api/history` with `Authorization: Bearer <JWT>`

### Set location (test helper)
`POST /api/location` with `Authorization: Bearer <JWT>`
```json
{ "lat": 28.59, "lon": 77.01 }
```

## External API (for Next.js and other integrations)

### Chat with RAG system
`POST /api/external/chat` with headers `X-API-Key` and `X-User-ID`
```json
{ "message": "What was my latest vegetation assessment?", "session_id": "<optional>" }
```

### Get user data
`GET /api/external/user-data` with headers `X-API-Key` and `X-User-ID`

### Get chat history
`GET /api/external/chat/history?session_id=<optional>` with headers `X-API-Key` and `X-User-ID`

### Get chat sessions
`GET /api/external/chat/sessions` with headers `X-API-Key` and `X-User-ID`

### Create new chat session
`POST /api/external/chat/session/new` with headers `X-API-Key` and `X-User-ID`

### Delete chat history
`POST /api/external/chat/delete` with headers `X-API-Key` and `X-User-ID`

See `NEXTJS_INTEGRATION.md` for detailed usage instructions.

## Notes
- For **scale**, switch to **MongoDB Atlas Vector Search** and create a vector index on `rag_chunks.embedding` to avoid loading all chunks into memory.
- The ingest step **chunks JSON** and embeds each chunk with `text-embedding-004`.
- The answer step uses `gemini-1.5-pro` by default (override with env `GEN_MODEL`). 
- The prompt forces the model to rely only on provided CONTEXT.
