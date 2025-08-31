# server/tests/test_filters.py
from app.main import file_allowed

def test_file_allowed_glob_and_slash():
    assert file_allowed("src/a.py", [".py"], ["/"])
    assert file_allowed("src/pkg/a.py", [".py"], ["src/**/*.py"])
    assert file_allowed("src/pkg/a.py", ["py"], ["src/"])
    assert not file_allowed("static/a.css", [".py"], ["src/"])
