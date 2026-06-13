from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.image_client import (
    ChainedImageClient,
    GeminiImageClient,
    HuggingFaceImageClient,
    ImageClient,
)


class _FakeImage:
    def save(self, path: Path) -> None:
        Path(path).write_bytes(b"fake-png-bytes")


class _FakePart:
    def __init__(self, *, inline_data: object | None = object()) -> None:
        self.inline_data = inline_data
        self.text = None

    def as_image(self) -> _FakeImage:
        return _FakeImage()


class _FakeResponse:
    def __init__(self, parts: list[_FakePart]) -> None:
        self.parts = parts


def test_gemini_image_client_writes_image_on_success(tmp_path: Path) -> None:
    output_path = tmp_path / "panel-1.png"
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _FakeResponse([_FakePart()])
    mock_genai = MagicMock()
    mock_genai.Client.return_value = mock_client
    mock_types = MagicMock()
    mock_google = MagicMock()
    mock_google.genai = mock_genai

    with patch.dict("sys.modules", {"google": mock_google, "google.genai": mock_genai, "google.genai.types": mock_types}):
        client = GeminiImageClient("test-api-key", "gemini-2.5-flash-image")
        result = client.generate_image("A comic panel about code", output_path)

    assert result == output_path
    assert output_path.read_bytes() == b"fake-png-bytes"
    mock_client.models.generate_content.assert_called_once()
    call_kwargs = mock_client.models.generate_content.call_args.kwargs
    assert call_kwargs["model"] == "gemini-2.5-flash-image"
    assert call_kwargs["contents"] == "A comic panel about code"


def test_gemini_image_client_raises_when_api_key_missing(tmp_path: Path) -> None:
    client = GeminiImageClient(None, "gemini-2.5-flash-image")

    with pytest.raises(RuntimeError, match="requires an API key"):
        client.generate_image("prompt", tmp_path / "panel.png")


def test_gemini_image_client_raises_when_no_image_in_response(tmp_path: Path) -> None:
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _FakeResponse([_FakePart(inline_data=None)])
    mock_genai = MagicMock()
    mock_genai.Client.return_value = mock_client
    mock_types = MagicMock()
    mock_google = MagicMock()
    mock_google.genai = mock_genai

    with patch.dict("sys.modules", {"google": mock_google, "google.genai": mock_genai, "google.genai.types": mock_types}):
        client = GeminiImageClient("test-api-key", "gemini-2.5-flash-image")

        with pytest.raises(RuntimeError, match="no image data"):
            client.generate_image("prompt", tmp_path / "panel.png")


class _FakePILImage:
    def save(self, path: Path) -> None:
        Path(path).write_bytes(b"hf-png-bytes")


def test_huggingface_image_client_writes_image_on_success(tmp_path: Path) -> None:
    output_path = tmp_path / "panel-1.png"
    mock_inference_client = MagicMock()
    mock_inference_client.text_to_image.return_value = _FakePILImage()
    mock_hf_module = MagicMock()
    mock_hf_module.InferenceClient.return_value = mock_inference_client

    with patch.dict("sys.modules", {"huggingface_hub": mock_hf_module}):
        client = HuggingFaceImageClient("hf-token", "black-forest-labs/FLUX.1-schnell")
        result = client.generate_image("A comic panel about code", output_path)

    assert result == output_path
    assert output_path.read_bytes() == b"hf-png-bytes"
    mock_inference_client.text_to_image.assert_called_once_with("A comic panel about code")


def test_chained_image_client_falls_back_to_secondary(tmp_path: Path) -> None:
    output_path = tmp_path / "panel-1.png"

    class FailingClient:
        model = "primary-model"

        def generate_image(self, prompt: str, output_path: Path) -> Path:
            raise RuntimeError("primary failed")

    class SuccessClient:
        model = "gemini-2.5-flash-image"

        def generate_image(self, prompt: str, output_path: Path) -> Path:
            output_path.write_bytes(b"secondary-bytes")
            return output_path

    chain = ChainedImageClient([FailingClient(), SuccessClient()])  # type: ignore[list-item]
    result = chain.generate_image("prompt", output_path)

    assert result == output_path
    assert output_path.read_bytes() == b"secondary-bytes"


def test_image_client_from_config_builds_chain_for_multiple_models() -> None:
    class FakeConfig:
        image_models_resolved = ["black-forest-labs/FLUX.1-schnell", "gemini-2.5-flash-image"]
        image_provider = None
        hf_api_key = "hf-token"
        gemini_api_key = "gemini-token"
        image_api_key = "fallback-token"

        def _infer_provider_from_model(self, model: str) -> str | None:
            if "gemini" in model:
                return "gemini"
            return "huggingface"

    client = ImageClient.from_config(FakeConfig())
    assert isinstance(client, ChainedImageClient)
    assert len(client._clients) == 2
    assert isinstance(client._clients[0], HuggingFaceImageClient)
    assert isinstance(client._clients[1], GeminiImageClient)
