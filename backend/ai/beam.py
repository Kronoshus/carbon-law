"""Beam (Reflection) model client: OpenAI-compatible, loop-guarded, one retry."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from typing import Any

import httpx

try:
    from ai import ModelError, Completion, sha256_bytes
except Exception:
    from backend.ai import ModelError, Completion, sha256_bytes
try:
    from carbon_intake import looping
except Exception:
    import sys, os as _os
    sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
    from carbon_intake import looping

logger = logging.getLogger("backend.ai.beam")

BASE_URL = os.environ.get("BEAM_BASE_URL", "https://api.reflection.ai/openai/v1")
DEFAULT_MODEL = os.environ.get("BEAM_MODEL", "Beam-1.0-501B-A23B")

DRAFT_PURPOSES = {"draft_documents", "draft", "draft_all"}


def _resolve_key() -> str:
    key = os.environ.get("REFLECTION_API_KEY") or os.environ.get("BEAM_API_KEY")
    if not key:
        raise ModelError("missing REFLECTION_API_KEY/BEAM_API_KEY")
    return key


class BeamClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.api_key = api_key  # resolved lazily so env set at construction wins
        self._api_key_override = api_key
        self.base_url = (base_url or BASE_URL).rstrip("/")
        self.model = model or DEFAULT_MODEL
        self._timeout_override = timeout

    def _key(self) -> str:
        if self._api_key_override:
            return self._api_key_override
        # read once per call is acceptable here; key is not cached to a global.
        key = os.environ.get("REFLECTION_API_KEY") or os.environ.get("BEAM_API_KEY")
        if not key:
            raise ModelError("missing REFLECTION_API_KEY/BEAM_API_KEY")
        return key

    def _timeout(self, purpose: str) -> float:
        if self._timeout_override is not None:
            return self._timeout_override
        if purpose in DRAFT_PURPOSES or "draft" in (purpose or ""):
            return 900.0
        return 300.0

    async def complete(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int,
        *,
        purpose: str,
    ) -> Completion:
        try:
            import db
        except Exception:
            from backend import db

        key = self._key()
        # Build request messages, preserving reasoning_content on prior turns.
        req_messages: list[dict] = []
        if system:
            req_messages.append({"role": "system", "content": system})
        for m in messages or []:
            # shallow copy to avoid mutating caller's dicts
            req_messages.append(dict(m))

        payload = {
            "model": self.model,
            "messages": req_messages,
            "max_tokens": int(max_tokens) + 4000,
            "stream": False,
            "temperature": 0.7,
            "top_p": 0.9,
        }
        body_bytes = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        request_hash = hashlib.sha256(body_bytes).hexdigest()

        headers = {
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
        }

        started = time.monotonic()
        retried = False
        last_error: Exception | None = None
        response_text_for_hash = ""
        usage: dict[str, Any] = {}
        text = ""
        reasoning = None
        ok = 1

        while True:
            try:
                async with httpx.AsyncClient(timeout=self._timeout(purpose)) as client:
                    resp = await client.post(
                        self.base_url + "/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                if resp.status_code >= 500:
                    raise httpx.HTTPStatusError(
                        f"server error {resp.status_code}",
                        request=resp.request,
                        response=resp,
                    )
                resp.raise_for_status()
                data = resp.json()
                response_text_for_hash = json.dumps(data, ensure_ascii=False, sort_keys=True)
                choice = (data.get("choices") or [{}])[0]
                msg = choice.get("message") or {}
                text = msg.get("content") or ""
                reasoning = msg.get("reasoning_content") or msg.get("reasoning")
                usage = data.get("usage") or {}

                if looping(text):
                    if not retried:
                        retried = True
                        continue
                    raise ModelError("model looping")
                # success
                break
            except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.ConnectError) as exc:
                last_error = exc
                if not retried:
                    retried = True
                    continue
                ok = 0
                raise ModelError(str(exc)) from exc

        latency_ms = int((time.monotonic() - started) * 1000)

        # write ai_calls row
        try:
            db.execute(
                "INSERT INTO ai_calls (id, purpose, model, prompt_tokens, completion_tokens, "
                "latency_ms, cost_usd_est, request_sha256, response_sha256, ok) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    _new_id(),
                    purpose,
                    self.model,
                    usage.get("prompt_tokens"),
                    usage.get("completion_tokens"),
                    latency_ms,
                    None,
                    request_hash,
                    hashlib.sha256(response_text_for_hash.encode("utf-8")).hexdigest(),
                    ok,
                ),
            )
        except Exception:
            logger.exception("failed to write ai_calls row")

        return Completion(text=text, reasoning=reasoning, usage=usage, latency_ms=latency_ms)


def _new_id() -> str:
    import uuid

    return str(uuid.uuid4())
