"""Application helper: redirect Location becomes a fresh scope candidate. Not a grant."""

from __future__ import annotations

from research_os.core.scope import ScopeCheck
from research_os.core.scope_compiler import CompiledScope, ScopeCandidate, evaluate_scope_candidate
from research_os.platform.url_normalize import normalize_url


def scope_candidate_from_redirect_location(location: str) -> ScopeCandidate:
    return normalize_url(location)


def reevaluate_redirect_location(location: str, compiled: CompiledScope) -> ScopeCheck:
    """Worker does not follow redirects. Core re-evaluates the Location as a new candidate."""

    return evaluate_scope_candidate(scope_candidate_from_redirect_location(location), compiled)
