# server/tests/test_e2e_uvicorn_live_llm.py
import os, requests, pytest
from ._e2e_utils import UvicornProc

API = "http://127.0.0.1:8124"

@pytest.mark.live_llm
@pytest.mark.skipif(not os.getenv("LLM_API_KEY"), reason="LLM_API_KEY not set")
def test_e2e_live_llm_roundtrip():
    # Provider-agnostic env so it runs with Gemini (or any provider using LLM_*).
    env = {
        "ALLOWED_ORIGINS": "http://127.0.0.1:5501,*",
        "LLM_API_URL": os.environ.get("LLM_API_URL", "https://generativelanguage.googleapis.com/v1beta"),
        "LLM_API_KEY": os.environ["LLM_API_KEY"],
        "LLM_MODEL": os.environ.get("LLM_MODEL", "gemini-1.5-flash"),
    }
    with UvicornProc(port=8124, env=env):
        r = requests.get(f"{API}/health", timeout=10)
        assert r.ok and r.json().get("ok") is True

        body = {
            "repo": "fromLELI/storycompare-with-LLM",
            "branch": "main",
            "include_ext": [".py"],
            "include_paths": ["/"],          # allow all so we don't miss files
            "requisitos": "Sem codigo duplicado!",
            "debug_no_llm": False,
            "max_files": 3,
            "max_bytes": 60_000,
            # Explicitly pass model; server also reads from env.
            "model": env["LLM_MODEL"],
        }
        r = requests.post(f"{API}/compare", json=body, timeout=120)
        if r.status_code == 429:
            pytest.skip("rate-limited (TPM). Retry later.")
        assert r.ok, r.text
        j = r.json()
        assert isinstance(j.get("report", ""), str)
        assert isinstance(j.get("summary", []), list)
        assert isinstance(j.get("updated_files", []), list)
        for f in j.get("updated_files", []):
            assert "path" in f and "content" in f
