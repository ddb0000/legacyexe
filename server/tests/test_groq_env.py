# tests/test_groq_env.py
import os
import pytest
import requests

API_URL = "https://api.groq.com/openai/v1/models"

@pytest.mark.skipif(not os.getenv("GROQ_API_KEY"), reason="sem GROQ key")
def test_groq_models_list():
    headers = {
        "Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}",
    }
    try:
        resp = requests.get(API_URL, headers=headers, timeout=10)
        resp.raise_for_status()
        models = resp.json()
    except Exception as e:
        pytest.skip(f"rede/ambiente: {e}")
    assert "data" in models
