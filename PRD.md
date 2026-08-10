# Context Store MVP — Product Requirements Document
**Aivaura · v1.0 · August 2026 · Confidential**

---

## Table of Contents

1. [Product Overview and Goals](#1-product-overview-and-goals)
2. [MVP Scope](#2-mvp-scope)
3. [System Architecture](#3-system-architecture)
4. [Connector Specifications](#4-connector-specifications)
5. [Data Processing Pipeline](#5-data-processing-pipeline)
6. [Storage Design](#6-storage-design)
7. [RAG and Retrieval Pipeline](#7-rag-and-retrieval-pipeline)
8. [LLM Abstraction Layer](#8-llm-abstraction-layer)
9. [MCP Server](#9-mcp-server)
10. [API Endpoint Design](#10-api-endpoint-design)
11. [Frontend UI Design](#11-frontend-ui-design)
12. [Complete Tech Stack](#12-complete-tech-stack)
13. [Third-Party Services and Costs](#13-third-party-services-and-costs)
14. [Security and Privacy Standards](#14-security-and-privacy-standards)
15. [Environment Variables Reference](#15-environment-variables-reference)
16. [Project File Structure](#16-project-file-structure)
17. [Development Sequence](#17-development-sequence)
18. [Claude Code Model Recommendation](#18-claude-code-model-recommendation)

---

## 1. Product Overview and Goals

The Context Store is an AI-powered company intelligence platform. It connects to the tools a company already uses, ingests all their data continuously, and creates a single searchable layer on top. Team members ask questions in plain language and get accurate, cited answers from their own company data. AI agents built on top can act on that knowledge proactively.

### MVP Goal

Build a working system with 5 data source connectors, a hybrid retrieval engine, a pluggable LLM layer, an MCP server, and a simple non-technical user interface. Internal team can query company knowledge and get accurate, cited answers within 60 days of starting development.

### Non-goals for this version

- Multi-tenant support (one company only in MVP)
- Proactive agents (read and answer only, no actions)
- Mobile app
- On-premise packaging
- Tally, Zoho, or CRM connectors (next version)

---

## 2. MVP Scope

| In Scope | Out of Scope |
|---|---|
| Google Drive connector | Tally / accounting connectors |
| Gmail connector | Zoho / Salesforce / CRM connectors |
| Microsoft Outlook connector | Proactive agents (alerts, drafts) |
| WhatsApp Business API connector | Multi-language input (Hindi / Gujarati) |
| Google Sheets + Excel file connector | On-premise deployment packaging |
| Document processing pipeline | Voice-to-text input in UI |
| Hybrid vector + keyword search | Role-based access control |
| Pluggable LLM (Ollama / Groq / Claude) | Agent builder interface |
| Source citation on every answer | Analytics dashboard |
| MCP server endpoint | Slack / Teams connector |
| Simple web UI (5 screens) | Multi-user management |
| Audit log of all queries | WhatsApp as answer delivery channel |

---

## 3. System Architecture

Seven layers, each independent. The frontend talks only to the FastAPI backend. The backend handles connectors, processing, storage, and retrieval. The MCP server is a separate process that reads from the same storage layer.

```
┌─────────────────────────────────────────────────────────┐
│           Layer 7 — User Interface                      │
│     Next.js 14 · Chat, Dashboard, Connectors, Admin     │
└───────────────────────────┬─────────────────────────────┘
                            ↓
┌───────────────────────────┐  ┌──────────────────────────┐
│   Layer 6 — API Layer     │  │      MCP Server           │
│   FastAPI · JWT auth      │  │  Port 3001 · Agents here  │
│   REST endpoints          │  │  Separate process         │
└───────────────────────────┘  └──────────────────────────┘
                            ↓
┌───────────────────────────┐  ┌──────────────────────────┐
│  Layer 5 — Retrieval/RAG  │  │   Layer 4 — LLM Layer    │
│  LlamaIndex · Hybrid      │  │  Pluggable via env var   │
│  search · Re-ranking      │  │  Ollama / Groq / Claude  │
└───────────────────────────┘  └──────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                   Layer 3 — Storage                     │
│   Qdrant (vectors) · PostgreSQL (structured) · Redis    │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│              Layer 2 — Processing Pipeline              │
│     Chunking · Embedding · Entity extraction · Celery   │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                  Layer 1 — Connectors                   │
│   Google Drive · Gmail · Outlook · WhatsApp · Sheets    │
└─────────────────────────────────────────────────────────┘
```

---

## 4. Connector Specifications

Each connector is a Python class inheriting from `BaseConnector`. Every connector implements three methods: `authenticate()`, `fetch_documents(since=None)`, and `get_status()`. Celery runs each on a defined schedule.

### 4.1 Google Drive

| Item | Detail |
|---|---|
| Auth method | OAuth 2.0 via Google Cloud Console |
| Library | `google-auth-oauthlib`, `google-api-python-client` |
| Scopes | `drive.readonly` |
| File types handled | Google Docs (export to text), PDF, DOCX, TXT, MD |
| Sync method | Delta sync using `pageToken` from Drive Changes API |
| Sync frequency | Every 2 hours (configurable) |
| What is stored | File content, file name, last modified date, file URL, owner email |
| What is skipped | Files larger than 10MB, video, audio, binary files |

### 4.2 Gmail

| Item | Detail |
|---|---|
| Auth method | OAuth 2.0 — same Google Cloud project as Drive |
| Library | `google-api-python-client` (Gmail API) |
| Scopes | `gmail.readonly` |
| What is fetched | Email subject, sender, recipients, body (plain text), date, thread ID |
| Sync method | History ID based incremental sync |
| Sync frequency | Every 30 minutes |
| Chunking | Long emails split by paragraph. Short emails kept as single chunk. Thread grouped as one document. |
| What is skipped | Spam folder, Trash folder, emails with no text body, calendar invites |

### 4.3 Microsoft Outlook

| Item | Detail |
|---|---|
| Auth method | OAuth 2.0 via Microsoft Azure App Registration (free) |
| Library | `msgraph-sdk` (official Microsoft Python SDK) |
| Scopes | `Mail.Read`, `offline_access` |
| What is fetched | Same as Gmail — subject, sender, body, date, conversation ID |
| Sync method | Delta query using Microsoft Graph `$deltaToken` |
| Sync frequency | Every 30 minutes |
| What is skipped | Junk Email, Deleted Items, calendar items |

### 4.4 WhatsApp Business API

| Item | Detail |
|---|---|
| Auth method | Meta permanent access token from WhatsApp Cloud API dashboard |
| API | Meta WhatsApp Cloud API (free: first 1,000 service conversations/month) |
| Library | `httpx` (async HTTP calls to Meta API) |
| Receive method | Webhook — Meta sends messages to `POST /api/v1/webhooks/whatsapp` |
| What is captured | Message text, sender phone number, timestamp, message type, media captions |
| Voice notes | Downloaded from Meta URL, transcribed via `openai-whisper` (local, free), stored as text |
| What is skipped | Images without caption, video files, sticker messages |
| Local dev note | Use `ngrok http 8000` to expose webhook. Free ngrok account gives a static domain. |

### 4.5 Google Sheets and Excel

| Item | Detail |
|---|---|
| Google Sheets auth | Same OAuth as Drive. Scope: `spreadsheets.readonly` |
| Google Sheets library | `google-api-python-client` (Sheets API v4) |
| Excel files | Uploaded via direct upload endpoint. Parsed locally. |
| Excel library | `openpyxl` for .xlsx, `xlrd` for legacy .xls |
| How sheets are stored | Each tab becomes one document. Rows converted to readable text: "Row 3: Product=Laptop, Qty=5, Price=45000" |
| Sync frequency | Every 1 hour for Sheets. Excel files on upload only. |
| Row limit | First 10,000 rows per sheet tab. Beyond that, warn the admin. |

---

## 5. Data Processing Pipeline

Every document from every connector passes through this pipeline before being stored. Pipeline runs as Celery background tasks — never blocks the API.

```
Raw document arrives from connector
        ↓
[Step 1: Clean]
Strip HTML tags, remove duplicate whitespace,
normalize line breaks, detect language
        ↓
[Step 2: Chunk]
Split into overlapping chunks of 512 tokens
with 64-token overlap. Use sentence boundaries.
Short documents (< 200 tokens) stay as one chunk.
        ↓
[Step 3: Extract metadata]
Source type, source name, document URL/ID,
date, author, chunk index, total chunks
        ↓
[Step 4: Embed]
Send each chunk to embedding model.
Get back a 768-dimensional vector.
Model: nomic-embed-text via Ollama (local, free)
        ↓
[Step 5: Store]
Vector + metadata → Qdrant
Document record + chunk refs → PostgreSQL
Mark document as indexed in sync status table
```

### Chunking Strategy

- **Text documents, emails:** `SentenceWindowNodeParser` from LlamaIndex. 512 token window, 64 token overlap.
- **Spreadsheet rows:** Group 20 rows per chunk. Each chunk includes the header row.
- **WhatsApp messages:** Group messages by conversation and day. One chunk per day per conversation.

### Embedding Model

> **Primary choice: `nomic-embed-text` via Ollama**
>
> Cost: Free. Runs entirely on your local machine or VPS. 768-dimensional embeddings. Good quality for English and Hindi text. Pull with: `ollama pull nomic-embed-text`. No data leaves your infrastructure.

---

## 6. Storage Design

### PostgreSQL Tables

```sql
users           — id, email, hashed_password, role, created_at
connectors      — id, user_id, type, status, oauth_token_encrypted,
                  last_sync_at, document_count, error_message
documents       — id, connector_id, source_id, source_url, title,
                  author, created_at, indexed_at, chunk_count
chunks          — id, document_id, chunk_index, text, token_count
audit_logs      — id, user_id, query_text, response_text,
                  sources_used, created_at
sync_state      — id, connector_id, state_key, state_value
                  (stores delta tokens, history IDs, page tokens)
```

### Qdrant Collection

```json
Collection: "company_knowledge"
Vector size: 768
Distance: Cosine

Payload per vector:
{
  "chunk_id": "string",
  "document_id": "string",
  "source_type": "gmail | drive | outlook | whatsapp | sheets",
  "source_name": "string",
  "document_title": "string",
  "document_url": "string",
  "author": "string",
  "date": "ISO string",
  "text": "string",
  "chunk_index": "integer"
}
```

### Redis Usage

- **Celery broker:** Routes background sync tasks to workers
- **Celery result backend:** Stores task completion status
- **Rate limit counters:** Query rate limiting per user
- **Cache:** Cache frequent queries for 10 minutes

---

## 7. RAG and Retrieval Pipeline

```
User question: "What did we quote the Sharma account last month?"
        ↓
[Step 1: Query understanding]
Clean the query. Detect if it needs date filtering.
("last month" → extract date range)
        ↓
[Step 2: Hybrid search]
Run in parallel:
A) Dense search: embed query → Qdrant cosine similarity → top 20 chunks
B) Sparse search: BM25 keyword search on chunk texts → top 20 chunks
Merge results, deduplicate, keep top 30 unique chunks
        ↓
[Step 3: Re-rank]
Use cross-encoder model to re-score all 30 chunks
against the original query. Keep top 5-8.
Model: cross-encoder/ms-marco-MiniLM-L-6-v2 (free, local)
        ↓
[Step 4: Context assembly]
Build context string from top chunks.
Each chunk labelled: [Source: Gmail, From: Rajesh, Date: 15 July 2026]
        ↓
[Step 5: LLM call]
Send: system prompt + context + user question to LLM.
System prompt: answer only from context, cite sources,
say "I don't have this information" if context is insufficient.
        ↓
[Step 6: Response]
Return: answer text + list of source citations + confidence
Log to audit_logs table.
```

> **Hallucination prevention — non-negotiable**
>
> The system prompt must always include: "Answer only using the context provided. If the context does not contain enough information to answer, respond with: I do not have enough information in the indexed data to answer this. Do not make up any information." Every response must include citations. This is not optional.

---

## 8. LLM Abstraction Layer

All LLM calls go through a single `BaseLLM` class. Provider is chosen at startup via `LLM_PROVIDER` environment variable. Switching providers requires zero code changes.

```python
# app/llm/base.py
class BaseLLM:
    async def complete(self, messages: list[dict]) -> str:
        raise NotImplementedError

# Implementations:
# app/llm/ollama.py     → OllamaLLM
# app/llm/groq.py       → GroqLLM
# app/llm/anthropic.py  → AnthropicLLM
# app/llm/openai.py     → OpenAILLM

# app/llm/factory.py
def get_llm() -> BaseLLM:
    provider = settings.LLM_PROVIDER
    if provider == "ollama":    return OllamaLLM(model=settings.OLLAMA_MODEL)
    if provider == "groq":      return GroqLLM(model=settings.GROQ_MODEL)
    if provider == "anthropic": return AnthropicLLM()
    if provider == "openai":    return OpenAILLM()
    raise ValueError(f"Unknown LLM provider: {provider}")
```

### LLM Options — Ranked by Recommendation

| Provider | Model | Quality | Cost | When to use |
|---|---|---|---|---|
| **Groq API** ✅ FREE | `llama-3.1-70b-versatile` | Excellent | Free: 6,000 req/day, 14,400 tokens/min | **Primary choice for testing.** Sign up at groq.com. |
| **Ollama local** ✅ FREE | `llama3.2:3b` | Decent | Completely free | Offline dev or 100% data-local clients |
| **Ollama local** ✅ FREE | `llama3.1:8b` | Good | Free. Needs 8GB RAM minimum | Better quality when machine has RAM |
| **Anthropic Claude** ⚡ OPTIONAL | `claude-sonnet-4-6` | Best | ~$3 per million input tokens | When client approves cloud LLM |

> **Data privacy note:** When using Groq or Anthropic, the query + context chunks (real company data) are sent to their servers. For internal testing this is acceptable. For client deployments where data privacy is critical, use Ollama. The architecture supports both without code changes.

---

## 9. MCP Server

An MCP (Model Context Protocol) server runs as a separate FastAPI process on port 3001. Any AI agent that speaks MCP — Claude Code, any other agent framework — can connect to it and access the context store.

### MCP Tools Exposed

| Tool name | Input | Output |
|---|---|---|
| `search_company_knowledge` | `query: string`, `top_k: int (default 5)` | List of chunks with text, source, date, URL |
| `get_document` | `document_id: string` | Full document text and metadata |
| `list_sources` | none | All connected sources with last sync time and document count |
| `get_recent_messages` | `source_type: string`, `limit: int` | Most recent messages from a source |

```bash
# Run MCP server separately
python -m app.mcp.server --port 3001

# Connect Claude Code to it:
# In ~/.claude/settings.json or mcp config:
{
  "mcpServers": {
    "context-store": {
      "url": "http://localhost:3001"
    }
  }
}
```

---

## 10. API Endpoint Design

All endpoints under `/api/v1/`. All require `Authorization: Bearer <token>` except auth endpoints.

All responses follow:
```json
{ "data": "<payload>", "error": null }
{ "data": null, "error": "Human readable message" }
```

### Auth
```
POST   /api/v1/auth/login     → {access_token, token_type}
POST   /api/v1/auth/logout
GET    /api/v1/auth/me        → {id, email, role}
```

### Connectors
```
GET    /api/v1/connectors                      → list all with status
GET    /api/v1/connectors/{type}/auth-url      → OAuth redirect URL
GET    /api/v1/connectors/{type}/callback      → OAuth callback (redirect)
DELETE /api/v1/connectors/{type}               → disconnect
POST   /api/v1/connectors/{type}/sync          → trigger manual sync
GET    /api/v1/connectors/{type}/status        → {status, last_sync, doc_count, error}

# WhatsApp only:
POST   /api/v1/webhooks/whatsapp               → receive incoming messages
GET    /api/v1/webhooks/whatsapp               → webhook verification (Meta requirement)
```

### Query
```
POST   /api/v1/query
  Body:     { "question": "string", "top_k": 5 }
  Response: { "answer": "string", "sources": [{title, url, date, snippet}], "query_id": "string" }

GET    /api/v1/query/history?limit=20          → list of past queries
```

### Documents
```
GET    /api/v1/documents?connector=gmail&limit=50&offset=0
GET    /api/v1/documents/{id}
DELETE /api/v1/documents/{id}    → remove from index
```

### Admin
```
GET    /api/v1/admin/audit-logs?limit=50
GET    /api/v1/admin/stats       → {total_docs, total_queries, connectors_count}
POST   /api/v1/admin/reindex     → trigger full re-index of all sources
```

---

## 11. Frontend UI Design

Five screens. Clean, minimal. Designed for non-technical users. No jargon. Every button says exactly what it does. Every status is shown with color and plain words.

### Screen 1 — Login (`/login`)
```
┌─────────────────────────────────┐
│           AIVAURA               │
│     Company Intelligence        │
│                                 │
│  Email address                  │
│  [ akshat@aivaura.com         ] │
│                                 │
│  Password                       │
│  [ ••••••••••••               ] │
│                                 │
│  [ Sign in →                  ] │
└─────────────────────────────────┘
```

### Screen 2 — Dashboard (`/`)
```
AIVAURA                              [Ask a question →]
────────────────────────────────────────────────────────
Good morning, Akshat.

Your knowledge sources               Last updated
────────────────────────────────────────────────────────
🟢 Gmail             1,243 emails     2 mins ago
🟢 Google Drive      89 documents     1 hour ago
🟡 Outlook           Syncing...       —
🔴 WhatsApp          Not connected    [Connect]
⚪ Google Sheets     Not connected    [Connect]

Total indexed: 1,332 items

Recent questions
────────────────────────────────────────────────────────
"What was our last quote to Sharma account?"    5 min ago
"Who is our contact at Infosys Pune?"           1 hour ago
"What are the Tata project deliverables?"       Yesterday
```

### Screen 3 — Ask (`/ask`)
```
← Back to dashboard

Ask anything about your company
────────────────────────────────────────────────────────
[ What do you want to know?                      ] [Ask]

────────────────────────────────────────────────────────
Q: What did we quote the Sharma account last month?

A: According to an email from Rajesh (15 July 2026),
   the quote sent to Sharma Industries was Rs 4,20,000
   for 14 laptops on a 12-month rental. A follow-up was
   sent on 22 July but no response was received.

   Sources used:
   📧 Email from Rajesh · 15 July 2026        [View →]
   📧 Email to sharma@industries.com · 22 Jul [View →]
```

### Screen 4 — Connectors (`/connectors`)
```
← Back to dashboard

Connect your data sources
────────────────────────────────────────────────────────
Connect the tools your team uses. We only read your
data and never modify or send anything.

[ Gmail               ]  🟢 Connected · 1,243 emails
  Last synced: 2 minutes ago          [Sync now] [Disconnect]

[ Google Drive        ]  🟢 Connected · 89 files
  Last synced: 1 hour ago             [Sync now] [Disconnect]

[ Outlook             ]  🟡 Syncing...
  Started: 3 minutes ago                         [Cancel]

[ WhatsApp Business   ]  ⚪ Not connected
  Requires WhatsApp Business account.             [Connect →]

[ Google Sheets/Excel ]  ⚪ Not connected
  Connect Sheets or upload .xlsx files.           [Connect →]
```

### Screen 5 — Admin (`/admin`)
```
← Back to dashboard

Admin Panel
────────────────────────────────────────────────────────
System Stats
  Total documents indexed:  1,332
  Total queries answered:   47
  Active connectors:        3 of 5

Recent activity log
────────────────────────────────────────────────────────
Time        User    Query
11:42 AM    Akshat  "What was the Sharma quote..."
10:15 AM    Akshat  "Who handles Wipro account..."
Yesterday   Akshat  "Tata project deliverables..."

[Load more]

Danger zone
  [ Re-index all data ]    [ Clear all indexed data ]
```

---

## 12. Complete Tech Stack

### Backend

| Package | Version | Purpose |
|---|---|---|
| `python` | 3.11 | Language. Use exactly 3.11 — some AI libraries break on 3.12. |
| `fastapi` | 0.115.x | Web framework. Async. Auto-generates API docs at /docs. |
| `uvicorn[standard]` | 0.30.x | ASGI server that runs FastAPI. |
| `pydantic` | v2 | Data validation for all API inputs and config. |
| `sqlalchemy` | 2.0.x | ORM for PostgreSQL. Async mode. |
| `alembic` | 1.13.x | Database migrations. |
| `asyncpg` | 0.29.x | Async PostgreSQL driver. Required with async SQLAlchemy. |
| `celery[redis]` | 5.4.x | Background job queue for sync tasks. |
| `redis` | 5.0.x | Redis client for Celery and caching. |
| `python-jose[cryptography]` | 3.3.x | JWT token creation and verification. |
| `passlib[bcrypt]` | 1.7.x | Password hashing. |
| `cryptography` | 43.x | Fernet encryption for OAuth tokens stored in DB. |
| `slowapi` | 0.1.x | Rate limiting middleware for FastAPI. |

### AI and RAG

| Package | Version | Purpose |
|---|---|---|
| `llama-index` | 0.11.x | RAG pipeline framework. Chunking, indexing, querying. |
| `llama-index-vector-stores-qdrant` | latest | LlamaIndex connector to Qdrant. |
| `llama-index-embeddings-ollama` | latest | nomic-embed-text via Ollama. |
| `llama-index-llms-ollama` | latest | Ollama LLM provider for LlamaIndex. |
| `llama-index-llms-groq` | latest | Groq LLM provider. |
| `llama-index-llms-anthropic` | latest | Anthropic Claude provider. |
| `qdrant-client` | 1.9.x | Qdrant vector database client. |
| `sentence-transformers` | 3.x | Cross-encoder re-ranker (ms-marco-MiniLM-L-6-v2). |
| `rank-bm25` | 0.2.x | BM25 keyword search for hybrid retrieval. |
| `openai-whisper` | latest | Transcribe WhatsApp voice notes. Runs locally. |

### Connectors

| Package | Purpose |
|---|---|
| `google-auth-oauthlib` | Google OAuth flow |
| `google-api-python-client` | Drive, Gmail, Sheets APIs |
| `msgraph-sdk` | Microsoft Graph (Outlook) |
| `httpx` | Async HTTP — WhatsApp API calls |
| `openpyxl` | Read .xlsx Excel files |
| `xlrd` | Read legacy .xls Excel files |
| `beautifulsoup4` | Strip HTML from email bodies |
| `python-docx` | Read .docx files from Drive |
| `pypdf` | Extract text from PDF files |

### MCP

| Package | Purpose |
|---|---|
| `mcp` | Official Anthropic MCP Python SDK |

### Frontend

| Package | Version | Purpose |
|---|---|---|
| `next` | 14.x App Router | React framework |
| `typescript` | 5.x | Type safety |
| `tailwindcss` | 3.x | Styling |
| `@shadcn/ui` | latest | UI component library |
| `zustand` | 4.x | State management |
| `@tanstack/react-query` | 5.x | API data fetching and caching |
| `lucide-react` | latest | Icons |
| `axios` | 1.x | HTTP client for API calls |

### Infrastructure (local dev)

| Tool | Purpose |
|---|---|
| Docker + Docker Compose | Runs PostgreSQL, Redis, Qdrant locally with one command |
| Ollama | Runs LLMs and embedding models locally |
| ngrok (free account) | HTTPS tunnel for WhatsApp webhook testing |
| Poetry | Python dependency management |

---

## 13. Third-Party Services and Costs

### Free Services — All of These

| Service | What it provides | Free tier limits | Sign up |
|---|---|---|---|
| Groq API | Llama 3.1 70B LLM | 6,000 req/day · 14,400 tokens/min | groq.com |
| Supabase | PostgreSQL hosted | 500MB storage · 2 projects | supabase.com |
| Qdrant Cloud | Vector database hosted | 1GB storage · 1M vectors | cloud.qdrant.io |
| Upstash Redis | Redis for Celery queue | 10,000 commands/day | upstash.com |
| Railway | App hosting | $5 credit/month · no CC needed | railway.app |
| Google Cloud Console | Drive, Gmail, Sheets API | Generous free quotas | console.cloud.google.com |
| Microsoft Azure App | Outlook / Graph API | Free to register | portal.azure.com |
| Meta for Developers | WhatsApp Business Cloud API | 1,000 conversations/month free | developers.facebook.com |
| ngrok | HTTPS tunnel for local dev | 1 static domain on free account | ngrok.com |
| Ollama | Local LLM runner | Unlimited — runs on your hardware | ollama.com |

### Hard Paid Requirements

| Service | Why it is required | Cost |
|---|---|---|
| **WhatsApp Business API** | After 1,000 service conversations/month, Meta charges per conversation. For testing with small message volumes: FREE. | ~$0.015 per conversation. Budget Rs 500–2,000/month for moderate production use. |

### Optional Paid Upgrades

| Service | When you need it | Cost |
|---|---|---|
| Hetzner CX22 VPS | After Railway free credit runs out | €3.79/month (~Rs 340/month) |
| Anthropic Claude API | When client approves cloud LLM | ~$3/M input tokens for Sonnet |
| Supabase Pro | If you exceed 500MB free storage | $25/month |

> **Total testing phase cost: Rs 0 to Rs 2,000/month** depending on WhatsApp volume. If you stay under 1,000 WhatsApp conversations and under Railway's free credit, the entire MVP testing phase costs nothing.

---

## 14. Security and Privacy Standards

### Authentication
- JWT tokens with 30-minute expiry for access tokens
- Refresh token pattern — 7-day refresh tokens in httponly cookies only
- Passwords hashed with bcrypt (cost factor 12)
- No plaintext passwords stored or logged anywhere

### OAuth Token Storage
- All OAuth tokens (Google, Microsoft) encrypted with Fernet before DB storage
- Encryption key in environment variable — never in code or database
- Tokens refreshed automatically when approaching expiry

### API Security
- CORS configured to allow only the frontend origin — not wildcard `*`
- Rate limiting: 60 queries per hour per user on `/api/v1/query`
- Input length limit: query max 2,000 characters
- All database queries through SQLAlchemy ORM — no raw SQL, no injection risk
- Pydantic validation on all request bodies

### Data Handling
- No company data sent to any third party unless `LLM_PROVIDER` is set to a cloud provider
- All data stays in infrastructure you control
- Audit log of every query — who asked what, when, what sources were used
- No logging of full document content in application logs (log metadata only)

### Secrets Management
- All secrets in `.env` file — never committed to git
- `.env` in `.gitignore` from day one
- `.env.example` committed with all keys but empty values
- On Railway: set via Railway environment variables dashboard

---

## 15. Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | **Required** | PostgreSQL connection string. Example: `postgresql+asyncpg://user:pass@host/dbname` |
| `REDIS_URL` | **Required** | Redis connection string. Example: `redis://localhost:6379` |
| `QDRANT_URL` | **Required** | Qdrant URL. Local: `http://localhost:6333`. Cloud: from Qdrant dashboard. |
| `QDRANT_API_KEY` | Optional | Only for Qdrant Cloud. Leave empty for local. |
| `SECRET_KEY` | **Required** | Random 64-char string for JWT signing. Generate: `openssl rand -hex 32` |
| `ENCRYPTION_KEY` | **Required** | Fernet key for OAuth token encryption. Generate: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `LLM_PROVIDER` | **Required** | One of: `ollama`, `groq`, `anthropic`, `openai`. Default: `groq` |
| `OLLAMA_BASE_URL` | Optional | Only if LLM_PROVIDER=ollama. Default: `http://localhost:11434` |
| `OLLAMA_MODEL` | Optional | Only if LLM_PROVIDER=ollama. Default: `llama3.2:3b` |
| `GROQ_API_KEY` | Optional | Required if LLM_PROVIDER=groq. From console.groq.com |
| `GROQ_MODEL` | Optional | Default: `llama-3.1-70b-versatile` |
| `ANTHROPIC_API_KEY` | Optional | Required only if LLM_PROVIDER=anthropic |
| `GOOGLE_CLIENT_ID` | **Required** | From Google Cloud Console → OAuth 2.0 credentials |
| `GOOGLE_CLIENT_SECRET` | **Required** | From Google Cloud Console → OAuth 2.0 credentials |
| `MICROSOFT_CLIENT_ID` | **Required** | From Azure App Registration |
| `MICROSOFT_CLIENT_SECRET` | **Required** | From Azure App Registration |
| `WHATSAPP_VERIFY_TOKEN` | **Required** | Any random string. Used to verify Meta webhook. |
| `WHATSAPP_ACCESS_TOKEN` | **Required** | Permanent access token from Meta WhatsApp Cloud API |
| `WHATSAPP_PHONE_NUMBER_ID` | **Required** | From Meta WhatsApp Cloud API dashboard |
| `FRONTEND_URL` | **Required** | Frontend origin for CORS. Local: `http://localhost:3000` |
| `BACKEND_URL` | **Required** | Backend public URL for OAuth callbacks. Local: `http://localhost:8000` |

---

## 16. Project File Structure

```
context-store/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app, middleware setup
│   │   ├── config.py                  # Pydantic settings, reads env vars
│   │   ├── database.py                # Async SQLAlchemy engine
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── connector.py
│   │   │   ├── document.py
│   │   │   ├── chunk.py
│   │   │   ├── audit_log.py
│   │   │   └── sync_state.py
│   │   ├── api/
│   │   │   ├── auth.py                # Login, logout, /me
│   │   │   ├── connectors.py          # Connect/disconnect/sync endpoints
│   │   │   ├── query.py               # Q&A endpoint
│   │   │   ├── documents.py           # List and delete indexed docs
│   │   │   ├── admin.py               # Audit logs, stats
│   │   │   └── webhooks.py            # WhatsApp webhook receiver
│   │   ├── connectors/
│   │   │   ├── base.py                # BaseConnector abstract class
│   │   │   ├── google_drive.py
│   │   │   ├── gmail.py
│   │   │   ├── outlook.py
│   │   │   ├── whatsapp.py
│   │   │   └── sheets.py              # Google Sheets + Excel
│   │   ├── processing/
│   │   │   ├── pipeline.py            # Orchestrates clean→chunk→embed→store
│   │   │   ├── cleaner.py             # HTML stripping, whitespace
│   │   │   ├── chunker.py             # LlamaIndex chunking strategy
│   │   │   ├── embedder.py            # nomic-embed-text via Ollama
│   │   │   └── transcriber.py         # Whisper for WhatsApp voice notes
│   │   ├── retrieval/
│   │   │   ├── hybrid_search.py       # Dense + BM25 merge
│   │   │   ├── reranker.py            # Cross-encoder re-ranking
│   │   │   └── query_engine.py        # Orchestrates search→LLM→response
│   │   ├── llm/
│   │   │   ├── base.py                # BaseLLM abstract class
│   │   │   ├── factory.py             # get_llm() function
│   │   │   ├── ollama.py
│   │   │   ├── groq.py
│   │   │   └── anthropic.py
│   │   ├── mcp/
│   │   │   └── server.py              # MCP server (run separately)
│   │   └── workers/
│   │       ├── celery_app.py          # Celery app setup
│   │       └── sync_tasks.py          # Scheduled sync tasks per connector
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/                  # Migration files
│   ├── tests/
│   │   ├── test_connectors.py
│   │   ├── test_retrieval.py
│   │   └── test_api.py
│   ├── pyproject.toml                 # Poetry deps
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx               # Dashboard
│   │   │   ├── ask/page.tsx           # Q&A chat
│   │   │   ├── connectors/page.tsx    # Manage sources
│   │   │   ├── admin/page.tsx         # Audit logs
│   │   │   └── login/page.tsx
│   │   ├── components/
│   │   │   ├── ui/                    # shadcn components
│   │   │   ├── ConnectorCard.tsx
│   │   │   ├── QueryBox.tsx
│   │   │   ├── AnswerCard.tsx         # Shows answer + citations
│   │   │   ├── SourceBadge.tsx        # "[Gmail · Rajesh · 15 Jul]"
│   │   │   └── StatusBadge.tsx        # Green/amber/red status dots
│   │   ├── lib/
│   │   │   ├── api.ts                 # axios instance + API functions
│   │   │   └── store.ts               # Zustand auth store
│   │   └── types/
│   │       └── index.ts               # TypeScript types
│   ├── package.json
│   ├── tailwind.config.ts
│   └── Dockerfile
├── docker-compose.yml                 # Runs postgres, redis, qdrant locally
├── CLAUDE.md                          # Claude Code instructions
├── .env.example
└── README.md
```

### docker-compose.yml (local dev)

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: contextstore
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports: ["5432:5432"]
    volumes: ["postgres_data:/var/lib/postgresql/data"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  qdrant:
    image: qdrant/qdrant
    ports: ["6333:6333"]
    volumes: ["qdrant_data:/qdrant/storage"]

volumes:
  postgres_data:
  qdrant_data:
```

---

## 17. Development Sequence

Build in this exact order. Each phase must work before the next starts. Do not skip ahead.

### Phase 1 — Project Setup and Skeleton `Week 1`
- Create repo. Set up Poetry for backend, npm for frontend.
- Write `docker-compose.yml`. Run `docker compose up`. Confirm Postgres, Redis, Qdrant all start.
- FastAPI skeleton: `main.py`, `config.py`, `database.py`. One health check endpoint: `GET /health → {"status": "ok"}`
- Next.js 14 setup with Tailwind and shadcn/ui. One blank page.
- Write `.env.example`. Write `CLAUDE.md`.

### Phase 2 — Database and Auth `Week 1–2`
- Write all SQLAlchemy models. Run first Alembic migration.
- Build auth endpoints: login, logout, /me. JWT tokens working.
- Frontend: login page. Store token in memory (not localStorage). Auth middleware for protected routes.
- Test: can log in, get token, make authenticated request.

### Phase 3 — LLM Layer and Basic Q&A (no real data yet) `Week 2`
- Pull `nomic-embed-text` and `llama3.2:3b` via Ollama locally.
- Build `BaseLLM`, `OllamaLLM`, `GroqLLM`. Test both work.
- Build `embedder.py`. Test embedding a sample sentence returns a 768-dim vector.
- Create Qdrant collection. Test inserting and searching 5 fake chunks.
- Build `query_engine.py` skeleton. Test end-to-end with fake data.

### Phase 4 — Processing Pipeline `Week 2–3`
- Build `cleaner.py`, `chunker.py`. Test on a sample email and PDF.
- Set up Celery. Build `sync_tasks.py` skeleton. Test a task runs and logs.
- Build `pipeline.py` that takes a raw document, runs all steps, stores in Qdrant + Postgres.
- Test: manually trigger pipeline with a hardcoded text. Confirm it appears in Qdrant.

### Phase 5 — Google Drive Connector `Week 3`
- Set up Google Cloud project. Enable Drive and Gmail APIs. Create OAuth credentials.
- Build `google_drive.py` connector. OAuth flow working.
- Test: connect Drive, fetch first 10 files, run through pipeline, query them.
- Build connector status and manual sync endpoints.

### Phase 6 — Gmail Connector `Week 3–4`
- Build `gmail.py`. Reuse Google OAuth tokens from Drive (same project).
- Test: fetch last 50 emails, process, query "who sent me an email about pricing?"
- Add to Celery schedule: sync Gmail every 30 minutes.

### Phase 7 — Frontend Dashboard and Q&A `Week 4–5`
- Build Dashboard page. Show connector status cards with real data from API.
- Build Ask page. Text input, submit query, show answer + citations.
- Build `AnswerCard` and `SourceBadge` components. Sources must be visually prominent.
- **Internal testing begins here. Use it daily. Note what breaks.**

### Phase 8 — Sheets, Outlook, WhatsApp `Week 5–7`
- **Week 5:** Google Sheets connector. Excel file upload endpoint.
- **Week 6:** Outlook connector via Microsoft Graph. Azure app registration.
- **Week 7:** WhatsApp connector. Set up ngrok, configure Meta webhook, receive and index messages. Whisper for voice notes.

### Phase 9 — Hybrid Search, Connectors UI, Admin `Week 7–8`
- Add BM25 keyword search alongside vector search. Merge results.
- Add cross-encoder re-ranking. Test answer quality improves.
- Build Connectors page UI (connect, disconnect, sync, status).
- Build Admin page (audit logs, stats).

### Phase 10 — MCP Server and Railway Deploy `Week 8–9`
- Build MCP server (`app/mcp/server.py`). Expose 4 tools.
- Test: connect Claude Code to MCP server. Ask it a question requiring company context.
- Deploy to Railway. Set all environment variables. Test everything on staging.
- Security review: all env vars set, no secrets in code, CORS strict, rate limits work.

---

## 18. Claude Code Model Recommendation

**Use `claude-sonnet-4-6` as your default.** It is fast and capable enough for all routine coding — writing endpoints, building components, debugging, writing tests.

Switch to `claude-opus-4-6` when:
- Making major architectural decisions
- Sonnet is going in circles on a hard bug
- Designing the retrieval pipeline logic

### Configure in Claude Code

```bash
# When starting Claude Code
claude --model claude-sonnet-4-6
```

Or set as default in `~/.claude/settings.json`:
```json
{
  "model": "claude-sonnet-4-6"
}
```

### How to work with Claude Code effectively

- Always start Claude Code sessions from the project root — it reads `CLAUDE.md` automatically
- Give Claude one task at a time: "Build the Gmail connector" not "Build everything"
- Run tests after each phase before moving to the next
- Update the "what to build next" section in `CLAUDE.md` at the end of each session
- If Claude writes something you don't understand, ask it to explain before accepting

---

*Aivaura · Context Store MVP PRD v1.0 · August 2026 · Confidential*
