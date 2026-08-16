"""Provider ModelPort adapters. Research must not import this package."""

from integrations.models.availability import AdapterAvailability, UnavailableReason
from integrations.models.factory import (
    LIVE_ADAPTER_IDS,
    LiveAdapterHandle,
    probe_live_adapter,
    resolve_live_adapter,
)

__all__ = [
    "LIVE_ADAPTER_IDS",
    "AdapterAvailability",
    "LiveAdapterHandle",
    "UnavailableReason",
    "probe_live_adapter",
    "resolve_live_adapter",
]
