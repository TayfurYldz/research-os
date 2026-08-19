"""OAST domain types. Pure research layer; no network, no execution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Protocol, runtime_checkable

from research_os.research.types import ResearchInputError


class OastError(Exception):
    """OAST operational failure. Does not create Evidence or Finding."""


class OastTokenExpiredError(OastError):
    """Callback received for an expired token."""


class OastCallbackNotFoundError(OastError):
    """No callback recorded for the requested token."""


def _require_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ResearchInputError(f"{field_name} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True)
class OastToken:
    """Opaque callback token bound to a research run + hypothesis + target."""

    token_id: str
    research_run_id: str
    hypothesis_id: str
    target_reference: str
    expires_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "token_id", _require_text(self.token_id, "token_id"))
        object.__setattr__(
            self, "research_run_id", _require_text(self.research_run_id, "research_run_id")
        )
        object.__setattr__(
            self, "hypothesis_id", _require_text(self.hypothesis_id, "hypothesis_id")
        )
        object.__setattr__(
            self, "target_reference", _require_text(self.target_reference, "target_reference")
        )
        if not isinstance(self.expires_at, datetime):
            raise ResearchInputError("expires_at must be a datetime")
        if self.expires_at.tzinfo is None or self.expires_at.utcoffset() is None:
            raise ResearchInputError("expires_at must be timezone-aware")


@dataclass(frozen=True)
class OastCallback:
    """One callback hit matched to a token."""

    callback_id: str
    token_id: str
    received_at: datetime
    source_address: str
    request_summary: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "callback_id", _require_text(self.callback_id, "callback_id"))
        object.__setattr__(self, "token_id", _require_text(self.token_id, "token_id"))
        object.__setattr__(
            self, "source_address", _require_text(self.source_address, "source_address")
        )
        if not isinstance(self.received_at, datetime):
            raise ResearchInputError("received_at must be a datetime")
        if self.received_at.tzinfo is None or self.received_at.utcoffset() is None:
            raise ResearchInputError("received_at must be timezone-aware")
        if not isinstance(self.request_summary, Mapping):
            raise ResearchInputError("request_summary must be a mapping")
        object.__setattr__(self, "request_summary", dict(self.request_summary))


@runtime_checkable
class OastPort(Protocol):
    """Out-of-band callback port. Production implementation lives in workers/."""

    def mint_token(
        self,
        *,
        token_id: str,
        research_run_id: str,
        hypothesis_id: str,
        target_reference: str,
        expires_at: datetime,
    ) -> OastToken: ...

    def poll(self, token_id: str, *, now: datetime) -> tuple[OastCallback, ...]: ...
