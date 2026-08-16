"""Runtime Draft 2020-12 validation of canonical Worker contracts.

Loads `contracts/` JSON Schema files. Resolves URN `$id` locally.
Never fetches schemas from the network. Does not replace `contracts/` as truth.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from jsonschema.exceptions import SchemaError, ValidationError
from jsonschema.validators import Draft202012Validator
from referencing import Registry, Resource
from referencing.exceptions import Unresolvable
from referencing.jsonschema import DRAFT202012

WORKER_REQUEST_ID = "urn:research-os:contracts:v1:worker-request"
WORKER_RESULT_ID = "urn:research-os:contracts:v1:worker-result"
SUPPORTED_CONTRACT_VERSION = "v1"

CORRELATION_KEYS = (
    "correlation_id",
    "research_run_id",
    "experiment_id",
    "request_id",
)


class ContractValidationError(Exception):
    """Instance failed canonical schema or local $ref resolution."""


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_contracts_root() -> Path:
    return _repo_root() / "contracts" / "v1"


def _no_network_retrieve(uri: str):
    raise Unresolvable(uri)


class ContractValidator:
    """Draft 2020-12 instance validator over the local URN registry."""

    def __init__(self, contracts_root: Path | None = None) -> None:
        self._root = contracts_root or default_contracts_root()
        self._schemas: dict[str, dict[str, Any]] = {}
        registry: Registry = Registry(retrieve=_no_network_retrieve)
        for path in sorted(self._root.rglob("*.schema.json")):
            contents = json.loads(path.read_text(encoding="utf-8"))
            schema_id = contents.get("$id")
            if not isinstance(schema_id, str) or not schema_id.startswith(
                "urn:research-os:contracts:v1:"
            ):
                raise ContractValidationError(
                    f"refusing schema without local v1 $id: {path}"
                )
            self._schemas[schema_id] = contents
            registry = registry.with_resource(
                schema_id,
                Resource.from_contents(contents, default_specification=DRAFT202012),
            )
        self._registry = registry
        for required in (WORKER_REQUEST_ID, WORKER_RESULT_ID):
            if required not in self._schemas:
                raise ContractValidationError(f"missing canonical schema {required}")

    def _validator(self, schema_id: str) -> Draft202012Validator:
        schema = self._schemas[schema_id]
        return Draft202012Validator(
            schema,
            registry=self._registry,
            format_checker=Draft202012Validator.FORMAT_CHECKER,
        )

    def validate_worker_request(self, document: Mapping[str, Any]) -> None:
        self._validate_version(document)
        self._validate(WORKER_REQUEST_ID, document)

    def validate_worker_result(self, document: Mapping[str, Any]) -> None:
        self._validate_version(document)
        self._validate(WORKER_RESULT_ID, document)

    def correlation_matches(
        self, request: Mapping[str, Any], result: Mapping[str, Any]
    ) -> bool:
        request_corr = request.get("correlation")
        result_corr = result.get("correlation")
        if not isinstance(request_corr, Mapping) or not isinstance(result_corr, Mapping):
            return False
        return all(request_corr.get(key) == result_corr.get(key) for key in CORRELATION_KEYS)

    def _validate_version(self, document: Mapping[str, Any]) -> None:
        version = document.get("contract_version")
        if version != SUPPORTED_CONTRACT_VERSION:
            raise ContractValidationError(
                f"unsupported contract_version {version!r}; only {SUPPORTED_CONTRACT_VERSION} is accepted"
            )

    def _validate(self, schema_id: str, document: Mapping[str, Any]) -> None:
        try:
            self._validator(schema_id).validate(document)
        except Unresolvable as exc:
            raise ContractValidationError(
                f"unknown or non-local schema reference: {exc}"
            ) from exc
        except (ValidationError, SchemaError) as exc:
            raise ContractValidationError(str(exc)) from exc
