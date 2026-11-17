"""Stub model client for tests and offline development."""

from __future__ import annotations

from typing import Any

try:
    from ai import Completion
except Exception:
    from backend.ai import Completion


class StubClient:
    def __init__(
        self,
        *,
        text: str = "",
        reasoning: str | None = None,
        usage: dict[str, Any] | None = None,
        latency_ms: int = 0,
        replies: list[tuple[str, str | None]] | None = None,
    ) -> None:
        self.text = text
        self.reasoning = reasoning
        self.usage = usage or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        self.latency_ms = latency_ms
        self.replies = list(replies) if replies else None
        self.calls: list[dict] = []

    async def complete(self, system, messages, max_tokens, *, purpose):
        self.calls.append({"system": system, "messages": messages, "max_tokens": max_tokens, "purpose": purpose})
        if self.replies:
            text, reasoning = self.replies.pop(0)
        else:
            text, reasoning = self.text, self.reasoning
        return Completion(text=text, reasoning=reasoning, usage=self.usage, latency_ms=self.latency_ms)
