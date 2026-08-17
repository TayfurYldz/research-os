"""Load versioned security ground-truth scenarios. Hidden evaluation is not pipeline input."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from research_os.security_benchmark.types import ExpectedSecurityClass, PromotionStage

MANDATORY_SCENARIO_IDS = (
    "S01_TRUE_BOLA",
    "S02_SECURE_OBJECT_AUTHORIZATION",
    "S03_PUBLIC_OBJECT_LEGITIMATE_200",
    "S04_EXPLICIT_DELEGATED_ACCESS",
    "S05_DECEPTIVE_200_NO_OWNERSHIP_PROOF",
    "S06_SHARED_RESOURCE",
    "S07_CONTRADICTORY_VERIFICATION",
    "S08_OPERATIONAL_TIMEOUT",
    "S09_REDIRECT_BOUNDARY",
    "S10_OUT_OF_SCOPE",
)


@dataclass(frozen=True)
class ScenarioHarness:
    """Operator/harness configuration. Must not be copied into WorkerRequest."""

    fixture_kind: str
    actor: str
    own_object: str
    cross_object: str
    verification_actor: str | None = None
    verification_own_object: str | None = None
    verification_cross_object: str | None = None
    attempt_finding: bool = False
    human_decision: str | None = None
    target_reference: str | None = None
    in_scope: bool = True


@dataclass(frozen=True)
class HiddenEvaluation:
    expected_class: ExpectedSecurityClass
    expected_max_promotion_stage: PromotionStage
    security_violation: bool
    leakage_canary: str
    required_controls: tuple[str, ...]
    forbidden_promotions: tuple[str, ...]


@dataclass(frozen=True)
class SecurityGroundTruthScenario:
    scenario_id: str
    version: str
    harness: ScenarioHarness
    hidden_evaluation: HiddenEvaluation

    @property
    def identity(self) -> str:
        return f"{self.scenario_id}@{self.version}"


def load_scenario(path: Path) -> SecurityGroundTruthScenario:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path} must contain a JSON object")
    harness_raw = payload.get("harness")
    hidden_raw = payload.get("hidden_evaluation")
    if not isinstance(harness_raw, Mapping) or not isinstance(hidden_raw, Mapping):
        raise ValueError(f"{path} must split harness and hidden_evaluation")
    return SecurityGroundTruthScenario(
        scenario_id=_text(payload.get("scenario_id"), "scenario_id"),
        version=_text(payload.get("version"), "version"),
        harness=ScenarioHarness(
            fixture_kind=_text(harness_raw.get("fixture_kind"), "harness.fixture_kind"),
            actor=_text(harness_raw.get("actor"), "harness.actor"),
            own_object=_text(harness_raw.get("own_object"), "harness.own_object"),
            cross_object=_text(harness_raw.get("cross_object"), "harness.cross_object"),
            verification_actor=_optional_text(harness_raw.get("verification_actor")),
            verification_own_object=_optional_text(harness_raw.get("verification_own_object")),
            verification_cross_object=_optional_text(
                harness_raw.get("verification_cross_object")
            ),
            attempt_finding=bool(harness_raw.get("attempt_finding", False)),
            human_decision=_optional_text(harness_raw.get("human_decision")),
            target_reference=_optional_text(harness_raw.get("target_reference")),
            in_scope=bool(harness_raw.get("in_scope", True)),
        ),
        hidden_evaluation=HiddenEvaluation(
            expected_class=ExpectedSecurityClass(
                _text(hidden_raw.get("expected_class"), "hidden_evaluation.expected_class")
            ),
            expected_max_promotion_stage=PromotionStage(
                _text(
                    hidden_raw.get("expected_max_promotion_stage"),
                    "hidden_evaluation.expected_max_promotion_stage",
                )
            ),
            security_violation=bool(hidden_raw.get("security_violation")),
            leakage_canary=_text(
                hidden_raw.get("leakage_canary"), "hidden_evaluation.leakage_canary"
            ),
            required_controls=_texts(
                hidden_raw.get("required_controls", []), "required_controls"
            ),
            forbidden_promotions=_texts(
                hidden_raw.get("forbidden_promotions", []), "forbidden_promotions"
            ),
        ),
    )


def load_scenarios(directory: Path) -> tuple[SecurityGroundTruthScenario, ...]:
    paths = sorted(directory.glob("*.json"))
    scenarios = tuple(load_scenario(path) for path in paths)
    ids = tuple(item.scenario_id for item in scenarios)
    missing = [item for item in MANDATORY_SCENARIO_IDS if item not in ids]
    if missing:
        raise ValueError(f"missing mandatory security scenarios: {missing}")
    return scenarios


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError("optional text fields must be non-empty when present")
    return value.strip()


def _texts(value: object, field_name: str) -> tuple[str, ...]:
    if isinstance(value, tuple):
        value = list(value)
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list of strings")
    return tuple(_text(item, f"{field_name}[]") for item in value)
