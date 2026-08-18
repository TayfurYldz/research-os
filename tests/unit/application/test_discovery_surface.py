from __future__ import annotations

import unittest

import pathsetup  # noqa: F401

from research_os.application.discovery.claim import claim_frontier_selected
from research_os.application.discovery.compile_plan import ReobserveRequired, compile_frontier_plan
from research_os.application.discovery.config import (
    assert_runtime_matches_persisted,
    config_from_record,
    record_from_config,
)
from research_os.application.discovery.project import project_observation, reconcile_missing_projections
from research_os.application.discovery.runner import SurfaceDiscoveryRunner, SurfaceDiscoveryStart
from research_os.application.errors import ApplicationError, OrchestrationIntegrityError
from research_os.data.records import (
    FrontierEventRecord,
    FrontierItemRecord,
    ObservationRecord,
    WorkerResultRecord,
)
from research_os.research.discovery.config import DiscoveryBounds, DiscoveryRunConfig
from research_os.research.discovery.types import SURFACE_DISCOVERY_STRATEGY_VERSION
from research_os.tools.capabilities import HTTP_TRANSACTION_CAPABILITY
from support.fake_unit_of_work import FakeUnitOfWorkFactory, _Store
from support.recording_worker import RecordingWorkerPort
from support.spine import CREATED_AT, seed_authorization_run


def _bounds(**overrides) -> DiscoveryBounds:
    values = dict(
        max_discovery_cycles=8,
        max_frontier_items=32,
        max_new_facts_per_cycle=16,
        max_browser_actions=16,
        max_http_transactions=16,
        max_per_route_revisit=1,
        max_identity_variants=3,
        max_transition_depth=4,
        max_graph_depth_from_seed=8,
        max_template_inference_fanout=4,
        max_duplicate_observations=8,
    )
    values.update(overrides)
    return DiscoveryBounds(**values)


def _config(**overrides) -> DiscoveryRunConfig:
    values = dict(
        research_run_id="run-1",
        seed_target_reference="http://127.0.0.1:9/",
        normalized_origin="http://127.0.0.1:9",
        normalized_path="/",
        bounds=_bounds(),
    )
    values.update(overrides)
    return DiscoveryRunConfig(**values)


def _frontier(**overrides) -> FrontierItemRecord:
    values = dict(
        frontier_id="front-1",
        research_run_id="run-1",
        strategy_version=SURFACE_DISCOVERY_STRATEGY_VERSION,
        goal_kind="INSPECT_CONTROL",
        candidate_origin="http://127.0.0.1:9",
        candidate_path="/",
        identity_id="ANONYMOUS",
        proposed_capability="browser.page",
        proposed_action="interact",
        expected_side_effect=1,
        budget_class=1,
        structural_signature="sig-control",
        dedupe_identity="dedupe-control",
        created_at=CREATED_AT,
        attributes={"tag": "button", "name": "go", "role": "", "input_type": ""},
    )
    values.update(overrides)
    return FrontierItemRecord(**values)


class DiscoveryConfigTests(unittest.TestCase):
    def test_fingerprint_survives_reload(self) -> None:
        config = _config()
        record = record_from_config(config, created_at=CREATED_AT)
        loaded = config_from_record(record)
        self.assertEqual(config.fingerprint(), loaded.fingerprint())
        self.assertEqual(record.configuration_fingerprint, loaded.fingerprint())

    def test_widening_runtime_bounds_fail_closed(self) -> None:
        persisted = _config()
        wider = _config(bounds=_bounds(max_discovery_cycles=99))
        with self.assertRaises(OrchestrationIntegrityError):
            assert_runtime_matches_persisted(persisted, wider)


class CompilePlanTests(unittest.TestCase):
    def test_stale_control_does_not_click(self) -> None:
        with self.assertRaises(ReobserveRequired):
            compile_frontier_plan(
                _frontier(),
                hypothesis_id="hyp-1",
                budget_id="budget-1",
                target_reference="target-1",
                live_page=None,
            )

    def test_http_characterization_is_fresh_http_plan(self) -> None:
        plan = compile_frontier_plan(
            _frontier(
                goal_kind="CHARACTERIZE_HTTP_OPERATION",
                proposed_capability=HTTP_TRANSACTION_CAPABILITY,
                proposed_action="read",
                expected_side_effect=0,
                budget_class=0,
                attributes={"method": "GET", "auto_replay": False},
            ),
            hypothesis_id="hyp-1",
            budget_id="budget-1",
            target_reference="target-1",
        )
        self.assertEqual(plan.required_capability, HTTP_TRANSACTION_CAPABILITY)
        self.assertNotIn("auto_replay", plan.arguments)
        self.assertEqual(plan.arguments["path"], "/")


class ProjectionReceiptTests(unittest.TestCase):
    def test_missing_receipt_replays_without_worker(self) -> None:
        store = _Store()
        seed_authorization_run(store)
        store.worker_results["wr-1"] = WorkerResultRecord(
            worker_result_id="wr-1",
            experiment_id="exp-1",
            research_run_id="run-1",
            request_id="req-1",
            correlation_id="corr-1",
            worker_capability="browser.page",
            action="observe",
            authorization_decision_reference="authz-1",
            budget_id="budget-1",
            side_effect_level=0,
            contract_version="v1",
            worker_id="worker-1",
            status="SUCCEEDED",
            received_at=CREATED_AT,
        )
        store.observations["obs-1"] = ObservationRecord(
            observation_id="obs-1",
            worker_result_id="wr-1",
            observation_kind="BROWSER_PAGE_STATE",
            payload={
                "normalized_url": "http://127.0.0.1:9/",
                "path": "/",
                "snapshot_fingerprint": "fp-1",
                "browser_context_reference": "ctx-1",
                "page_reference": "page-1",
                "controls": [],
                "network_events": [],
            },
            normalization_version="browser.page.v1",
            observed_at=CREATED_AT,
            created_at=CREATED_AT,
        )
        factory = FakeUnitOfWorkFactory(store)
        worker = RecordingWorkerPort(store=store)
        with factory.open() as uow:
            projected = reconcile_missing_projections(
                uow, "run-1", created_at=CREATED_AT, target_reference="target-1"
            )
            uow.commit()
        self.assertEqual(projected, 1)
        self.assertEqual(len(store.discovery_projection_receipts), 1)
        self.assertGreaterEqual(len(store.discovery_facts), 1)
        self.assertEqual(len(worker.calls), 0)
        with factory.open() as uow:
            again = reconcile_missing_projections(
                uow, "run-1", created_at=CREATED_AT, target_reference="target-1"
            )
            uow.commit()
        self.assertEqual(again, 0)

    def test_duplicate_source_attaches_without_duplicate_fact(self) -> None:
        store = _Store()
        seed_authorization_run(store)
        factory = FakeUnitOfWorkFactory(store)
        payload = {
            "normalized_url": "http://127.0.0.1:9/",
            "path": "/",
            "snapshot_fingerprint": "fp-1",
            "browser_context_reference": "ctx-1",
            "page_reference": "page-1",
            "controls": [],
            "network_events": [],
        }
        for index, result_id in enumerate(("wr-1", "wr-2"), start=1):
            store.worker_results[result_id] = WorkerResultRecord(
                worker_result_id=result_id,
                experiment_id=f"exp-{index}",
                research_run_id="run-1",
                request_id=f"req-{index}",
                correlation_id=f"corr-{index}",
                worker_capability="browser.page",
                action="observe",
                authorization_decision_reference="authz-1",
                budget_id="budget-1",
                side_effect_level=0,
                contract_version="v1",
                worker_id="worker-1",
                status="SUCCEEDED",
                received_at=CREATED_AT,
            )
            store.observations[f"obs-{index}"] = ObservationRecord(
                observation_id=f"obs-{index}",
                worker_result_id=result_id,
                observation_kind="BROWSER_PAGE_STATE",
                payload=payload,
                normalization_version="browser.page.v1",
                observed_at=CREATED_AT,
                created_at=CREATED_AT,
            )
        with factory.open() as uow:
            project_observation(uow, store.observations["obs-1"], created_at=CREATED_AT)
            first = len(uow.discovery_facts.list_for_research_run("run-1"))
            project_observation(uow, store.observations["obs-2"], created_at=CREATED_AT)
            second = len(uow.discovery_facts.list_for_research_run("run-1"))
            sources = []
            for fact in uow.discovery_facts.list_for_research_run("run-1"):
                sources.extend(uow.discovery_fact_sources.list_for_fact(fact.fact_id))
            uow.commit()
        self.assertEqual(first, second)
        self.assertGreater(len(sources), first)


class FrontierClaimTests(unittest.TestCase):
    def test_concurrent_selected_generation_has_one_winner(self) -> None:
        store = _Store()
        seed_authorization_run(store)
        store.frontier_items["front-1"] = _frontier(
            goal_kind="INSPECT_PATH", expected_side_effect=0, budget_class=0
        )
        store.frontier_events["ev-1"] = FrontierEventRecord(
            event_id="ev-1",
            frontier_id="front-1",
            research_run_id="run-1",
            event_kind="CREATED",
            sequence=1,
            created_at=CREATED_AT,
        )
        store.frontier_events["ev-2"] = FrontierEventRecord(
            event_id="ev-2",
            frontier_id="front-1",
            research_run_id="run-1",
            event_kind="ELIGIBLE",
            sequence=2,
            created_at=CREATED_AT,
        )
        factory = FakeUnitOfWorkFactory(store)
        with factory.open() as uow:
            first = claim_frontier_selected(uow, "front-1", created_at=CREATED_AT)
            with self.assertRaises(ApplicationError):
                claim_frontier_selected(uow, "front-1", created_at=CREATED_AT)
            uow.commit()
        selected = [
            item for item in store.frontier_events.values() if item.event_kind == "SELECTED"
        ]
        self.assertEqual(len(selected), 1)
        self.assertEqual(first.selection_generation, 1)


class RunnerConfigTests(unittest.TestCase):
    def test_persisted_config_mismatch_fails_closed(self) -> None:
        store = _Store()
        seed_authorization_run(store)
        factory = FakeUnitOfWorkFactory(store)
        runner = SurfaceDiscoveryRunner(factory, RecordingWorkerPort(store=store))
        start = SurfaceDiscoveryStart(config=_config())
        runner.ensure_started(start)
        wider = SurfaceDiscoveryStart(config=_config(bounds=_bounds(max_http_transactions=99)))
        with self.assertRaises(OrchestrationIntegrityError):
            runner.ensure_started(wider)
        self.assertEqual(len(store.discovery_run_configs), 1)
