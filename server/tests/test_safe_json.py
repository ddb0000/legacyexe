from app.main import safe_json

def test_safe_json_plain_ok():
    j = safe_json('{"report":"r","summary":["s"],"updated_files":[]}')
    assert j["report"] == "r" and j["summary"] == ["s"]

def test_safe_json_fenced_extraction():
    j = safe_json("```json\n{\"report\":\"ok\",\"summary\":[],\"updated_files\":[]}\n```")
    assert j["report"] == "ok"

def test_safe_json_broken_returns_stub():
    j = safe_json("nonsense")
    assert "report" in j and "updated_files" in j
