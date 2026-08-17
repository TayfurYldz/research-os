"""Exact-host scope compilation and evaluation over Platform-normalized candidates.

Core does not parse URLs. Wildcard/glob hosts are rejected. Exclusions win.
"""

from __future__ import annotations

from dataclasses import dataclass

from research_os.core.enums import ReasonCode, ScopeDecision, ScopeRuleEffect
from research_os.core.errors import CoreInputError
from research_os.core.identity import require_opaque_id
from research_os.core.scope import ScopeCheck

DEFAULT_SCHEME_PORTS = {
    "http": 80,
    "https": 443,
}
NORMALIZATION_USERINFO = "USERINFO"
NORMALIZATION_WILDCARD = "WILDCARD"
NORMALIZATION_PATH_AMBIGUOUS = "PATH_AMBIGUOUS"


@dataclass(frozen=True)
class ScopeCandidate:
    raw_target: str
    normalized_scheme: str | None
    normalized_host: str | None
    normalized_port: int | None
    raw_path: str
    scope_match_path: str | None
    normalization_error: str | None


@dataclass(frozen=True)
class ScopeRuleDefinition:
    rule_id: str
    effect: ScopeRuleEffect
    scheme: str
    host: str
    port: int | None
    path_prefix: str | None
    source_reference: str

    def __post_init__(self) -> None:
        require_opaque_id(self.rule_id, "rule_id")
        require_opaque_id(self.source_reference, "source_reference")
        if not isinstance(self.effect, ScopeRuleEffect):
            raise CoreInputError("effect must be ScopeRuleEffect")
        if not isinstance(self.scheme, str) or not self.scheme.strip():
            raise CoreInputError("scheme must be a non-empty string")
        if not isinstance(self.host, str) or not self.host.strip():
            raise CoreInputError("host must be a non-empty string")
        if "*" in self.host or "*" in self.scheme:
            raise CoreInputError("wildcard scope is not allowed")
        if self.port is not None and (not isinstance(self.port, int) or self.port < 1):
            raise CoreInputError("port must be a positive integer or None")
        if self.path_prefix is not None and (
            not isinstance(self.path_prefix, str) or not self.path_prefix.startswith("/")
        ):
            raise CoreInputError("path_prefix must be an absolute path or None")


@dataclass(frozen=True)
class CompiledScopeRule:
    rule_id: str
    effect: ScopeRuleEffect
    scheme: str
    host: str
    port: int
    path_prefix: str | None
    source_reference: str


@dataclass(frozen=True)
class CompiledScope:
    rules: tuple[CompiledScopeRule, ...]


def compile_scope_rules(rules: tuple[ScopeRuleDefinition, ...]) -> CompiledScope:
    compiled: list[CompiledScopeRule] = []
    for rule in rules:
        scheme = rule.scheme.lower().strip()
        if scheme not in DEFAULT_SCHEME_PORTS:
            raise CoreInputError("scheme must be http or https")
        host = rule.host.strip("[]").lower()
        if "*" in host:
            raise CoreInputError("wildcard scope is not allowed")
        port = rule.port if rule.port is not None else DEFAULT_SCHEME_PORTS[scheme]
        compiled.append(
            CompiledScopeRule(
                rule_id=rule.rule_id,
                effect=rule.effect,
                scheme=scheme,
                host=host,
                port=port,
                path_prefix=rule.path_prefix,
                source_reference=rule.source_reference,
            )
        )
    return CompiledScope(rules=tuple(compiled))


def evaluate_scope_candidate(
    candidate: ScopeCandidate, compiled: CompiledScope
) -> ScopeCheck:
    if not isinstance(candidate, ScopeCandidate):
        raise CoreInputError("scope candidate is required")
    if not isinstance(compiled, CompiledScope):
        raise CoreInputError("compiled scope is required")
    if candidate.normalization_error == NORMALIZATION_USERINFO:
        return ScopeCheck(ScopeDecision.DENY, ReasonCode.SCOPE_USERINFO_DENIED, ())
    if candidate.normalization_error == NORMALIZATION_WILDCARD:
        return ScopeCheck(ScopeDecision.DENY, ReasonCode.SCOPE_WILDCARD_REJECTED, ())
    if candidate.normalization_error == NORMALIZATION_PATH_AMBIGUOUS:
        return ScopeCheck(ScopeDecision.DENY, ReasonCode.SCOPE_PATH_AMBIGUOUS, ())
    if candidate.normalization_error is not None:
        return ScopeCheck(ScopeDecision.DENY, ReasonCode.SCOPE_NORMALIZATION_INVALID, ())
    if candidate.scope_match_path is None:
        return ScopeCheck(ScopeDecision.DENY, ReasonCode.SCOPE_PATH_AMBIGUOUS, ())

    matched_exclusions: list[CompiledScopeRule] = []
    matched_allows: list[CompiledScopeRule] = []
    for rule in compiled.rules:
        if not _origin_matches(candidate, rule):
            continue
        if rule.path_prefix is not None and not _path_prefix_matches(
            candidate.scope_match_path, rule.path_prefix
        ):
            continue
        if rule.effect in (ScopeRuleEffect.DENY, ScopeRuleEffect.OUT_OF_SCOPE):
            matched_exclusions.append(rule)
        elif rule.effect is ScopeRuleEffect.ALLOW:
            matched_allows.append(rule)

    if matched_exclusions:
        return ScopeCheck(
            ScopeDecision.DENY,
            ReasonCode.SCOPE_DENIED,
            tuple(item.rule_id for item in matched_exclusions),
        )
    if matched_allows:
        return ScopeCheck(
            ScopeDecision.ALLOW,
            ReasonCode.ALLOWED,
            tuple(item.rule_id for item in matched_allows),
        )
    return ScopeCheck(ScopeDecision.DENY, ReasonCode.SCOPE_NOT_EXPLICITLY_ALLOWED, ())


def _origin_matches(candidate: ScopeCandidate, rule: CompiledScopeRule) -> bool:
    if candidate.normalized_scheme != rule.scheme:
        return False
    if candidate.normalized_host != rule.host:
        return False
    return candidate.normalized_port == rule.port


def _path_prefix_matches(path: str, prefix: str) -> bool:
    if path == prefix:
        return True
    if not prefix.endswith("/"):
        prefix = prefix + "/"
    return path.startswith(prefix)
