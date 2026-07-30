# RAS — Document Intelligence System

A multi-user, multilingual Retrieval-Augmented Q&A system built with Streamlit:
upload documents, ask questions one-at-a-time (chat mode) or in bulk (batch
Q&A mode), get cited, source-backed answers with a "view the original PDF
page" option, confidence scores per source, and a regenerate-with-a-different-model
button if an answer isn't good enough.

This README is deliberately exhaustive — it lists **every** environment
variable / secret the code actually reads (traced from `config/settings.py`,
not guessed), what breaks if each one is missing, and every system-level
dependency beyond `pip install`.

---

## 1. Requirements

- **Python 3.11 or 3.12** (developed/tested against 3.12). Python 3.13 is
  untested — several of the pinned ML libraries (torch, sentence-transformers)
  lag behind new Python releases by a few months.
- **~3-4 GB free disk** for the ML models `pip install` will pull down
  (torch, sentence-transformers, easyocr all bundle or download model weights).
- A machine with at least **4 GB RAM** free for the app process itself — more
  if several people will have active chats open at once (see `RAS_MAX_HOT_USERS`
  below).

### System-level dependencies (NOT installed by `pip`)

| Dependency | Needed for | Install |
|---|---|---|
| **Tesseract OCR binary** | `pytesseract` (one of the 3 selectable OCR engines) | Debian/Ubuntu: `sudo apt install tesseract-ocr tesseract-ocr-hin tesseract-ocr-tel` (the Hindi/Telugu language packs are separate packages) · macOS: `brew install tesseract tesseract-lang` |
| **Ghostscript** | Only if you enable the optional `camelot-py` table-extraction fallback | Debian/Ubuntu: `sudo apt install ghostscript` |

EasyOCR (the **default** OCR engine) and PaddleOCR do **not** need a system
binary — they're pure Python + downloaded model weights.

---

## 2. Install

```bash
git clone <your-repo-url>
cd ras_project
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

The first `pip install` will take a while — torch and sentence-transformers
are large. Model weights themselves (the embedding model, EasyOCR's
detector/recognizer, the reranker) download on **first use**, not at
`pip install` time — the first document you process will be slower than
every one after it while those download and get cached.

---

## 3. Configure secrets — `.streamlit/secrets.toml`

Streamlit reads secrets from `.streamlit/secrets.toml` in the project root
(this file should **never** be committed to git — add it to `.gitignore`).
Create it from this template:

```toml
# ── LLM provider keys — at least ONE of these is required ──────────────────
# The app tries providers in a fallback chain per request; you don't need
# all four, but the app can't answer any question with zero of them set.
GROQ_API_KEY       = ""   # https://console.groq.com/keys — free tier available
GOOGLE_API_KEY     = ""   # https://aistudio.google.com/apikey — used for Gemini
                          #   LLM answers AND "Gemini text-embedding-004" if selected
OPENROUTER_API_KEY = ""   # https://openrouter.ai/keys
OPENAI_API_KEY     = ""   # https://platform.openai.com/api-keys — also used if
                          #   you select "OpenAI text-embedding-3-small"

# ── Optional cloud embeddings / search — only needed if selected in the UI ─
JINA_API_KEY   = ""   # https://jina.ai/reader — needed for "Jina embeddings-v3"
                       #   AND for reading URLs into the knowledge base
COHERE_API_KEY = ""   # https://dashboard.cohere.com/api-keys — needed for
                       #   "Cohere Rerank" or "Cohere Embed" if selected
SERP_API_KEY   = ""   # https://serpapi.com — needed ONLY if you turn on the
                       #   "real-time web search" setting

# ── Admin dashboard login (separate from normal user accounts) ─────────────
# The admin dashboard (append ?admin=1 to the app's URL) refuses to start
# at all while RAS_ADMIN_CODE is left at its placeholder value — you MUST
# set a real value here before it's reachable.
RAS_ADMIN_USERNAME = "admin"
RAS_ADMIN_CODE     = "change-this-to-something-real"

# ── Optional operational tuning (sensible defaults if omitted) ─────────────
# RAS_MAX_HOT_USERS       = "8"   # concurrent chat sessions kept warm in RAM
# RAS_MAX_UPLOADS_PER_DAY = "5"   # per-user upload cap per rolling 24h
```

### What breaks without each key

| Key | If missing |
|---|---|
| `GROQ_API_KEY`, `GOOGLE_API_KEY`, `OPENROUTER_API_KEY`, `OPENAI_API_KEY` | The app tries each provider in turn and falls back on failure — but if **all four** are unset, every question will fail with "No LLM available". You need at least one, and normal users will want to pick their provider from the dropdown in Agent Settings, so setting more than one is more robust. |
| `GOOGLE_API_KEY` specifically | Also required if a user selects "Gemini text-embedding-004" as the embedding model (separate from it being an LLM key) |
| `OPENAI_API_KEY` | Also required if a user selects "OpenAI text-embedding-3-small" as the embedding model |
| `JINA_API_KEY` | "Jina embeddings-v3" embedding model returns all-zero vectors (silently broken retrieval, logged as an error) instead of erroring loudly. Also needed for the "read a URL into the knowledge base" feature. |
| `COHERE_API_KEY` | "Cohere Rerank" / "Cohere Embed" options fail with a logged error and fall back to returning unranked/zero results |
| `SERP_API_KEY` | The "real-time web search" toggle in settings does nothing (search calls fail silently, logged) |
| `RAS_ADMIN_USERNAME` / `RAS_ADMIN_CODE` | Admin dashboard **will not start** while `RAS_ADMIN_CODE` is the placeholder `admin-changeme` — this is intentional (a deliberate check in `app.py`), not a bug |

None of the per-user document/chat data depends on any of these keys —
uploading, chunking, and local embedding (the default, `all-MiniLM-L6-v2`,
via `sentence-transformers`) all work with **zero keys set**. Only asking a
question (needs an LLM key) and any cloud-provider embedding/rerank choice
need keys.

You can also set every one of these as real environment variables instead
of `secrets.toml` — `config/settings.py` checks `st.secrets` first, then
falls back to `os.getenv(...)`. That's the path you'll use when hosting
(see §6) rather than shipping a secrets file to a server.

---

## 4. Run it

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`. Append `?admin=1` to the URL for the admin
dashboard (separate login — see above).

`.streamlit/config.toml` already sets a 50 MB per-file upload cap and hides
Streamlit's own "Deploy" button; you don't need to touch it for local use.

---

## 5. Where your data actually lives

- **`data/`** — real user data: accounts, documents, chunks+embeddings, chat
  history. This is **not** cache — losing it loses real work. Back it up /
  put it on persistent storage when you deploy.
- **`cache/`** — safe to delete anytime; it's the content-addressed
  chunking/embedding cache plus downloaded model weights, and will just
  regenerate (slowly, the first time) if wiped.
- **`generated_outputs/`** — exported PDF/DOCX/TXT/JSON batch results.
- **`temp/`** — scratch space during document processing, safe to delete
  between runs.

---

## 6. Hosting on Hostinger

**Important up front:** Hostinger's **shared hosting** and **email
hosting** plans do not run arbitrary Python web servers (they're built for
PHP/WordPress + POP/IMAP mail, not long-running Python processes on a
custom port) — you can't put this app on a plain shared-hosting or
email-hosting plan. You need a **Hostinger VPS** plan (KVM 1/2/4/8, any
tier), which gives you a real Linux server with root SSH access. If you
only have a shared-hosting/email plan today, that's the first thing to
upgrade — everything below assumes VPS.

If your domain's mail (MX records) is already on Hostinger and you want the
app on a subdomain like `docs.yourdomain.com`, that's fine — mail (MX) and
this app (A record on a subdomain, pointed at your VPS) are independent DNS
records and won't conflict.

### Step-by-step (Ubuntu VPS)

**1. Point DNS at the VPS.** In Hostinger's DNS zone editor for your domain,
add an **A record**: `docs` (or whatever subdomain) → your VPS's IP address.

**2. SSH in and install Python + system deps:**
```bash
ssh root@your-vps-ip
apt update && apt install -y python3.12 python3.12-venv python3-pip \
    tesseract-ocr tesseract-ocr-hin tesseract-ocr-tel nginx git
```

**3. Get the code onto the server** (upload the zip via `scp`, or `git clone`
if it's in a repo), then set up the venv same as §2:
```bash
cd /opt
git clone <your-repo-url> ras_project   # or scp+unzip
cd ras_project
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**4. Create `.streamlit/secrets.toml`** on the server with real values (§3)
— or better for a server, set them as systemd environment variables instead
(step 5) so nothing sensitive sits in a file that might get committed by
accident.

**5. Run it as a systemd service** so it survives reboots and crashes:

Create `/etc/systemd/system/ras.service`:
```ini
[Unit]
Description=RAS Streamlit app
After=network.target

[Service]
User=root
WorkingDirectory=/opt/ras_project
Environment="GROQ_API_KEY=..."
Environment="GOOGLE_API_KEY=..."
Environment="RAS_ADMIN_USERNAME=admin"
Environment="RAS_ADMIN_CODE=..."
ExecStart=/opt/ras_project/venv/bin/streamlit run app.py \
    --server.port 8501 --server.address 127.0.0.1 --server.headless true
Restart=always

[Install]
WantedBy=multi-user.target
```
(Add every `Environment=` line you need from the table in §3. Skip
`.streamlit/secrets.toml` entirely on the server if you go this route —
`os.getenv()` picks these up directly.)

```bash
systemctl daemon-reload
systemctl enable --now ras
systemctl status ras          # should show "active (running)"
```

**6. Put Nginx in front of it** so it's on port 80/443 with a real domain
instead of `:8501`, and so you can add HTTPS. Create
`/etc/nginx/sites-available/ras`:
```nginx
server {
    listen 80;
    server_name docs.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";       # required — Streamlit uses WebSockets
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 86400;                     # long-lived WebSocket connections
    }
}
```
```bash
ln -s /etc/nginx/sites-available/ras /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

**7. Add HTTPS with Certbot (free, Let's Encrypt):**
```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d docs.yourdomain.com
```
Certbot edits the Nginx config to add the SSL block and sets up
auto-renewal. Your app is now at `https://docs.yourdomain.com`.

**8. Open the firewall** (if Hostinger's VPS firewall or `ufw` is active):
```bash
ufw allow 22    # SSH
ufw allow 80    # HTTP
ufw allow 443   # HTTPS
ufw enable
```

### After that

- Redeploying code changes: `git pull` (or re-upload) → `systemctl restart ras`.
- Logs: `journalctl -u ras -f`.
- Back up `/opt/ras_project/data/` regularly — it's the only thing on the
  server that isn't reproducible from the git repo (see §5).

### Alternative: Docker

If you'd rather not manage a systemd unit by hand, the same VPS supports
Docker (`apt install docker.io`), and you can containerize with a
`Dockerfile` that does `FROM python:3.12-slim`, installs the system deps
from §1, `pip install -r requirements.txt`, and `CMD ["streamlit", "run",
"app.py", "--server.port=8501", "--server.address=0.0.0.0"]` — then run
that container behind the same Nginx + Certbot setup in steps 6-7. Ask if
you'd like an actual `Dockerfile` written for this project.

---

## 7. Known compatibility notes

- **PaddleOCR vs numpy** — the code calls PaddleOCR with its old (2.x)
  constructor signature (`use_angle_cls`, `show_log`), so it must stay on
  `paddleocr` 2.x, not 3.x (a breaking API rewrite). `paddlepaddle` 2.6.2
  (the version pin compatible with that) also caps `numpy<2.0`, which
  conflicts with the `numpy==2.5.1` pinned for everything else. PaddleOCR
  is optional (EasyOCR is the default engine) — see the comment block at
  the bottom of `requirements.txt` for how to install it safely in a
  separate environment if you need it.
- **`embeddings/openai_embeddings.py` was fixed** — this file previously
  contained a stray copy of `config/prompts.py`'s text instead of any
  embedding code, meaning the "OpenAI text-embedding-3-small", "Gemini
  text-embedding-004", and "Cohere Embed" options in the embedding-model
  dropdown would have crashed with `ImportError` the moment they were
  selected. It's been rebuilt with the three classes
  (`OpenAIEmbedder`/`GeminiEmbedder`/`CohereEmbedder`) that
  `embeddings/embedding_factory.py` expects.

---

## 8. Folder structure

```
app.py                  Batch Q&A wizard — entry point / page router
config/                 Settings (secrets, defaults) & LLM prompt templates
ui/                     Streamlit UI: chat mode, batch output, admin, styling
auth/                   Login/signup screens
db/                     SQLite user store + in-RAM session cache
ingestion/              PDF/DOCX/TXT parsing, table extraction, doc classification
ocr/                    EasyOCR / PaddleOCR / Tesseract engines + preprocessing
chunking/               Fixed / recursive / semantic / sliding-window chunkers
embeddings/             Local (sentence-transformers) + cloud embedders
indexing/               FAISS-backed hierarchical index, BM25 index
retrieval/              Hybrid retriever, reranker, multi-query, semantic cache,
                        real-time web search
agent/                  ReAct agent (AgenticRAG) — chat & batch reasoning loop
llm/                    Prompt builder, answer generator, citation formatter,
                        confidence scorer, fact checker, regenerate
parsers/                Question-list parsing, document structure parsing
outputs/                PDF/DOCX/TXT/JSON exporters for batch results
utils/                  Logging, device (CPU/GPU) detection, PDF highlighting,
                        feedback store, misc helpers
```
