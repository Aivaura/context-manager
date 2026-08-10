# Context Store — Complete Setup Guide (No Docker)

**Aivaura · v1.0 · For the internal team**

---

## What You're Setting Up

| Service | What it does | Where to get it | Cost |
|---|---|---|---|
| Supabase | PostgreSQL database | supabase.com | FREE |
| Upstash | Redis (Celery + cache) | upstash.com | FREE |
| Qdrant Cloud | Vector database | cloud.qdrant.io | FREE |
| Groq API | LLM (Llama 3.1 70B) | console.groq.com | FREE |
| Ollama | Local embeddings | ollama.com | FREE |
| Google Cloud | Drive + Gmail + Sheets OAuth | console.cloud.google.com | FREE |
| Azure | Outlook OAuth | portal.azure.com | FREE |
| Meta | WhatsApp Cloud API | developers.facebook.com | FREE (first 1K msg/month) |

**Total cost for testing: ₹0**

---

## Step 1 — Prerequisites

Install these on your machine:

```bash
# Python 3.11 (already installed on server)
python3 --version   # must show 3.11.x

# Poetry (Python package manager)
curl -sSL https://install.python-poetry.org | python3 -

# Node.js 18+
node --version   # must show v18 or higher
npm --version

# Ollama (local AI model runner)
# Go to: https://ollama.com/download
# Install for your OS, then:
ollama pull nomic-embed-text   # 274MB — the embedding model
```

---

## Step 2 — Supabase (PostgreSQL)

1. Go to **https://supabase.com** → Sign up for free
2. Click **New project** → Choose a name, set a strong DB password, pick a region close to you
3. Wait 2 minutes for project to provision
4. Go to: **Project Settings → Database → Connection string**
5. Copy the **URI** format. It looks like:
   ```
   postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
   ```
6. Add `+asyncpg` after `postgresql` to make it async-compatible:
   ```
   postgresql+asyncpg://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
   ```
7. Save this as your `DATABASE_URL`

---

## Step 3 — Upstash Redis

1. Go to **https://upstash.com** → Sign up for free
2. Click **Create Database** → Name it `context-store`, pick closest region
3. After creation, click the database → **Connect** tab
4. Copy the **Redis URL** (starts with `rediss://`)
   ```
   rediss://default:[PASSWORD]@[HOST]:6379
   ```
5. Save this as your `REDIS_URL`

---

## Step 4 — Qdrant Cloud

1. Go to **https://cloud.qdrant.io** → Sign up for free
2. Click **Create Cluster** → Name it `context-store`, pick **Free tier**, pick a region
3. After creation, click your cluster → **API Keys** → Create an API key
4. Copy your:
   - **Cluster URL** (e.g., `https://abc123.us-east4-0.gcp.cloud.qdrant.io`)
   - **API Key** (keep this secret)
5. Save these as `QDRANT_URL` and `QDRANT_API_KEY`

---

## Step 5 — Groq API (Free LLM)

1. Go to **https://console.groq.com** → Sign up with Google
2. Click **API Keys** → **Create API Key** → Name it `context-store`
3. Copy the key (starts with `gsk_...`)
4. Save as `GROQ_API_KEY`

**Free tier**: 6,000 requests/day, 14,400 tokens/minute — more than enough for testing.

---

## Step 6 — Generate Security Keys

Run these commands in your terminal:

```bash
# SECRET_KEY: for JWT signing
openssl rand -hex 32
# Example output: a3f8d2e1c4b5...  (save this)

# ENCRYPTION_KEY: for encrypting OAuth tokens in DB
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Example output: dGhpcyBpcyBhIG...  (save this)
```

---

## Step 7 — Google OAuth (Drive + Gmail + Sheets)

**One Google Cloud project covers all three Google connectors.**

1. Go to **https://console.cloud.google.com** → Sign in
2. Click the project dropdown → **New Project** → Name: `context-store`
3. Select your new project

### Enable APIs
4. Go to **APIs & Services → Library**
5. Search and enable each of these (one at a time, click Enable):
   - Google Drive API
   - Gmail API
   - Google Sheets API

### Create OAuth Credentials
6. Go to **APIs & Services → Credentials → Create Credentials → OAuth client ID**
7. If prompted to configure consent screen:
   - User Type: **External** → Create
   - App name: `Context Store`
   - User support email: your email
   - Developer contact: your email
   - Save → Continue → Continue → Back to Dashboard
8. Back to Create OAuth client ID:
   - Application type: **Web application**
   - Name: `context-store-web`
   - **Authorized redirect URIs** — add ALL THREE:
     ```
     http://localhost:8000/api/v1/connectors/google_drive/callback
     http://localhost:8000/api/v1/connectors/gmail/callback
     http://localhost:8000/api/v1/connectors/sheets/callback
     ```
     (If deploying to Railway, also add your Railway URL versions)
9. Click **Create** → Copy:
   - `Client ID` → save as `GOOGLE_CLIENT_ID`
   - `Client Secret` → save as `GOOGLE_CLIENT_SECRET`

### Add Test Users (until you verify the app with Google)
10. Go to **APIs & Services → OAuth consent screen → Test users** → Add your Gmail address

---

## Step 8 — Microsoft Azure (Outlook)

1. Go to **https://portal.azure.com** → Sign in with Microsoft account
2. Search for **App registrations** → **New registration**
3. Fill in:
   - Name: `context-store`
   - Supported account types: **Accounts in any organizational directory and personal Microsoft accounts**
   - Redirect URI: **Web** → `http://localhost:8000/api/v1/connectors/outlook/callback`
4. Click **Register**
5. On the app overview page, copy:
   - **Application (client) ID** → save as `MICROSOFT_CLIENT_ID`
6. Go to **Certificates & secrets → New client secret** → Description: `context-store` → Add
7. Copy the **Value** (NOT the ID) → save as `MICROSOFT_CLIENT_SECRET`

   ⚠️ **Copy it NOW** — it's only shown once.

8. Go to **API permissions → Add a permission → Microsoft Graph → Delegated**
   - Add: `Mail.Read`
   - Add: `offline_access`
9. Click **Grant admin consent** if available

---

## Step 9 — WhatsApp Business API

1. Go to **https://developers.facebook.com** → Log in with Facebook
2. Click **My Apps → Create App → Business → Continue**
3. App name: `context-store` → Create App
4. From the dashboard, click **WhatsApp → Set up**
5. Under **Temporary access token**, copy the token → save as `WHATSAPP_ACCESS_TOKEN`
6. Copy the **Phone Number ID** → save as `WHATSAPP_PHONE_NUMBER_ID`
7. Choose any string as your `WHATSAPP_VERIFY_TOKEN` (e.g., `context-store-webhook-2026`)

### Setting up the webhook (for local testing with ngrok):
```bash
# Install ngrok (free account at ngrok.com)
ngrok http 8000

# You'll get a URL like: https://abc123.ngrok-free.app
# Go to WhatsApp → Configuration → Webhook
# Callback URL: https://abc123.ngrok-free.app/api/v1/webhooks/whatsapp
# Verify token: (your WHATSAPP_VERIFY_TOKEN value)
# Subscribe to: messages
```

---

## Step 10 — Configure Environment Variables

```bash
cd /path/to/context-manager/backend
cp .env.example .env
```

Edit `.env` with all the values you collected:

```bash
DATABASE_URL=postgresql+asyncpg://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres
REDIS_URL=rediss://default:[PASSWORD]@[HOST].upstash.io:6379
QDRANT_URL=https://[CLUSTER].cloud.qdrant.io
QDRANT_API_KEY=[YOUR_QDRANT_KEY]
SECRET_KEY=[YOUR_64_CHAR_HEX]
ENCRYPTION_KEY=[YOUR_FERNET_KEY]
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.1-70b-versatile
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBED_MODEL=nomic-embed-text
GOOGLE_CLIENT_ID=[YOUR_GOOGLE_CLIENT_ID]
GOOGLE_CLIENT_SECRET=[YOUR_GOOGLE_CLIENT_SECRET]
MICROSOFT_CLIENT_ID=[YOUR_AZURE_CLIENT_ID]
MICROSOFT_CLIENT_SECRET=[YOUR_AZURE_CLIENT_SECRET]
WHATSAPP_VERIFY_TOKEN=context-store-webhook-2026
WHATSAPP_ACCESS_TOKEN=[YOUR_META_TOKEN]
WHATSAPP_PHONE_NUMBER_ID=[YOUR_PHONE_NUMBER_ID]
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
```

---

## Step 11 — Install Backend Dependencies

```bash
cd backend
poetry install

# Install Whisper separately (large, optional — for WhatsApp voice notes)
# poetry install --extras whisper
```

---

## Step 12 — Install Frontend Dependencies

```bash
cd frontend
npm install
cp .env.local.example .env.local
# .env.local already has: NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Step 13 — Run the Application

You need **5 terminal windows**:

### Terminal 1: Ollama (embeddings)
```bash
# Ollama runs as a service — if you installed it, it may already be running
# Check: curl http://localhost:11434/api/tags
# If not running: ollama serve
```

### Terminal 2: Backend API
```bash
cd backend
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

On first start, the API will:
- Connect to Supabase and create all tables
- Connect to Qdrant and create the `company_knowledge` collection
- Create default admin user: `admin@aivaura.com` / `changeme123`

### Terminal 3: Celery Worker (background sync jobs)
```bash
cd backend
poetry run celery -A app.workers.celery_app worker --loglevel=info -P solo
```

### Terminal 4: Celery Beat (scheduler)
```bash
cd backend
poetry run celery -A app.workers.celery_app beat --loglevel=info
```

### Terminal 5: Frontend
```bash
cd frontend
npm run dev
```

### Optional Terminal 6: MCP Server
```bash
cd backend
poetry run python -m app.mcp.server
# Runs on http://localhost:3001
```

---

## Step 14 — First Login

Open **http://localhost:3000**

Login with:
- Email: `admin@aivaura.com`
- Password: `changeme123`

> **Change this password immediately** after first login — set a new one via the API:
> ```bash
> curl -X POST http://localhost:8000/api/v1/auth/login \
>   -H "Content-Type: application/json" \
>   -d '{"email":"admin@aivaura.com","password":"changeme123"}'
> ```

---

## Step 15 — Connect Your First Data Source

1. Go to **http://localhost:3000/connectors**
2. Click **Connect →** next to Gmail
3. You'll be redirected to Google — sign in and authorize
4. You'll be sent back to the connectors page with "Gmail connected"
5. The initial sync starts automatically (runs in Celery worker)

---

## Step 16 — Test the Q&A

1. Wait ~5 minutes for initial Gmail sync to complete
2. Go to **http://localhost:3000/ask**
3. Type a question about your emails: "What emails did I receive this week about [topic]?"
4. You should get an answer with source citations

---

## Verify Everything is Working

```bash
# Health check
curl http://localhost:8000/health
# Expected: {"status":"ok","service":"context-store"}

# Qdrant status
curl http://localhost:8000/api/v1/admin/stats \
  -H "Authorization: Bearer [YOUR_TOKEN]"

# Ollama embedding test
curl http://localhost:11434/api/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model":"nomic-embed-text","prompt":"test"}'
# Expected: {"embedding":[0.01234,...]} (768-dimensional vector)
```

---

## Deploying to Railway (Optional)

1. Install Railway CLI: `npm install -g @railway/cli`
2. `railway login`
3. `cd backend && railway init`
4. Set all environment variables in Railway dashboard
5. Change `BACKEND_URL` to your Railway URL
6. Change `FRONTEND_URL` to your Railway frontend URL
7. Update Google OAuth redirect URIs and Azure redirect URI with Railway URLs
8. `railway up`

---

## MCP Server — Claude Code Integration

After the MCP server is running (`python -m app.mcp.server`):

Add to your `~/.claude/settings.json`:
```json
{
  "mcpServers": {
    "context-store": {
      "url": "http://localhost:3001"
    }
  }
}
```

Claude Code can now use:
- `search_company_knowledge("your question")` — semantic + keyword search
- `get_document("doc-id")` — retrieve full document
- `list_sources()` — list all connected sources
- `get_recent_messages("gmail", 20)` — recent messages from a source

---

## Common Issues

### "Connection refused" on API startup
→ Check if Supabase URL is correct and password is URL-encoded (special chars in password need escaping)

### "Embedding model not found"
→ Run `ollama pull nomic-embed-text` and make sure Ollama is running

### "Invalid state" on OAuth callback
→ Redis is not reachable — check REDIS_URL and that Upstash Redis is active

### Celery worker shows "connection refused"
→ Check REDIS_URL — it should start with `rediss://` (with SSL) for Upstash

### BM25 search returns empty results
→ Normal on first start — BM25 index builds after first documents are indexed. Ask a question after indexing some data.

### Gmail sync fails with "Token has been expired"
→ Delete and reconnect the Gmail connector — the refresh token will be re-issued

---

## Security Checklist Before Production

- [ ] Change `admin@aivaura.com` password from `changeme123`
- [ ] Set `SECRET_KEY` to a proper 64-char random hex (not the default)
- [ ] Set `ENCRYPTION_KEY` to a proper Fernet key (not the default)
- [ ] Set `FRONTEND_URL` to your actual domain (not wildcard)
- [ ] Set `BACKEND_URL` to your actual domain
- [ ] Update Google OAuth redirect URIs to production URLs
- [ ] Update Azure redirect URI to production URL
- [ ] Enable HTTPS (Railway does this automatically)
- [ ] Consider setting `LLM_PROVIDER=ollama` if data must stay local

---

*Aivaura · Context Store MVP · 2026*
