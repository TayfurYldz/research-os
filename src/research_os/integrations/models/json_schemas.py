"""Transport JSON Schema for ModelPort structured output. Not Research validation."""

from __future__ import annotations

from typing import Any

_STRING = {"type": "string"}
_STRING_OR_NULL = {"type": ["string", "null"]}
_STRING_ARRAY = {"type": "array", "items": {"type": "string"}}


def _object(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


GENERATOR_OUTPUT_SCHEMA = _object(
    {
        "proposed_claim": _STRING,
        "rationale": _STRING,
        "source_references": _STRING_ARRAY,
        "assumptions": _STRING_ARRAY,
        "unresolved_questions": _STRING_ARRAY,
        "suggested_disconfirming_test": _STRING,
        "suggested_capability": _STRING,
        "expected_security_relevance": _STRING_OR_NULL,
        "novelty_basis": _STRING,
    }
)

FALSIFIER_OUTPUT_SCHEMA = _object(
    {
        "alternative_explanations": _STRING_ARRAY,
        "missing_preconditions": _STRING_ARRAY,
        "contradictory_source_references": _STRING_ARRAY,
        "required_negative_controls": _STRING_ARRAY,
        "reasons_not_to_test": _STRING_ARRAY,
        "proposed_disconfirming_observation": _STRING,
        "ambiguity": _STRING_OR_NULL,
    }
)


def schema_for_role(role_value: str) -> dict[str, Any]:
    if role_value == "GENERATOR":
        return GENERATOR_OUTPUT_SCHEMA
    if role_value == "FALSIFIER":
        return FALSIFIER_OUTPUT_SCHEMA
    raise ValueError(f"unsupported model role for schema: {role_value}")
