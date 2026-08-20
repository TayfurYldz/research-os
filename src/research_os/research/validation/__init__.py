"""SD-G10 independent validation, severity, and circuit-breaker policy."""

from research_os.research.validation.circuit_breaker import (
    CircuitBreakerAction,
    CircuitBreakerDecision,
    FamilyTelemetry,
    evaluate_family_circuit_breaker,
)
from research_os.research.validation.severity import (
    InternalSeverity,
    PlatformSeverityMapping,
    ScopeState,
    SeverityInput,
    SeverityResult,
    ValidationState,
    classify_severity,
)
from research_os.research.validation.tier_gate import (
    ValidationAdmissionDecision,
    ValidationAdmissionOutcome,
    ValidationTier,
    ValidationTierOutcome,
    validate_required_tiers,
)

__all__ = [
    "CircuitBreakerAction",
    "CircuitBreakerDecision",
    "FamilyTelemetry",
    "InternalSeverity",
    "PlatformSeverityMapping",
    "ScopeState",
    "SeverityInput",
    "SeverityResult",
    "ValidationState",
    "ValidationAdmissionDecision",
    "ValidationAdmissionOutcome",
    "ValidationTier",
    "ValidationTierOutcome",
    "classify_severity",
    "evaluate_family_circuit_breaker",
    "validate_required_tiers",
]
