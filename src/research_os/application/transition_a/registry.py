"""Normalizer registry keyed by trusted request capability/action, not Worker payload."""

from __future__ import annotations

from typing import Any, Mapping, Protocol

from research_os.application.transition_a.diagnostic_echo import DiagnosticEchoNormalizer
from research_os.application.transition_a.drafts import ObservationDraft
from research_os.application.transition_a.errors import UnsupportedNormalizerError


class ObservationNormalizer(Protocol):
    capability: str
    action: str
    version: str

    def normalize(
        self,
        request: Mapping[str, Any],
        result: Mapping[str, Any],
    ) -> tuple[ObservationDraft, ...]: ...


class NormalizerRegistry:
    def __init__(self, normalizers: tuple[ObservationNormalizer, ...] | None = None) -> None:
        registered = normalizers if normalizers is not None else (DiagnosticEchoNormalizer(),)
        self._normalizers: dict[tuple[str, str], ObservationNormalizer] = {}
        for normalizer in registered:
            key = (normalizer.capability, normalizer.action)
            self._normalizers[key] = normalizer

    def get(self, capability: str, action: str) -> ObservationNormalizer:
        try:
            return self._normalizers[(capability, action)]
        except KeyError as exc:
            raise UnsupportedNormalizerError(
                f"no Transition A normalizer for capability={capability!r} action={action!r}"
            ) from exc
