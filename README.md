# legacy.exe — Compare & Refactor

Minimal **LLM-powered code comparison / refactoring tool**.  
It includes:

- **FastAPI server** (`server/app/main.py`) — GitHub integration, filters, LLM calls.
- **Frontend client** (`frontend/`) — static HTML/JS, runs against your local API.
- **Tests** (`server/tests/`) — unit + e2e with Uvicorn.
- **BYO-key client (old)** (`old/`) — experimental web UI for direct provider calls.

---

## ✨ Features

- Fetches code from GitHub repos (with PAT or GitHub App).
- Filters by file extension + path globs.
- Sends numbered code to an LLM for refactor/review.
- Provider-agnostic: works with **Groq (OpenAI API)** or **Gemini (v1beta)**.
- Returns structured JSON:  
  ```json
  { "report": "...", "summary": ["..."], "updated_files": [{ "path": "...", "content": "..." }] }
  ```

* Frontend UI to run comparisons and download results.

---

## 🚀 Quick Start (Windows/PowerShell)

### Backend (FastAPI)

```powershell
cd server

# (optional) pick your Python; 3.11/3.12 both fine
py -V
py -m venv .venv
.venv\Scripts\Acticvate.ps1

# deps
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
```

#### Env file

```powershell
Copy-Item .env.example .env
notepad .env
```

Set at least:

```
ALLOWED_ORIGINS=http://127.0.0.1:5501,http://localhost:5501

# Prefer Gemini (works out-of-the-box)
LLM_API_URL=https://generativelanguage.googleapis.com/v1beta
LLM_API_KEY=YOUR_GEMINI_KEY
LLM_MODEL=gemini-1.5-flash

# Optional (Groq, OpenAI-compatible)
GROQ_API_KEY=YOUR_GROQ_KEY
GROQ_MODEL=llama-3.1-8b-instant

# Optional GitHub
GITHUB_PAT=
GITHUB_APP_ID=
GITHUB_INSTALLATION_ID=
GITHUB_PRIVATE_KEY_PATH=./keys/github_app.pem
```

#### Run API

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
# → http://127.0.0.1:8000
```

#### Smoke-test API

```powershell
# health
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method GET

$body = @{
  repo          = "fromLELI/storycompare-with-LLM";
  branch        = "main";
  include_ext   = @(".py", ".js", ".html", ".css");
  include_paths = @("/");                            # scan whole repo
  requisitos    = "Refatore o codigo da melhor forma possivel";
  debug_no_llm  = $false;
  max_files     = 10;
  max_bytes     = 200000;

  # get the raw LLM output back for debugging
  debug_echo_raw = $true
} | ConvertTo-Json -Depth 6

$r = Invoke-RestMethod -Uri "http://127.0.0.1:8000/compare" -Method POST -ContentType "application/json" -Body $body
$r | ConvertTo-Json -Depth 10
```

### Frontend (static)

Option A — quick local server (Python):

```powershell
cd ..\frontend
py -m http.server 5501
# → http://127.0.0.1:5501  (open index.html)
```

Option B — VS Code Live Server:

* Open `frontend/` folder in VS Code → “Go Live” (ensure port **5501** if you didn’t change CORS).

### End-to-end flow

1. Start backend (step 1).
2. Start frontend (step 2).
3. In the UI, fill: repo, branch, provider (Gemini or Groq), model, API key.
4. Click **comparar**.
   Result JSON shows `report`, `summary`, `updated_files`.

### Running tests (Windows)

```powershell
cd server
.\.venv\Scripts\Activate.ps1

# Unit + debug tests (no live LLM)
pytest -q

# Live LLM (needs LLM_API_KEY in your .env)
pytest -q -m live_llm
```

### PowerShell curl equivalent (if you prefer curl.exe)

```powershell
curl.exe -s "http://127.0.0.1:8000/compare" -H "content-type: application/json" -d ^
"{`"repo`":`"ddb0000/legacyexe`",`"branch`":`"main`",`"include_ext`":[`".py`",`".js`"],`"include_paths`":[`"server/`",`"frontend/`"],`"requisitos`":`"Sem codigo duplicado!`",`"debug_no_llm`":false}"
```

That’s it. Run API, run static server, hit `/compare`.

---

## 🚀 Quick Start (Linux)

### 1. Clone & install 

```bash
cd server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment

Copy `.env.example` → `.env` and edit:

```dotenv
# CORS (local frontend)
ALLOWED_ORIGINS=http://127.0.0.1:5501,http://localhost:5501

# === Generic LLM config (preferred) ===
LLM_API_URL=https://generativelanguage.googleapis.com/v1beta
LLM_API_KEY=your_gemini_key
LLM_MODEL=gemini-1.5-flash

# === Back-compat (Groq) ===
GROQ_API_KEY=your_groq_key
GROQ_MODEL=llama-3.1-8b-instant

# === GitHub auth (optional) ===
GITHUB_PAT=
GITHUB_APP_ID=
GITHUB_INSTALLATION_ID=
GITHUB_PRIVATE_KEY_PATH=./keys/github_app.pem
```

### 3. Run server

```bash
uvicorn app.main:app --reload
# API at http://127.0.0.1:8000
```

### 4. Run frontend

Open `frontend/index.html` in a browser. (LiverServer preferred)
Fill in repo, branch, model, key → click **comparar**.

---

## 📡 API

**POST** `/compare`

```json
{
  "repo": "org/repo",
  "branch": "main",
  "include_ext": [".py",".js"],
  "include_paths": ["src/"],
  "requisitos": "Sem código duplicado!",
  "debug_no_llm": false,
  "max_files": 10,
  "max_bytes": 200000
}
```

Response:

```json
{
  "report": "Refatoração aplicada",
  "summary": ["..."],
  "updated_files": [
    { "path": "src/util.py", "content": "def util(): ..." }
  ]
}
```

Health check:
`GET /health` → `{"ok": true}`

---

## 🧪 Tests

From `server/`:

```bash
pytest -q               # unit + debug tests
pytest -q -m live_llm   # live LLM tests (requires LLM_API_KEY in env)
```

* `test_e2e_uvicorn_debug.py`: spins up API with `debug_no_llm`.
* `test_e2e_uvicorn_live_llm.py`: full roundtrip with real LLM.
* Unit tests: filters, safe\_json, repo fallback, etc.

---

## 🖥️ Project Layout

```
frontend/       # static UI
server/app/     # FastAPI app
server/tests/   # pytest suite
```

---

## 🔑 Providers

* **Gemini** (preferred):

  ```
  LLM_API_URL=https://generativelanguage.googleapis.com/v1beta
  LLM_MODEL=gemini-1.5-flash
  ```
* **Groq (OpenAI-compat)**:

  ```
  LLM_API_URL=https://api.groq.com/openai/v1/chat/completions
  LLM_MODEL=llama-3.1-8b-instant
  ```

Pass via `.env` or override in request body.

---

## ⚡ Roadmap

* Multi-file patch/diff export
* Better error surfaces in frontend
* More providers (OpenAI, Anthropic, etc.)
* Richer unit test coverage