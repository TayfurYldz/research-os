"""Provider-neutral ModelPort consumed by Research. Not a vendor SDK.

Concrete adapters belong in Integrations (or a later Platform adapter).
Research must not import provider SDKs. Output is UNTRUSTED STRUCTURED PROPOSAL.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Protocol


class ModelRole(Enum):
    """Reasoning job. Not a vendor, not a Finding authority, not a router product."""

    GENERATOR = "GENERATOR"
    FALSIFIER = "FALSIFIER"


class ModelPortError(ValueError):
    """Invalid ModelPort request or result envelope. Not a Core DENY."""


@dataclass(frozen=True)
class ModelCallRequest:
    """One reasoning invocation. Instructions and untrusted data stay separate."""

    role: ModelRole
    correlation_id: str
    context_fingerprint: str
    instructions: str
    payload: Mapping[str, object]
    model_id_hint: str | None = None
    timeout_ms: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.role, ModelRole):
            raise ModelPortError("role must be a ModelRole")
        if not isinstance(self.correlation_id, str) or not self.correlation_id.strip():
            raise ModelPortError("correlation_id must be a non-empty string")
        if not isinstance(self.context_fingerprint, str) or not self.context_fingerprint.strip():
            raise ModelPortError("context_fingerprint must be a non-empty string")
        if not isinstance(self.instructions, str) or not self.instructions.strip():
            raise ModelPortError("instructions must be a non-empty string")
        if not isinstance(self.payload, Mapping):
            raise ModelPortError("payload must be a mapping")
        object.__setattr__(self, "payload", dict(self.payload))
        if self.timeout_ms is not None and (
            not isinstance(self.timeout_ms, int) or isinstance(self.timeout_ms, bool) or self.timeout_ms <= 0
        ):
            raise ModelPortError("timeout_ms must be a positive int when set")


@dataclass(frozen=True)
class ModelCallResult:
    """Untrusted structured output plus adapter identity. Do not invent missing fields."""

    role: ModelRole
    adapter_identity: str
    provider_adapter_identity: str
    structured_output: Mapping[str, object]
    model_id: str | None = None
    model_version: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.role, ModelRole):
            raise ModelPortError("role must be a ModelRole")
        if not isinstance(self.adapter_identity, str) or not self.adapter_identity.strip():
            raise ModelPortError("adapter_identity must be a non-empty string")
        if (
            not isinstance(self.provider_adapter_identity, str)
            or not self.provider_adapter_identity.strip()
        ):
            raise ModelPortError("provider_adapter_identity must be a non-empty string")
        if not isinstance(self.structured_output, Mapping):
            raise ModelPortError("structured_output must be a mapping")
        object.__setattr__(self, "structured_output", dict(self.structured_output))
        if self.model_id is not None and (
            not isinstance(self.model_id, str) or not self.model_id.strip()
        ):
            raise ModelPortError("model_id must be a non-empty string when set")
        if self.model_version is not None and (
            not isinstance(self.model_version, str) or not self.model_version.strip()
        ):
            raise ModelPortError("model_version must be a non-empty string when set")


class ModelPort(Protocol):
    """Replaceable completion port. Implementations must not live in Core."""

    def complete(self, request: ModelCallRequest) -> ModelCallResult: ...
