# server/tests/_e2e_utils.py
import os, time, socket, subprocess, sys
from contextlib import closing
from pathlib import Path

def wait_port(host: str, port: int, timeout: float = 10.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock.settimeout(0.5)
            if sock.connect_ex((host, port)) == 0:
                return True
        time.sleep(0.1)
    return False

class UvicornProc:
    def __init__(self, host="127.0.0.1", port=8123, env=None):
        self.host = host
        self.port = port
        self.env = {**os.environ, **(env or {})}
        self.proc = None
        # repo_root = server/
        self.cwd = str(Path(__file__).resolve().parents[1])

    def __enter__(self):
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", self.host, "--port", str(self.port)],
            cwd=self.cwd,
            env=self.env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        if not wait_port(self.host, self.port, timeout=15):
            self.kill()
            raise RuntimeError("uvicorn did not start in time")
        return self

    def kill(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except Exception:
                self.proc.kill()

    def __exit__(self, exc_type, exc, tb):
        self.kill()

    def stream_output(self):
        if not self.proc or not self.proc.stdout:
            return
        for line in self.proc.stdout:
            yield line.rstrip()
