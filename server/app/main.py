import os, base64, logging, fnmatch, time, re
from typing import List, Optional, Dict, Any, Tuple
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from github import Github, GithubIntegration
from github.GithubException import GithubException
from dotenv import load_dotenv
import requests

load_dotenv()

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")
allow_origins = ["*"] if ALLOWED_ORIGINS.strip() == "*" else [
    o.strip() for o in ALLOWED_ORIGINS.split(",") if o.strip()
]
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

log = logging.getLogger("uvicorn.error")

# =============================================================================
# Models
# =============================================================================
class CompareIn(BaseModel):
    repo: str
    branch: Optional[str] = "main"
    include_ext: List[str] = Field(default_factory=lambda: [".py", ".js", ".java"])
    include_paths: List[str] = Field(default_factory=list)
    requisitos: str
    prompt_base: Optional[str] = None
    max_files: int = 200
    max_bytes: int = 800_000
    debug_no_llm: bool = False

    # Generic LLM config
    llm_api_url: Optional[str] = None
    llm_api_key: Optional[str] = None
    model: Optional[str] = None

    # Back-compat (prefer generic fields above)
    groq_api_key: Optional[str] = None

    # Optional GitHub App BYOK
    github_pat: Optional[str] = None
    github_app_id: Optional[str] = None
    github_installation_id: Optional[str] = None
    github_private_key_pem_b64: Optional[str] = None

    # NEW: debugging / filtering toggles
    debug_echo_raw: bool = False
    allow_placeholders: bool = False

class FileOut(BaseModel):
    path: str
    content: str

class CompareOut(BaseModel):
    report: str
    summary: List[str]
    updated_files: List[FileOut]
    raw: Optional[str] = None

# =============================================================================
# GitHub helpers
# =============================================================================
def gh_via_pat(pat: str) -> Github:
    return Github(pat, timeout=30)

def gh_via_app(app_id: str, installation_id: str, private_key_pem: str) -> Github:
    integ = Github(app_id, private_key_pem)
    token = integ.get_access_token(int(installation_id)).token
    return Github(token, timeout=30)

def gh_client(body: CompareIn) -> Github:
    if body.github_pat:
        return gh_via_pat(body.github_pat)
    if body.github_app_id and body.github_installation_id and body.github_private_key_pem_b64:
        pem = base64.b64decode(body.github_private_key_pem_b64).decode("utf-8")
        return gh_via_app(body.github_app_id, body.github_installation_id, pem)
    app_id = os.getenv("GITHUB_APP_ID")
    inst_id = os.getenv("GITHUB_INSTALLATION_ID")
    key_path = os.getenv("GITHUB_PRIVATE_KEY_PATH")
    if app_id and inst_id and key_path and os.path.exists(key_path):
        with open(key_path, "r") as f:
            pem = f.read()
        return gh_via_app(app_id, inst_id, pem)
    return Github(timeout=30)

# =============================================================================
# Filters
# =============================================================================
def _norm_exts(exts: List[str]) -> List[str]:
    out = []
    for e in exts or []:
        e = e.strip().lower()
        if not e:
            continue
        if e == "*":
            return []  # wildcard = no filter
        if not e.startswith("."):
            e = "." + e
        out.append(e)
    return out

def _norm_path(p: str) -> str:
    out = (p or "").replace("\\", "/")
    while "//" in out:
        out = out.replace("//", "/")
    return out

def _path_matches_any(path: str, patterns: List[str]) -> bool:
    if not patterns:
        return True
    if any(p.strip() == "/" for p in patterns):
        return True
    p_norm = _norm_path(path).lstrip("/")
    for raw in patterns:
        pat = _norm_path(raw).lstrip("/")
        if any(ch in pat for ch in ["*", "?", "["]):
            if fnmatch.fnmatch(p_norm, pat):
                return True
        if p_norm.startswith(pat):
            return True
    return False

def file_allowed(path: str, exts: List[str], include_paths: List[str]) -> bool:
    p = _norm_path(path)
    exts_norm = _norm_exts(exts)
    if exts_norm and not any(p.lower().endswith(e) for e in exts_norm):
        return False
    if not _path_matches_any(p, include_paths):
        return False
    return True

def extract_numbered_code(
    g: Github,
    repo_name: str,
    branch: str,
    include_ext: List[str],
    include_paths: List[str],
    max_files: int,
    max_bytes: int,
) -> Tuple[str, int, int]:
    repo, ref = _repo_and_ref(g, repo_name, branch)
    contents = repo.get_contents("", ref=ref)
    chunks: List[str] = []
    nfiles = 0
    nbytes = 0

    while contents:
        it = contents.pop(0)
        if it.type == "dir":
            dir_path = _norm_path(it.path).rstrip("/") + "/"
            if include_paths and not _path_matches_any(dir_path, include_paths):
                keep = any(_norm_path(p).lstrip("/").startswith(dir_path) for p in include_paths)
                if not keep:
                    continue
            contents.extend(repo.get_contents(it.path, ref=ref))
            continue

        if not file_allowed(it.path, include_ext, include_paths):
            continue

        try:
            blob = it.decoded_content
        except Exception:
            continue

        nfiles += 1
        nbytes += len(blob)
        if nfiles > max_files or nbytes > max_bytes:
            break

        snippet = blob.decode(errors="ignore")
        lines = snippet.splitlines()[:800]
        snippet = "\n".join(lines)
        numbered = "\n".join(f"{i+1}: {line}" for i, line in enumerate(snippet.splitlines()))
        chunks.append(f"### {it.path}\n{numbered}")

    return ("\n\n".join(chunks), nfiles, nbytes)

# =============================================================================
# LLM glue (OpenAI-compatible + Gemini)
# =============================================================================
REF_PROMPT_HDR = (
    "Você é um engenheiro sênior. RETORNE SOMENTE JSON válido em UTF-8, sem markdown, sem comentários.\n"
    "Formato obrigatório: {\"report\":\"...\",\"summary\":[\"...\"],\"updated_files\":[{\"path\":\"...\",\"content\":\"...\"}]}\n"
)

def safe_json(s: str) -> Dict[str, Any]:
    import json
    s = (s or "").strip()
    try:
        j = json.loads(s)
        if isinstance(j, dict):
            return j
    except Exception:
        pass
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", s or "", re.I)
    if m:
        try:
            j = json.loads(m.group(1))
            if isinstance(j, dict):
                return j
        except Exception:
            pass
    return {"report": "", "summary": [], "updated_files": [], "_raw": s}

def _is_gemini_url(api_url: str) -> bool:
    return "generativelanguage.googleapis.com" in (api_url or "")

def _openai_chat(api_url: str, api_key: str, model: str, messages: list, *, temperature=0.2, top_p=0.9) -> str:
    url = api_url or "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {"model": model, "messages": messages, "temperature": temperature, "top_p": top_p}
    for attempt in range(3):
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        status = getattr(r, "status_code", 200)
        if status == 429:
            delay = float(r.headers.get("Retry-After", 1.5 * (attempt + 1)))
            time.sleep(delay)
            continue
        if status >= 400:
            r.raise_for_status()
        j = r.json()
        return j["choices"][0]["message"]["content"]
    r.raise_for_status()
    raise RuntimeError("unexpected")

def _gemini_generate(api_base: str, api_key: str, model: str, user_text: str, *, temperature=0.2, top_p=0.9) -> str:
    base = api_base.rstrip("/")
    endpoint = f"{base}/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [ {"role": "user", "parts": [{"text": user_text}]} ],
        "generationConfig": {"temperature": temperature, "topP": top_p}
    }
    for attempt in range(3):
        r = requests.post(endpoint, json=payload, timeout=60)
        status = getattr(r, "status_code", 200)
        if status == 429:
            delay = float(r.headers.get("Retry-After", 1.5 * (attempt + 1)))
            time.sleep(delay)
            continue
        if status >= 400:
            r.raise_for_status()
        j = r.json()
        cands = (j or {}).get("candidates") or []
        if not cands:
            return ""
        parts = (cands[0].get("content") or {}).get("parts") or []
        out = []
        for p in parts:
            t = p.get("text", "")
            if t:
                out.append(t)
        return "\n".join(out).strip()
    r.raise_for_status()
    raise RuntimeError("unexpected")

def _call_llm_text(api_url: str, api_key: str, model: str, messages: list) -> str:
    if _is_gemini_url(api_url):
        # flatten to one "user" turn for Gemini
        buf = []
        for m in messages:
            role = m.get("role") or "user"
            content = m.get("content") or ""
            if role == "system":
                buf.append(f"[SYSTEM]\n{content}")
            else:
                buf.append(content)
        user_text = "\n\n".join(buf)
        return _gemini_generate(api_url, api_key, model, user_text)
    else:
        return _openai_chat(api_url, api_key, model, messages)

def call_llm_json(api_url: str, api_key: str, model: str, messages: list) -> Tuple[Dict[str, Any], str]:
    text = _call_llm_text(api_url, api_key, model, messages)
    return safe_json(text), text

def llm_refactor_review(api_url: str, api_key: str, requisitos: str, codigo: str, prompt_base: Optional[str], model: str) -> Tuple[Dict[str, Any], str, str]:
    base = prompt_base or ""
    m1 = [
        {"role": "system", "content": REF_PROMPT_HDR + base},
        {"role": "user", "content": f"=== REQUISITOS ===\n{requisitos}\n\n=== CODIGO NUMERADO ===\n{codigo}"},
    ]
    j1, raw1 = call_llm_json(api_url, api_key, model, m1)

    repair_instr = (
        "Valide que o JSON possui as chaves 'report', 'summary'(lista), 'updated_files'(lista de objetos com 'path' e 'content').\n"
        "Se algo faltar, corrija. Retorne SOMENTE JSON válido."
    )
    m2 = [
        {"role": "system", "content": REF_PROMPT_HDR + repair_instr},
        {"role": "user", "content": str(j1)},
    ]
    j2, raw2 = call_llm_json(api_url, api_key, model, m2)

    def looks_ok(j):
        return isinstance(j.get("updated_files"), list) and isinstance(j.get("summary"), list) and isinstance(j.get("report"), str)

    final = j2 if looks_ok(j2) else j1
    final.setdefault("report", "")
    final.setdefault("summary", [])
    final.setdefault("updated_files", [])
    return final, raw1, raw2

# =============================================================================
# Anti-placeholder / sanitize
# =============================================================================
_PLACEHOLDER_PATTERNS = [
    r"conte[uú]do do arquivo",
    r"resultado[s]? dispon[ií]vel",
    r"placeholder",
]
def _looks_like_placeholder(text: str) -> bool:
    t = (text or "").lower()
    if len(t.strip()) < 8:
        return True
    for pat in _PLACEHOLDER_PATTERNS:
        if re.search(pat, t):
            return True
    return False

def _sanitize_llm_output(out: Dict[str, Any], *, allow_placeholders: bool) -> Dict[str, Any]:
    cleaned = {"report": "", "summary": [], "updated_files": []}
    cleaned["report"] = str(out.get("report", "") or "")
    cleaned["summary"] = [str(x) for x in (out.get("summary") or [])]
    seen = set()
    for f in (out.get("updated_files") or []):
        path = str(f.get("path", "")).strip()
        content = str(f.get("content", ""))
        if not path or not content.strip():
            continue
        if path in seen:
            continue
        if not allow_placeholders and _looks_like_placeholder(content):
            continue
        if path.lower().endswith(".py"):
            c = content
            if not any(tok in c for tok in ("def ", "class ", "import ", "if __name__")):
                # still allow if user opted to allow placeholders
                if not allow_placeholders:
                    continue
        seen.add(path)
        cleaned["updated_files"].append({"path": path, "content": content})
    return cleaned

# =============================================================================
# Misc
# =============================================================================
@app.middleware("http")
async def log_req_res(request: Request, call_next):
    try:
        body = (await request.body())[:500].decode(errors="ignore")
        log.info(f"{request.method} {request.url.path} body={body}")
    except Exception:
        pass
    resp = await call_next(request)
    log.info(f"RESP {request.url.path} status={resp.status_code}")
    return resp

@app.exception_handler(Exception)
async def all_exc_handler(request: Request, exc: Exception):
    log.exception("UNHANDLED")
    return JSONResponse(status_code=500, content={"detail": f"internal error: {type(exc).__name__}"})

@app.get("/health")
def health():
    return {"ok": True}

# =============================================================================
# Endpoint
# =============================================================================
@app.post("/compare", response_model=CompareOut)
def compare(body: CompareIn):
    gh = gh_client(body)

    # make bad/empty paths mean "whole repo"
    def _looks_bad(p: str) -> bool:
        return ("/" not in p) and not any(ch in p for ch in "*?[")
    include_paths = body.include_paths or ["/"]
    if include_paths and all(_looks_bad(p) for p in include_paths):
        include_paths = ["/"]

    try:
        code, nfiles, nbytes = extract_numbered_code(
            gh,
            body.repo,
            body.branch or "main",
            body.include_ext,
            include_paths,
            body.max_files,
            body.max_bytes,
        )
    except Exception as e:
        raise HTTPException(400, f"Falha ao ler repositório: {e}")

    if not code.strip():
        raise HTTPException(400, "Nenhum arquivo elegível encontrado (ext/paths).")

    if body.debug_no_llm:
        return {
            "report": f"[debug_no_llm] arquivos={nfiles} bytes={nbytes}",
            "summary": [f"Coletados {nfiles} arquivos (~{nbytes} bytes)"],
            "updated_files": [],
        }

    # Resolve LLM config
    api_url = (body.llm_api_url or os.getenv("LLM_API_URL") or "https://api.groq.com/openai/v1/chat/completions").strip()
    api_key = (body.llm_api_key or body.groq_api_key or os.getenv("LLM_API_KEY") or os.getenv("GROQ_API_KEY") or "").strip()
    model   = (body.model or os.getenv("LLM_MODEL") or os.getenv("GROQ_MODEL") or "llama-3.1-8b-instant").strip()

    if not api_key:
        raise HTTPException(
            400,
            "LLM desabilitado: passe 'debug_no_llm=true' OU forneça 'llm_api_key'/'LLM_API_KEY'."
        )

    try:
        out, raw1, raw2 = llm_refactor_review(api_url, api_key, body.requisitos, code, body.prompt_base, model)
    except requests.HTTPError as e:
        txt = (e.response.text or "")[:400]
        status = getattr(e.response, "status_code", 502)
        if status == 429 or "rate_limit" in txt or "rate_limit_exceeded" in txt:
            raise HTTPException(429, f"Erro ao chamar LLM (rate limit): {txt}")
        raise HTTPException(502, f"Erro ao chamar LLM: {txt}")
    except Exception as e:
        raise HTTPException(502, f"Erro ao chamar LLM: {e}")

    out_sane = _sanitize_llm_output(
        {"report": out.get("report", ""), "summary": out.get("summary", []), "updated_files": out.get("updated_files", [])},
        allow_placeholders=body.allow_placeholders,
    )
    report = out_sane["report"]
    summary = out_sane["summary"]
    files = out_sane["updated_files"]

    if not report.strip() and (summary or files):
        head = "; ".join(summary)[:240] if summary else f"{len(files)} arquivo(s) sugeridos"
        report = head

    resp = {"report": report, "summary": summary, "updated_files": files}
    if body.debug_echo_raw:
        # attach truncated raw for inspection
        raw_combined = (raw2 or raw1 or "")[:8000]
        resp["raw"] = raw_combined
    return resp

def _repo_and_ref(g: Github, repo_name: str, branch: Optional[str]) -> Tuple[Any, str]:
    repo = g.get_repo(repo_name)
    ref = branch or repo.default_branch or "main"
    try:
        repo.get_contents("", ref=ref)
        return repo, ref
    except GithubException:
        try:
            fallback = repo.default_branch or "main"
            if fallback != ref:
                repo.get_contents("", ref=fallback)
                return repo, fallback
        except Exception:
            pass
        raise
