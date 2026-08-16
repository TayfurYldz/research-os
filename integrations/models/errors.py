"""Map provider SDK exceptions to provider-neutral ModelPort errors."""

from __future__ import annotations

from research_os.research.model_port import (
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderRuntimeError,
    ProviderTimeoutError,
)

from integrations.models.secrets import redact_secret


def classify_provider_exception(exc: BaseException, *, secret: str | None = None) -> Exception:
    name = type(exc).__name__.lower()
    message = redact_secret(str(exc), secret)
    status = _status_code(exc)
    combined = f"{name} {message} {status}".lower()
    if status == 401 or status == 403 or "auth" in combined or "api_key" in combined or "unauthorized" in combined:
        return ProviderAuthError(message)
    if status == 429 or "rate" in combined or "overloaded" in combined:
        return ProviderRateLimitError(message)
    if status == 408 or "timeout" in combined or "timed out" in combined:
        return ProviderTimeoutError(message)
    if (
        status == 400
        and ("content" in combined or "safety" in combined or "policy" in combined)
    ) or "content_filter" in combined or "content_policy" in combined:
        from research_os.research.model_port import ContentPolicyBlockedError

        return ContentPolicyBlockedError(message)
    return ProviderRuntimeError(message)


def _status_code(exc: BaseException) -> int | None:
    for attr in ("status_code", "status", "http_status"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    response = getattr(exc, "response", None)
    if response is not None:
        value = getattr(response, "status_code", None)
        if isinstance(value, int):
            return value
    return None
