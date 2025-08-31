import json
import types
from fastapi.testclient import TestClient
import app.main as m

# build a tiny fake GH client so /compare doesn't hit network
class _FakeContent:
    def __init__(self, path, typ, data=b""):
        self.path = path; self.type = typ; self._data = data
    @property
    def decoded_content(self):
        return self._data

class _FakeRepo:
    default_branch = "main"
    def get_contents(self, path, ref="main"):
        if path == "":
            return [_FakeContent("src","dir")]
        if path == "src":
            return [_FakeContent("src/a.py","file", b"print('legacy')\n")]
        return []

class _FakeGH:
    def get_repo(self, name):
        return _FakeRepo()

def _mk_client(monkeypatch, groq_mock=None):
    # monkeypatch GH client factory
    monkeypatch.setattr(m, "gh_client", lambda body: _FakeGH())
    # monkeypatch requests.post used by _groq_chat
    if groq_mock:
        import requests
        monkeypatch.setattr(requests, "post", groq_mock)
    return TestClient(m.app)

def test_compare_debug_no_llm(monkeypatch):
    c = _mk_client(monkeypatch)
    r = c.post("/compare", json={
        "repo":"fromLELI/storycompare-with-LLM",
        "branch":"main",
        "include_ext":[".py"],
        "include_paths":["src/"],
        "requisitos":"Sem duplicado",
        "debug_no_llm": True
    })
    assert r.status_code == 200
    j = r.json()
    assert "report" in j and j["updated_files"] == []

def test_compare_llm_ok(monkeypatch):
    # emulate 2-pass: first returns minimal JSON, second returns corrected JSON
    calls = {"n":0}
    def fake_post(url, headers=None, json=None, timeout=60):
        class R:
            def __init__(self, content):
                self._content = content
            def raise_for_status(self): return None
            def json(self): return self._content
        calls["n"] += 1
        if calls["n"] == 1:
            content = {"choices":[{"message":{"content":'{"report":"r1","summary":[],"updated_files":[]}'}}]}
        else:
            content = {"choices":[{"message":{"content":'{"report":"r2","summary":["ok"],"updated_files":[{"path":"src/a.py","content":"print(42)"}]}'}}]}
        return R(content)

    c = _mk_client(monkeypatch, groq_mock=fake_post)
    r = c.post("/compare", json={
        "repo":"fromLELI/storycompare-with-LLM",
        "branch":"main",
        "include_ext":[".py"],
        "include_paths":["src/"],
        "requisitos":"Sem duplicado",
        "debug_no_llm": False,
        "groq_api_key": "xxx"
    })
    assert r.status_code == 200
    j = r.json()
    assert j["report"] == "r2"
    assert j["summary"] == ["ok"]
    assert j["updated_files"] and j["updated_files"][0]["path"] == "src/a.py"

def test_compare_llm_error_bubbles_502(monkeypatch):
    def fake_post(url, headers=None, json=None, timeout=60):
        class R:
            def raise_for_status(self):
                # emulate HTTP error from Groq
                from requests import HTTPError, Response
                resp = Response()
                resp._content = b'{"error":{"message":"model_decommissioned"}}'
                resp.status_code = 400
                raise HTTPError(response=resp)
            def json(self): return {}
        return R()
    c = _mk_client(monkeypatch, groq_mock=fake_post)
    r = c.post("/compare", json={
        "repo":"fromLELI/storycompare-with-LLM",
        "branch":"main",
        "include_ext":[".py"],
        "include_paths":["src/"],
        "requisitos":"x",
        "debug_no_llm": False,
        "groq_api_key": "xxx"
    })
    assert r.status_code == 502

def test_cors_preflight(monkeypatch):
    c = _mk_client(monkeypatch)
    r = c.options("/compare", headers={
        "Origin":"http://127.0.0.1:5501",
        "Access-Control-Request-Method":"POST"
    })
    assert r.status_code == 200
