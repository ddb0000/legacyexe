import os, requests, itertools
from ._e2e_utils import UvicornProc

API = "http://127.0.0.1:8123"

def test_e2e_debug_no_llm():
    env = {
        # Make sure CORS is permissive for local manual tests as well:
        "ALLOWED_ORIGINS": "http://127.0.0.1:5501,*",
        # Ensure a valid non-deprecated default model if someone forgets debug flag later:
        "GROQ_MODEL": os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b"),
    }
    with UvicornProc(port=8123, env=env):
        # health
        r = requests.get(f"{API}/health", timeout=10)
        assert r.ok and r.json().get("ok") is True

        # e2e compare with debug_no_llm (no Groq call)
        body = {
            "repo": "fromLELI/storycompare-with-LLM",
            "branch": "main",
            "include_ext": [".py", ".js", ".java"],
            "include_paths": ["/"],              # keep broad on purpose
            "requisitos": "Sem codigo duplicado!",
            "debug_no_llm": True,
            "max_files": 12,                     # keep token small if someone toggles flag
            "max_bytes": 200_000
        }
        r = requests.post(f"{API}/compare", json=body, timeout=60)
        assert r.ok, r.text
        j = r.json()
        assert "report" in j and "summary" in j and "updated_files" in j
        assert isinstance(j["summary"], list)
        # Debug path should not produce any updated_files:
        assert j["updated_files"] == []
