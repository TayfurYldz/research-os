"""Admit an OAST callback as an observation and then as a discovery fact.

The callback is out-of-band evidence. It enters the same deterministic admission
chain as any other sensor observation and is marked UNTRUSTED_EXTERNAL until
admitted. Stale (expired) callbacks are recorded but never admitted as evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from research_os.application.identity import new_opaque_id
from research_os.application.ports import UnitOfWorkFactory
from research_os.application.sensor.admit import (
    AdmitSensorObservations,
    SensorAdmissionError,
    SensorAdmissionResult,
)
from research_os.core.enums import ActorType
from research_os.data.records import AuditEventRecord, SensorObservationRecord
from research_os.research.oast.types import OastCallback
from research_os.research.sensor.types import build_observation


class OastCallbackAdmissionError(Exception):
    """Callback rejected from evidence admission."""


@dataclass(frozen=True)
class OastCallbackAdmissionResult:
    admitted: bool
    observation_id: str
    fact_id: str | None
    reason_code: str


def _default_clock() -> datetime:
    return datetime.now(timezone.utc)


class AdmitOastCallback:
    """Application-layer admission for OAST callbacks."""

    SENSOR_ID = "oast.loopback"

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock or _default_clock

    def execute(
        self,
        callback: OastCallback,
        *,
        scope_classification: str,
        identity_id: str = "ANONYMOUS",
        now: datetime | None = None,
    ) -> OastCallbackAdmissionResult:
        observed_at = now if now is not None else self._clock()

        with self._uow_factory.open() as uow:
            token_record = uow.oast_tokens.get(callback.token_id)

        if token_record is None:
            self._write_rejection_audit(
                callback,
                observed_at,
                "OAST_TOKEN_NOT_FOUND",
                {},
            )
            return OastCallbackAdmissionResult(
                admitted=False,
                observation_id="",
                fact_id=None,
                reason_code="OAST_TOKEN_NOT_FOUND",
            )

        if observed_at > token_record.expires_at:
            self._write_rejection_audit(
                callback,
                observed_at,
                "OAST_TOKEN_EXPIRED",
                {
                    "research_run_id": token_record.research_run_id,
                    "hypothesis_id": token_record.hypothesis_id,
                    "target_reference": token_record.target_reference,
                },
            )
            return OastCallbackAdmissionResult(
                admitted=False,
                observation_id="",
                fact_id=None,
                reason_code="OAST_TOKEN_EXPIRED",
            )

        observation_id = new_opaque_id()
        observation = build_observation(
            observation_id=observation_id,
            sensor_id=self.SENSOR_ID,
            target_reference=token_record.target_reference,
            research_run_id=token_record.research_run_id,
            payload={
                "callback_id": callback.callback_id,
                "source_address": callback.source_address,
                "request_summary": dict(callback.request_summary),
            },
            source_metadata={
                "sensor_id": self.SENSOR_ID,
                "token_id": callback.token_id,
                "hypothesis_id": token_record.hypothesis_id,
                "target_reference": token_record.target_reference,
            },
            collected_at=observed_at,
        )

        with self._uow_factory.open() as uow:
            uow.sensor_observations.insert(
                SensorObservationRecord(
                    observation_id=observation.observation_id,
                    research_run_id=observation.research_run_id,
                    sensor_id=observation.sensor_id,
                    target_reference=observation.target_reference,
                    collected_at=observation.collected_at,
                    payload_digest=observation.payload_digest,
                    epistemic_status=observation.epistemic_status.value,
                    source_metadata=dict(observation.source_metadata),
                    payload=dict(observation.payload),
                    created_at=observed_at,
                )
            )
            uow.commit()

        try:
            admission = AdmitSensorObservations(self._uow_factory).execute(
                observation,
                research_run_id=token_record.research_run_id,
                identity_id=identity_id,
                scope_classification=scope_classification,
            )
        except SensorAdmissionError as exc:
            self._write_rejection_audit(
                callback,
                observed_at,
                "OAST_ADMISSION_REJECTED",
                {
                    "research_run_id": token_record.research_run_id,
                    "hypothesis_id": token_record.hypothesis_id,
                    "target_reference": token_record.target_reference,
                    "detail": str(exc),
                },
            )
            return OastCallbackAdmissionResult(
                admitted=False,
                observation_id=observation_id,
                fact_id=None,
                reason_code="OAST_ADMISSION_REJECTED",
            )

        self._write_admission_audit(
            callback,
            observation,
            admission,
            observed_at,
            token_record.research_run_id,
        )
        return OastCallbackAdmissionResult(
            admitted=True,
            observation_id=observation_id,
            fact_id=admission.fact_id,
            reason_code="OAST_CALLBACK_ADMITTED",
        )

    def _write_rejection_audit(
        self,
        callback: OastCallback,
        occurred_at: datetime,
        reason_code: str,
        context: dict[str, Any],
    ) -> None:
        with self._uow_factory.open() as uow:
            uow.audit_events.insert(
                AuditEventRecord(
                    audit_event_id=new_opaque_id(),
                    occurred_at=occurred_at,
                    actor_id="control-plane:oast-admitter",
                    actor_type=ActorType.CONTROL_PLANE.value,
                    event_type="OAST_CALLBACK_REJECTED",
                    subject_type="OAST_CALLBACK",
                    subject_id=callback.callback_id,
                    correlation_id=callback.token_id,
                    payload={
                        "reason_code": reason_code,
                        "callback_id": callback.callback_id,
                        "token_id": callback.token_id,
                        "context": context,
                    },
                )
            )
            uow.commit()

    def _write_admission_audit(
        self,
        callback: OastCallback,
        observation: Any,
        admission: SensorAdmissionResult,
        occurred_at: datetime,
        research_run_id: str,
    ) -> None:
        with self._uow_factory.open() as uow:
            uow.audit_events.insert(
                AuditEventRecord(
                    audit_event_id=new_opaque_id(),
                    occurred_at=occurred_at,
                    actor_id="control-plane:oast-admitter",
                    actor_type=ActorType.CONTROL_PLANE.value,
                    event_type="OAST_CALLBACK_ADMITTED",
                    subject_type="OAST_CALLBACK",
                    subject_id=callback.callback_id,
                    correlation_id=callback.token_id,
                    payload={
                        "reason_code": "OAST_CALLBACK_ADMITTED",
                        "observation_id": observation.observation_id,
                        "fact_id": admission.fact_id,
                        "research_run_id": research_run_id,
                    },
                )
            )
            uow.commit()
