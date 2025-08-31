from app.main import extract_numbered_code, file_allowed

class _FakeContent:
    def __init__(self, path, typ, data=b""):
        self.path = path
        self.type = typ
        self._data = data
    @property
    def decoded_content(self):
        if self.type != "file":
            raise RuntimeError("no content")
        return self._data

class _FakeRepo:
    default_branch = "main"
    def __init__(self):
        # tree:
        #   src/a.py   "print(1)\n"
        #   src/b.js   "console.log(2)\n"
        #   static/x.css "..."
        self._root = [
            _FakeContent("src", "dir"),
            _FakeContent("static", "dir"),
        ]
        self._src = [
            _FakeContent("src/a.py", "file", b"print(1)\n"),
            _FakeContent("src/b.js", "file", b"console.log(2)\n"),
        ]
        self._static = [
            _FakeContent("static/x.css", "file", b"body{}"),
        ]
    def get_contents(self, path, ref="main"):
        if path == "":
            return list(self._root)
        if path == "src":
            return list(self._src)
        if path == "static":
            return list(self._static)
        raise FileNotFoundError(path)

class _FakeGH:
    def get_repo(self, name):
        assert name == "org/repo" or name == "fromLELI/storycompare-with-LLM"
        return _FakeRepo()

def test_extract_numbered_code_filters_and_limits():
    code, nfiles, nbytes = extract_numbered_code(
        _FakeGH(), "org/repo", "main",
        include_ext=[".py",".js"], include_paths=["src/"],
        max_files=10, max_bytes=1_000_000,
    )
    assert "### src/a.py" in code and "1: print(1)" in code
    assert "### src/b.js" in code and "1: console.log(2)" in code
    assert "static/x.css" not in code
    assert nfiles == 2 and nbytes > 0
