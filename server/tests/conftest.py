# server/tests/conftest.py
import os, sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]  # .../server
sys.path.insert(0, str(ROOT))