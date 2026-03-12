"""WebSocket message protocol for Ableton Live bridge.

Defines typed message classes and a pending-request registry for
matching async responses to their originating tool calls.
"""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional


@dataclass
class BridgeRequest:
    """Message sent from Python tools to Max for Live."""
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BridgeResponse:
    """Message received from Max for Live."""
    id: str
    result: Optional[Any] = None
    error: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BridgeResponse":
        return cls(
            id=data["id"],
            result=data.get("result"),
            error=data.get("error"),
        )


class PendingRequests:
    """Thread-safe registry of in-flight requests awaiting responses.

    Each send_command() creates a Future, stores it by message ID,
    and awaits it.  When the Max for Live response arrives, resolve()
    completes the matching Future.
    """

    def __init__(self) -> None:
        self._futures: Dict[str, asyncio.Future] = {}

    def create(self, message_id: str) -> asyncio.Future:
        loop = asyncio.get_event_loop()
        fut = loop.create_future()
        self._futures[message_id] = fut
        return fut

    def resolve(self, message_id: str, response: BridgeResponse) -> bool:
        """Resolve a pending future.  Returns True if found."""
        fut = self._futures.pop(message_id, None)
        if fut is None or fut.done():
            return False
        if response.error:
            fut.set_exception(RuntimeError(response.error))
        else:
            fut.set_result(response.result)
        return True

    def cancel_all(self) -> None:
        for fut in self._futures.values():
            if not fut.done():
                fut.cancel()
        self._futures.clear()

    @property
    def count(self) -> int:
        return len(self._futures)
