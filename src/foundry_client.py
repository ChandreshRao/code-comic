from __future__ import annotations

import logging
from typing import Any, Optional

import requests

logger = logging.getLogger("foundry_client")


class FoundryClient:
    def __init__(self, endpoint: str, api_key: str, timeout: int = 10, cache: bool = False) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.cache = cache

    @classmethod
    def from_config(cls, cfg: Any) -> Optional["FoundryClient"]:
        endpoint = getattr(cfg, "foundry_iq_endpoint", None)
        api_key = getattr(cfg, "foundry_iq_api_key", None)
        timeout = getattr(cfg, "foundry_iq_timeout", 10)
        cache = getattr(cfg, "foundry_iq_cache", False)
        if not endpoint or not api_key:
            return None
        return cls(endpoint, api_key, timeout=timeout, cache=cache)

    def retrieve_knowledge(self, query: str, top_k: int = 5) -> Optional[str]:
        """Query Foundry IQ and return concatenated text snippets or None on failure.

        The client posts JSON {"query": ..., "top_k": N} to the configured endpoint with
        an Authorization: Bearer <API_KEY> header. The response may be any JSON shape; this
        method attempts to extract textual fields sensibly.
        """
        try:
            url = self.endpoint
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {"query": query, "top_k": top_k}
            resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            resp.raise_for_status()
            try:
                j = resp.json()
            except Exception:
                text = resp.text.strip()
                return text or None

            texts: list[str] = []
            # Common response shapes
            if isinstance(j, dict):
                for key in ("results", "items", "documents", "hits"):
                    if key in j and isinstance(j[key], list):
                        for it in j[key]:
                            if isinstance(it, str):
                                texts.append(it)
                            elif isinstance(it, dict):
                                for sub in ("text", "content", "snippet"):
                                    if sub in it and isinstance(it[sub], str):
                                        texts.append(it[sub])
                                        break
            elif isinstance(j, list):
                for it in j:
                    if isinstance(it, str):
                        texts.append(it)
                    elif isinstance(it, dict):
                        for sub in ("text", "content", "snippet"):
                            if sub in it and isinstance(it[sub], str):
                                texts.append(it[sub])
                                break

            if texts:
                return "\n\n".join(texts)

            # Fallback to raw text if available
            text = resp.text.strip()
            return text or None
        except Exception as exc:  # pragma: no cover - network/third-party failures
            logger.debug("Foundry IQ request failed: %s", exc)
            return None
