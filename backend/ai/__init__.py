"""Model client abstraction: one interface, Beam first."""

from __future__ import annotations

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
        temperature: float | None = None,
    ) -> Completion: ...


__all__ = ["ModelError", "Completion", "ModelClient"]
