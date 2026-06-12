from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

from src.llm_client import (
    ChainedLLMClient,
    GeminiClient,
    HuggingFaceLLMClient,
    LLMClient,
)


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


class _FakeChatMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChatChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeChatMessage(content)


class _FakeChatResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChatChoice(content)]


def test_huggingface_llm_client_uses_chat_completion() -> None:
    mock_inference_client = MagicMock()
    mock_inference_client.chat_completion.return_value = _FakeChatResponse(
        '[{"title": "Scene 1", "description": "Intro.", "speech_bubble": "Hi!", "mermaid": "flowchart TD\\n A-->B"}]'
    )
    mock_hf_module = MagicMock()
    mock_hf_module.InferenceClient.return_value = mock_inference_client

    with patch.dict("sys.modules", {"huggingface_hub": mock_hf_module}):
        client = HuggingFaceLLMClient("hf-token", "meta-llama/Meta-Llama-3-8B-Instruct")
        result = client.generate_text("create scenes")

    assert "Scene 1" in result
    mock_inference_client.chat_completion.assert_called_once()


def test_chained_llm_client_falls_back_to_secondary() -> None:
    class FailingClient:
        model = "gemini"

        def generate_text(self, prompt: str) -> str:
            raise RuntimeError("gemini failed")

    class SuccessClient:
        model = "meta-llama/Meta-Llama-3-8B-Instruct"

        def generate_text(self, prompt: str) -> str:
            return "secondary llm output"

    chain = ChainedLLMClient([FailingClient(), SuccessClient()])  # type: ignore[list-item]
    assert chain.generate_text("prompt") == "secondary llm output"


def test_llm_client_from_config_builds_chain_for_multiple_models(monkeypatch) -> None:
    genai_module = types.ModuleType("google.genai")

    class FakeModels:
        pass

    class FakeClient:
        def __init__(self, *, api_key: str | None = None) -> None:
            self.models = FakeModels()

    genai_module.Client = FakeClient
    google_module = types.ModuleType("google")
    google_module.__path__ = []
    google_module.genai = genai_module

    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.genai", genai_module)

    class FakeConfig:
        llm_models_resolved = ["gemini", "meta-llama/Meta-Llama-3-8B-Instruct"]
        llm_provider = None
        hf_api_key = "hf-token"
        gemini_api_key = "gemini-token"
        llm_api_key = "fallback-token"

        def _infer_provider_from_model(self, model: str) -> str | None:
            if "gemini" in model:
                return "gemini"
            return "huggingface"

    mock_hf_module = MagicMock()
    mock_hf_module.InferenceClient.return_value = MagicMock()

    with patch.dict("sys.modules", {"huggingface_hub": mock_hf_module}):
        client = LLMClient.from_config(FakeConfig())

    assert isinstance(client, ChainedLLMClient)
    assert len(client._clients) == 2
    assert isinstance(client._clients[0], GeminiClient)
    assert isinstance(client._clients[1], HuggingFaceLLMClient)
