"""Local operator dashboard. Read-only by default; never prints secrets."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import asdict
from datetime import date, datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

from sqlalchemy import text

from research_os.data.postgres.engine import (
    DATABASE_URL_ENV,
    TEST_DATABASE_URL_ENV,
    create_sync_engine,
    redacted_database_url,
)
from research_os.interface.cli import build_status_snapshot
from research_os.safe_data import redact_secret_keys


def collect_dashboard_payload(*, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    source = dict(os.environ if env is None else env)
    snapshot = build_status_snapshot(env=source)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": asdict(snapshot),
        "database": _database_payload(source),
        "git": _git_payload(),
        "oast": _oast_payload(source),
    }


def _database_payload(env: Mapping[str, str]) -> dict[str, Any]:
    url = env.get(DATABASE_URL_ENV)
    if not url:
        return {
            "state": "UNAVAILABLE",
            "dsn": "unset",
            "summary": {},
            "runs": [],
            "audit_events": [],
            "coverage": [],
            "queue": {},
            "error": "application database is not configured",
        }
    try:
        dsn = redacted_database_url(url)
    except Exception:
        dsn = "unparseable"
    engine = create_sync_engine(url)
    try:
        with engine.connect() as connection:
            summary = {
                "programs": _scalar(connection, "SELECT COUNT(*) FROM program"),
                "research_runs": _scalar(connection, "SELECT COUNT(*) FROM research_run"),
                "active_authorizations": _scalar(
                    connection,
                    "SELECT COUNT(*) FROM authorization_source WHERE state = 'ACTIVE'",
                ),
                "enabled_families": _scalar(
                    connection,
                    "SELECT COUNT(*) FROM hunter_family WHERE enabled = true",
                ),
                "pending_v3": _scalar(
                    connection,
                    "SELECT COUNT(*) FROM hunt_v3_queue WHERE state = 'PENDING'",
                ),
                "audit_events": _scalar(connection, "SELECT COUNT(*) FROM audit_event"),
            }
            runs = [
                _json_row(row)
                for row in connection.execute(
                    text(
                        """
                        SELECT r.research_run_id, r.program_id, r.started_at,
                               o.state, o.current_phase, o.cycle_number,
                               o.target_reference, o.updated_at
                        FROM research_run r
                        LEFT JOIN research_orchestration o
                          ON o.research_run_id = r.research_run_id
                        ORDER BY COALESCE(o.updated_at, r.started_at) DESC
                        LIMIT 8
                        """
                    )
                ).mappings()
            ]
            audit_events = [
                _json_row(row, redact_payload=True)
                for row in connection.execute(
                    text(
                        """
                        SELECT occurred_at, event_type, subject_type, subject_id,
                               correlation_id, payload
                        FROM audit_event
                        ORDER BY occurred_at DESC
                        LIMIT 40
                        """
                    )
                ).mappings()
            ]
            coverage = [
                _json_row(row, redact_payload=True)
                for row in connection.execute(
                    text(
                        """
                        SELECT research_run_id, total_debt, matrix_hash,
                               cell_counts, created_at
                        FROM coverage_debt_snapshot
                        ORDER BY created_at DESC
                        LIMIT 6
                        """
                    )
                ).mappings()
            ]
            queue = {
                str(row["state"]): int(row["count"])
                for row in connection.execute(
                    text(
                        """
                        SELECT state, COUNT(*) AS count
                        FROM hunt_v3_queue
                        GROUP BY state
                        ORDER BY state
                        """
                    )
                ).mappings()
            }
        return {
            "state": "HEALTHY",
            "dsn": dsn,
            "summary": summary,
            "runs": runs,
            "audit_events": audit_events,
            "coverage": coverage,
            "queue": queue,
            "error": None,
        }
    except Exception as exc:
        return {
            "state": "UNAVAILABLE",
            "dsn": dsn,
            "summary": {},
            "runs": [],
            "audit_events": [],
            "coverage": [],
            "queue": {},
            "error": exc.__class__.__name__,
        }
    finally:
        engine.dispose()


def _oast_payload(env: Mapping[str, str]) -> dict[str, Any]:
    configured = bool(env.get("RESEARCH_OS_INTERACTSH_SERVER") or env.get("INTERACTSH_SERVER"))
    return {
        "mode": "INTERACTSH_CONFIGURED" if configured else "LOOPBACK_CORE_ONLY",
        "adapter": "not implemented" if configured else "loopback",
        "live_ready": False,
    }


def _git_payload() -> dict[str, str | None]:
    root = Path(__file__).resolve().parents[3]

    def run(args: list[str]) -> str | None:
        try:
            return subprocess.check_output(
                ["git", *args],
                cwd=root,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=2,
            ).strip()
        except Exception:
            return None

    return {
        "branch": run(["rev-parse", "--abbrev-ref", "HEAD"]),
        "head": run(["rev-parse", "--short", "HEAD"]),
        "status": run(["status", "-sb"]),
    }


def _scalar(connection: Any, statement: str) -> int:
    value = connection.execute(text(statement)).scalar()
    return int(value or 0)


def _json_row(row: Mapping[str, Any], *, redact_payload: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in row.items():
        if key == "payload" and redact_payload:
            value = redact_secret_keys(value, "payload")
        result[str(key)] = _json_value(value)
    return result


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "ResearchOSDashboard/1.0"

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self._send(HTTPStatus.OK, HTML, "text/html; charset=utf-8")
            return
        if path == "/api/dashboard":
            self._send_json(collect_dashboard_payload())
            return
        if path == "/healthz":
            self._send_json({"ok": True})
            return
        self._send(HTTPStatus.NOT_FOUND, b"not found", "text/plain; charset=utf-8")

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def _send_json(self, value: Mapping[str, Any]) -> None:
        body = json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self._send(HTTPStatus.OK, body, "application/json; charset=utf-8")

    def _send(self, status: HTTPStatus, body: str | bytes, content_type: str) -> None:
        payload = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(status.value)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="research-os-dashboard")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    print(f"Research OS dashboard listening on http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 130
    finally:
        server.server_close()
    return 0


HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Research OS Dashboard</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f5f6f4;
      --panel: #ffffff;
      --line: #d9ddd7;
      --text: #222825;
      --muted: #69726d;
      --soft: #eef1ed;
      --ok: #12805c;
      --warn: #a66b00;
      --bad: #b42318;
      --info: #2f6f7e;
      --ink: #151918;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 14px;
      line-height: 1.4;
      letter-spacing: 0;
    }
    button, input, select {
      font: inherit;
    }
    .shell {
      min-height: 100vh;
      display: grid;
      grid-template-columns: 248px minmax(0, 1fr);
    }
    .rail {
      border-right: 1px solid var(--line);
      background: #fbfcfa;
      padding: 18px 14px;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 22px;
      font-weight: 750;
      color: var(--ink);
    }
    .mark {
      width: 28px;
      height: 28px;
      border: 1px solid #27312d;
      display: grid;
      place-items: center;
      font-size: 13px;
      font-weight: 800;
      background: #202724;
      color: white;
      border-radius: 6px;
    }
    .nav {
      display: grid;
      gap: 6px;
    }
    .nav button {
      width: 100%;
      height: 34px;
      border: 0;
      border-radius: 6px;
      background: transparent;
      color: var(--muted);
      text-align: left;
      padding: 0 10px;
      font-weight: 650;
      cursor: pointer;
    }
    .nav button.active,
    .nav button:hover {
      background: var(--soft);
      color: var(--ink);
    }
    .railBlock {
      border-top: 1px solid var(--line);
      margin-top: 18px;
      padding-top: 14px;
      display: grid;
      gap: 8px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 650;
    }
    main {
      min-width: 0;
      padding: 18px 22px 26px;
    }
    .topbar {
      height: 42px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 14px;
    }
    .title {
      font-size: 18px;
      font-weight: 800;
      color: var(--ink);
    }
    .actions {
      display: flex;
      align-items: center;
      gap: 10px;
      color: var(--muted);
      font-weight: 650;
      font-size: 12px;
    }
    .iconButton {
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 6px;
      width: 34px;
      height: 34px;
      cursor: pointer;
      color: var(--ink);
      font-weight: 800;
    }
    .grid {
      display: grid;
      gap: 14px;
    }
    .metrics {
      grid-template-columns: repeat(6, minmax(130px, 1fr));
    }
    .columns {
      grid-template-columns: minmax(0, 1.1fr) minmax(360px, .9fr);
      align-items: start;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }
    .panelHead {
      height: 40px;
      padding: 0 12px;
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      font-weight: 780;
      color: var(--ink);
    }
    .panelBody { padding: 12px; }
    .metric {
      padding: 12px;
      min-height: 82px;
      display: grid;
      gap: 8px;
    }
    .metric .label {
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
    }
    .metric .value {
      color: var(--ink);
      font-size: 22px;
      font-weight: 820;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .metric .sub {
      color: var(--muted);
      font-size: 12px;
      font-weight: 650;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .statusRow {
      display: grid;
      grid-template-columns: 1fr auto;
      align-items: center;
      min-height: 34px;
      border-bottom: 1px solid var(--soft);
      gap: 12px;
    }
    .statusRow:last-child { border-bottom: 0; }
    .name {
      min-width: 0;
      font-weight: 700;
      color: var(--text);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      height: 22px;
      border-radius: 999px;
      border: 1px solid var(--line);
      padding: 0 8px;
      font-size: 11px;
      font-weight: 780;
      color: var(--muted);
      background: #fff;
      white-space: nowrap;
    }
    .dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: var(--muted);
    }
    .ok .dot { background: var(--ok); }
    .ok { color: var(--ok); border-color: #b9d8c9; background: #f3faf6; }
    .warn .dot { background: var(--warn); }
    .warn { color: var(--warn); border-color: #e7cf9e; background: #fff9ea; }
    .bad .dot { background: var(--bad); }
    .bad { color: var(--bad); border-color: #efbbb6; background: #fff5f3; }
    .info .dot { background: var(--info); }
    .info { color: var(--info); border-color: #b8d5dc; background: #f0f8fa; }
    table {
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
    }
    th, td {
      padding: 9px 8px;
      border-bottom: 1px solid var(--soft);
      text-align: left;
      vertical-align: top;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    th {
      color: var(--muted);
      font-size: 11px;
      font-weight: 800;
      text-transform: uppercase;
    }
    td {
      color: var(--text);
      font-weight: 620;
      font-size: 13px;
    }
    tr:last-child td { border-bottom: 0; }
    .log {
      display: grid;
      gap: 8px;
      max-height: 520px;
      overflow: auto;
      padding-right: 4px;
    }
    .event {
      border-left: 3px solid var(--line);
      padding: 2px 0 8px 10px;
      display: grid;
      gap: 3px;
    }
    .event strong {
      font-size: 13px;
      color: var(--ink);
    }
    .event span {
      color: var(--muted);
      font-size: 12px;
      font-weight: 650;
    }
    .mono {
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
    }
    .empty {
      color: var(--muted);
      font-weight: 650;
      padding: 14px 0;
    }
    @media (max-width: 1120px) {
      .shell { grid-template-columns: 1fr; }
      .rail { display: none; }
      .metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .columns { grid-template-columns: 1fr; }
      main { padding: 14px; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <aside class="rail">
      <div class="brand"><div class="mark">RO</div><div>Research OS</div></div>
      <div class="nav">
        <button class="active">Operations</button>
        <button>Runs</button>
        <button>Coverage</button>
        <button>Approvals</button>
        <button>OAST</button>
        <button>Audit</button>
      </div>
      <div class="railBlock">
        <div id="gitBranch">branch: -</div>
        <div id="gitHead">head: -</div>
      </div>
    </aside>
    <main>
      <div class="topbar">
        <div class="title">Security Operations</div>
        <div class="actions">
          <span id="updated">waiting</span>
          <button class="iconButton" id="refresh" title="Refresh">R</button>
        </div>
      </div>

      <section class="grid metrics">
        <div class="panel metric"><div class="label">PostgreSQL</div><div class="value" id="metricDb">-</div><div class="sub" id="metricDsn">-</div></div>
        <div class="panel metric"><div class="label">Runs</div><div class="value" id="metricRuns">0</div><div class="sub" id="metricOrch">-</div></div>
        <div class="panel metric"><div class="label">Pending V3</div><div class="value" id="metricV3">0</div><div class="sub">approval queue</div></div>
        <div class="panel metric"><div class="label">Coverage Debt</div><div class="value" id="metricDebt">-</div><div class="sub" id="metricCoverage">latest snapshot</div></div>
        <div class="panel metric"><div class="label">Worker</div><div class="value" id="metricWorker">-</div><div class="sub">local python</div></div>
        <div class="panel metric"><div class="label">OAST</div><div class="value" id="metricOast">-</div><div class="sub" id="metricOastSub">-</div></div>
      </section>

      <section class="grid columns" style="margin-top:14px">
        <div class="grid">
          <div class="panel">
            <div class="panelHead"><span>System</span><span class="pill info"><span class="dot"></span><span id="maturity">maturity</span></span></div>
            <div class="panelBody" id="systemRows"></div>
          </div>
          <div class="panel">
            <div class="panelHead"><span>Research Runs</span><span class="pill" id="runCount">0</span></div>
            <div class="panelBody">
              <table>
                <thead><tr><th>Run</th><th>Program</th><th>State</th><th>Phase</th><th>Updated</th></tr></thead>
                <tbody id="runs"></tbody>
              </table>
            </div>
          </div>
          <div class="panel">
            <div class="panelHead"><span>Coverage</span><span class="pill" id="coverageCount">0</span></div>
            <div class="panelBody">
              <table>
                <thead><tr><th>Run</th><th>Total Debt</th><th>Matrix</th><th>Created</th></tr></thead>
                <tbody id="coverage"></tbody>
              </table>
            </div>
          </div>
        </div>
        <div class="grid">
          <div class="panel">
            <div class="panelHead"><span>Gates</span><span class="pill ok"><span class="dot"></span>SD sealed</span></div>
            <div class="panelBody" id="gates"></div>
          </div>
          <div class="panel">
            <div class="panelHead"><span>Audit Tail</span><span class="pill" id="auditCount">0</span></div>
            <div class="panelBody"><div class="log" id="audit"></div></div>
          </div>
        </div>
      </section>
    </main>
  </div>
  <script>
    const $ = (id) => document.getElementById(id);
    const cls = (value) => {
      const text = String(value || '').toLowerCase();
      if (text.includes('healthy') || text === 'pass' || text === 'true' || text.includes('ready')) return 'ok';
      if (text.includes('pending') || text.includes('not_implemented') || text.includes('loopback')) return 'warn';
      if (text.includes('unavailable') || text.includes('false') || text.includes('failed')) return 'bad';
      return 'info';
    };
    const pill = (value) => `<span class="pill ${cls(value)}"><span class="dot"></span>${escapeHtml(value ?? '-')}</span>`;
    const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
    const short = (value, n = 12) => {
      const text = String(value || '-');
      return text.length > n ? text.slice(0, n) : text;
    };
    const time = (value) => value ? new Date(value).toLocaleString() : '-';

    async function load() {
      const response = await fetch('/api/dashboard', { cache: 'no-store' });
      const data = await response.json();
      render(data);
    }

    function render(data) {
      const status = data.status || {};
      const db = data.database || {};
      const summary = db.summary || {};
      const latestCoverage = (db.coverage || [])[0] || {};
      $('updated').textContent = time(data.generated_at);
      $('gitBranch').textContent = `branch: ${(data.git || {}).branch || '-'}`;
      $('gitHead').textContent = `head: ${(data.git || {}).head || '-'}`;

      $('metricDb').textContent = status.postgresql || '-';
      $('metricDsn').textContent = status.application_dsn || db.dsn || '-';
      $('metricRuns').textContent = summary.research_runs ?? 0;
      $('metricOrch').textContent = status.orchestrator || '-';
      $('metricV3').textContent = summary.pending_v3 ?? 0;
      $('metricDebt').textContent = latestCoverage.total_debt ?? '-';
      $('metricCoverage').textContent = latestCoverage.research_run_id || 'latest snapshot';
      $('metricWorker').textContent = Object.values(status.worker || {})[0] || '-';
      $('metricOast').textContent = (data.oast || {}).mode || '-';
      $('metricOastSub').textContent = (data.oast || {}).adapter || '-';
      $('maturity').textContent = status.gate_16 === 'PASS' ? 'SD-G16 PASS' : 'check';

      const system = [
        ['Application DB', status.postgresql],
        ['Test DB', status.test_postgresql],
        ['Model API', (status.model_runtimes || {}).API],
        ['CLI Session', (status.model_runtimes || {}).CLI_SESSION],
        ['Local Model', (status.model_runtimes || {}).LOCAL_MODEL],
        ['Strix', status.strix],
        ['Budget', status.budget_ledger],
        ['OAST Adapter', (data.oast || {}).adapter],
      ];
      $('systemRows').innerHTML = system.map(([name, value]) => `<div class="statusRow"><div class="name">${escapeHtml(name)}</div>${pill(value)}</div>`).join('');

      const gates = [
        ['GATE 01', status.gate_01], ['GATE 04B', status.gate_04b], ['GATE 10', status.gate_10],
        ['GATE 14', status.gate_14], ['GATE 15', status.gate_15], ['GATE 16', status.gate_16],
        ['GATE 17', status.gate_17], ['GATE 18', status.gate_18], ['GATE 19', status.gate_19],
        ['GATE 20', status.gate_20], ['GATE 21', status.gate_21], ['GATE 22', status.gate_22],
      ];
      $('gates').innerHTML = gates.map(([name, value]) => `<div class="statusRow"><div class="name">${escapeHtml(name)}</div>${pill(value)}</div>`).join('');

      const runs = db.runs || [];
      $('runCount').textContent = runs.length;
      $('runs').innerHTML = runs.length ? runs.map(row => `
        <tr>
          <td class="mono" title="${escapeHtml(row.research_run_id)}">${escapeHtml(short(row.research_run_id, 18))}</td>
          <td>${escapeHtml(row.program_id)}</td>
          <td>${pill(row.state || 'not started')}</td>
          <td>${escapeHtml(row.current_phase || '-')}</td>
          <td>${escapeHtml(time(row.updated_at || row.started_at))}</td>
        </tr>`).join('') : `<tr><td colspan="5" class="empty">No research runs</td></tr>`;

      const coverage = db.coverage || [];
      $('coverageCount').textContent = coverage.length;
      $('coverage').innerHTML = coverage.length ? coverage.map(row => `
        <tr>
          <td class="mono">${escapeHtml(short(row.research_run_id, 18))}</td>
          <td>${escapeHtml(row.total_debt)}</td>
          <td class="mono" title="${escapeHtml(row.matrix_hash)}">${escapeHtml(short(row.matrix_hash, 16))}</td>
          <td>${escapeHtml(time(row.created_at))}</td>
        </tr>`).join('') : `<tr><td colspan="4" class="empty">No coverage snapshots</td></tr>`;

      const audit = db.audit_events || [];
      $('auditCount').textContent = audit.length;
      $('audit').innerHTML = audit.length ? audit.map(row => `
        <div class="event">
          <strong>${escapeHtml(row.event_type)}</strong>
          <span>${escapeHtml(row.subject_type)} · ${escapeHtml(short(row.subject_id, 24))}</span>
          <span>${escapeHtml(time(row.occurred_at))}</span>
        </div>`).join('') : `<div class="empty">No audit events</div>`;
    }

    $('refresh').addEventListener('click', load);
    load().catch(err => { $('updated').textContent = `error: ${err.message}`; });
    setInterval(() => load().catch(() => {}), 3000);
  </script>
</body>
</html>"""


if __name__ == "__main__":
    raise SystemExit(main())
