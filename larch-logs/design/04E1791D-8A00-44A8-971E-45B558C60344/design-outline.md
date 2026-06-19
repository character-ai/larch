## Proposed Design Outline

### Goals
- Fix the four confirmed external-tool defects: probe-timeout retry (Item 1), bounded diagnostic reads (Item 2), Cursor keychain mutex (Item 3), panel-stderr redaction (Item 10).
- Align failure-diagnostic source selection and stderr-tail resolution (Items 6, 7) only where a concrete gap remains; add the missing pytest coverage (Items 8, 9).
- Sync the external-reviewer and degraded-tools docs (Item 5).

### Non-goals
- No change to default probe behavior or health-gate latency. The new timeout-retry budget defaults to 0.
- No edits to retired Bash launcher surfaces (`scripts/lib-cursor-auth.sh` and peers).
- No `/research` rework unless Item 4 confirms a concrete per-lane routing gap; otherwise drop with recorded evidence.

### Approach sketch
- `python/agents.py`: add `LARCH_PROBE_TIMEOUT_RETRIES` parsing (default 0); give `_run_codex_probes` / `_run_cursor_probes` an independent timeout retry budget; wrap Darwin Cursor keychain reads in the external-startup lock; route implement/review failure paths through `resolve_failure_diagnostic_source`.
- `python/agent_voters.py` + `python/voting.py`: replace whole-file `read_bytes()[:N]` with a bounded prefix read; preserve the 200/200/500 byte caps.
- `python/collect_results.py`: extend `resolve_collector_stderr_tail_file` phase / NS-retry / `.launch-stderr` candidates only where a real gap remains.
- `python/plan_review_panel.py`: redact `proc.stderr` before the waterfall-failure log write and stderr re-surface.
- Add focused pytest coverage in the matching `test_*.py`; sync `docs/external-reviewers.md`, `docs/configuration-and-permissions.md`, `SECURITY.md`.

### Surfaces in scope
- Code: `python/agents.py`, `python/agent_voters.py`, `python/voting.py`, `python/collect_results.py`, `python/plan_review_panel.py`
- Tests: `python/test_agents.py`, `python/test_agent_voters.py`, `python/test_voting.py`, `python/test_collect_results.py`, `python/test_plan_review_panel.py`, `python/test_design_lifecycle.py`, `python/test_design_cli_ports.py`
- Docs: `docs/external-reviewers.md`, `docs/configuration-and-permissions.md`, `SECURITY.md`

### Open questions
- Items 4, 6, 7 may close as no-defect after drafting-time inspection; the plan will pin a concrete gap or record evidence and drop.
