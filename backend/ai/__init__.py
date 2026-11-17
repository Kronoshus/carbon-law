"""Model client abstraction: one interface, Beam first.

`ModelClient` is the protocol every caller uses; `BeamClient` talks to the
Reflection/Beam OpenAI-compatible endpoint; `StubClient` is for tests.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


class ModelError(Exception):
    """Raised when a model call fails after its single retry."""


@dataclass
class Completion:
    text: str = ""
    reasoning: str | None = None
    usage: dict[str, Any] = field(default_factory=dict)
    latency_ms: int = 0


@runtime_checkable
class ModelClient(Protocol):
    async def complete(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int,
        *,
        purpose: str,
    ) -> Completion: ...


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


__all__ = ["ModelError", "Completion", "ModelClient", "sha256_text", "sha256_bytes"]
