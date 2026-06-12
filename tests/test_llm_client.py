from __future__ import annotations

import sys
import types

from src.llm_client import GeminiClient


def test_gemini_client_uses_google_genai(monkeypatch) -> None:
    genai_module = types.ModuleType("google.genai")

    class FakeResponse:
        def __init__(self, text: str) -> None:
            self.text = text

    class FakeModels:
        def generate_content(self, *, model: str, contents: str, config=None):
            assert model == "gemini"
            assert contents == "hello"
            return FakeResponse("generated text")

    class FakeClient:
        def __init__(self, *, api_key: str | None = None) -> None:
            assert api_key == "test-key"
            self.models = FakeModels()

    genai_module.Client = FakeClient

    google_module = types.ModuleType("google")
    google_module.__path__ = []
    google_module.genai = genai_module

    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.genai", genai_module)

    client = GeminiClient("test-key", "gemini")
    assert client.generate_text("hello") == "generated text"


def test_gemini_client_uses_legacy_google_generativeai(monkeypatch) -> None:
    generativeai_module = types.ModuleType("google.generativeai")

    def configure(api_key: str | None) -> None:
        assert api_key == "legacy-key"

    def respond(model: str, prompt: str) -> str:
        assert model == "gemini"
        assert prompt == "world"
        return "legacy response"

    generativeai_module.configure = configure
    generativeai_module.respond = respond

    google_module = types.ModuleType("google")
    google_module.__path__ = []

    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.generativeai", generativeai_module)
    monkeypatch.syspath_prepend("")

    client = GeminiClient("legacy-key", "gemini")
    assert client.generate_text("world") == "legacy response"
