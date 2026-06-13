from __future__ import annotations

from types import SimpleNamespace

from src.foundry_client import FoundryClient


class _DummyResp:
    def __init__(self, data):
        self._data = data
        self.text = "raw"

    def raise_for_status(self):
        return None

    def json(self):
        return self._data


def test_foundry_client_retrieves_and_parses(monkeypatch):
    def fake_post(url, json, headers, timeout):
        assert "query" in json
        # Simulate a typical foundry-like response shape
        return _DummyResp({"results": [{"text": "snippet one"}, {"text": "snippet two"}]})

    monkeypatch.setattr("src.foundry_client.requests.post", fake_post)

    cfg = SimpleNamespace(foundry_iq_endpoint="https://example.com/query", foundry_iq_api_key="k", foundry_iq_timeout=5, foundry_iq_cache=False)
    client = FoundryClient.from_config(cfg)
    assert client is not None
    text = client.retrieve_knowledge("some repo query", top_k=3)
    assert text is not None
    assert "snippet one" in text
    assert "snippet two" in text
