from app.main import _norm_exts, _norm_path, _path_matches_any, file_allowed

def test_norm_exts_accepts_dot_or_not():
    assert _norm_exts([".py","js","  JAVA "]) == [".py",".js",".java"]

def test_norm_path_normalizes_slashes():
    assert _norm_path(r"app\\main.py") == "app/main.py"
    assert _norm_path("app\\\\main.py") == "app/main.py"
    assert _norm_path("app///main.py") == "app/main.py"
    
def test_path_matches_any_prefix_and_glob():
    assert _path_matches_any("src/a.py", ["src/"])
    assert _path_matches_any("src/pkg/x.py", ["src/**/*.py"])
    assert _path_matches_any("anything/here", ["/"])  # wildcard
    assert not _path_matches_any("static/a.css", ["src/"])

def test_file_allowed_combo():
    assert file_allowed("src/a.py", [".py"], ["src/"])
    assert file_allowed("src/pkg/a.py", ["py"], ["src/**/*.py"])
    assert not file_allowed("assets/x.css", [".py"], ["src/"])
