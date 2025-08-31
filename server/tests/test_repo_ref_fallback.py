import types
from github.GithubException import GithubException
from app.main import _repo_and_ref

class _RepoWithFallback:
    def __init__(self):
        self.default_branch = "main"
        self.calls = []
    def get_contents(self, path, ref="main"):
        self.calls.append((path, ref))
        if ref == "does-not-exist":
            raise GithubException(404, "not found", None)
        return []  # ok

class _GH:
    def get_repo(self, name):
        return _RepoWithFallback()

def test_repo_and_ref_fallback_to_default():
    repo, ref = _repo_and_ref(_GH(), "any/repo", "does-not-exist")
    assert ref == "main"
