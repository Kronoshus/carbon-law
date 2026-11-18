"""Beam (Reflection) model client: OpenAI-compatible, loop-guarded, one retry."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
import uuid
from typing import Any

import httpx

import db
from ai import ModelError, Completion
from carbon_intake import looping

logger = logging.getLogger("backend.ai.beam")

BASE_URL = os.environ.get("BEAM_BASE_URL", "https://api.reflection.ai/openai/v1")
DEFAULT_MODEL = os.environ.get("BEAM_MODEL", "Beam-1.0-501B-A23B")


class BeamClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self._api_key_override = api_key
        self.base_url = (base_url or BASE_URL).rstrip("/")
        self.model = model or DEFAULT_MODEL
        self._timeout_override = timeout

    def _key(self) -> str:
        if self._api_key_override:
            return self._api_key_override
        key = os.environ.get("REFLECTION_API_KEY") or os.environ.get("BEAM_API_KEY")
        if not key:
            raise ModelError("missing REFLECTION_API_KEY/BEAM_API_KEY")
        return key

    def _timeout(self, purpose: str) -> float:
        if self._timeout_override is not None:
            return self._timeout_override
        if purpose.startswith("draft"):
            return 900.0
        return 120.0

    async def complete(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int,
        *,
        purpose: str,
        temperature: float | None = None,
    ) -> Completion:
        key = self._key()

        req_messages: list[dict] = []
        if system:
            req_messages.append({"role": "system", "content": system})
        for m in messages or []:
            req_messages.append(dict(m))

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": req_messages,
            "max_tokens": int(max_tokens) + 4000,
            "stream": False,
        }
        if temperature is not None:
            payload["temperature"] = temperature

        body_bytes = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        request_hash = hashlib.sha256(body_bytes).hexdigest()

        headers = {
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
        }

        started = time.monotonic()
        retried = False
        response_text_for_hash = ""
        usage: dict[str, Any] = {}
        text = ""
        reasoning = None

        async def _write_row(ok_flag: int, lat: int, resp_hash: str, usg: dict[str, Any]) -> None:
            await asyncio.to_thread(
                db.execute,
                "INSERT INTO ai_calls (id, purpose, model, prompt_tokens, completion_tokens, "
                "latency_ms, cost_usd_est, request_sha256, response_sha256, ok) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    str(uuid.uuid4()),
                    purpose,
                    self.model,
                    usg.get("prompt_tokens"),
                    usg.get("completion_tokens"),
                    lat,
                    None,
                    request_hash,
                    resp_hash,
                    ok_flag,
                ),
            )

        while True:
            try:
                async with httpx.AsyncClient(timeout=self._timeout(purpose)) as client:
                    resp = await client.post(
                        self.base_url + "/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                if 400 <= resp.status_code < 500:
                    # no retry on client errors
                    response_text_for_hash = resp.text
                    latency_ms = int((time.monotonic() - started) * 1000)
                    await _write_row(0, latency_ms, hashlib.sha256(response_text_for_hash.encode("utf-8")).hexdigest(), {})
                    raise ModelError(f"client error {resp.status_code}")
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
                    latency_ms = int((time.monotonic() - started) * 1000)
                    await _write_row(0, latency_ms, hashlib.sha256(response_text_for_hash.encode("utf-8")).hexdigest(), usage)
                    raise ModelError("model looping")
                break
            except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.ConnectError, httpx.RemoteProtocolError) as exc:
                if not retried:
                    retried = True
                    continue
                latency_ms = int((time.monotonic() - started) * 1000)
                resp_hash = hashlib.sha256(response_text_for_hash.encode("utf-8")).hexdigest() if response_text_for_hash else hashlib.sha256(b"").hexdigest()
                await _write_row(0, latency_ms, resp_hash, usage)
                raise ModelError(str(exc)) from exc

        latency_ms = int((time.monotonic() - started) * 1000)
        await _write_row(1, latency_ms, hashlib.sha256(response_text_for_hash.encode("utf-8")).hexdigest(), usage)
        return Completion(text=text, reasoning=reasoning, usage=usage, latency_ms=latency_ms)
