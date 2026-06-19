## Proposed Design Outline

### Goals
- Fix the four confirmed defects: opt-in probe-timeout retry, bounded voter-diagnostic reads, Cursor keychain mutex, plan-review panel-failure stderr redaction.
- Verify items 4/6/7 against the tree (pin or drop with evidence); align implement/review failure-diagnostic source selection.
- Add pytest coverage (items 8, 9) and sync docs (item 5); preserve all current defaults and diagnostic contracts.

### Non-goals
- No change to default probe latency or default probe behavior.
- No partition of the 10-item bundle.
- No edits to retired Bash launcher surfaces (e.g. `scripts/lib-cursor-auth.sh`).

### Approach sketch
- Item 1: add `LARCH_PROBE_TIMEOUT_RETRIES` (default 0) in `python/agents.py`; retry `EXIT_TIMEOUT` in `_run_codex_probes`/`_run_cursor_probes`; keep auth and transient retry budgets independent.
- Item 2: bounded-prefix reads (`open` + `read(N)`) in `agent_voters.py` and `voting.py`; drop whole-file `read_bytes()[:N]`.
- Item 3: wrap Darwin Cursor keychain preflight/preread in the shared external-startup mutex; skip when `CURSOR_API_KEY` is set.
- Item 10: route waterfall `proc.stderr` through `redact.redact` before the failure-log write and stderr re-surface; preserve the #4747 log shape and KV.
- Items 4/6/7 verified then pinned or dropped; items 8/9 add focused tests; item 5 lightweight docs sync.

### Surfaces in scope
- Python: `agents.py`, `agent_voters.py`, `voting.py`, `collect_results.py`, `plan_review_panel.py`.
- Tests: `test_agents.py`, `test_agent_voters.py`, `test_voting.py`, `test_collect_results.py`, `test_plan_review_panel.py`, `test_design_lifecycle.py`, `test_design_cli_ports.py`.
- Docs: `docs/external-reviewers.md`, `docs/configuration-and-permissions.md`, `SECURITY.md`.

### Open questions
- Item 4: likely drop (research-phase.md already keys on binary presence with per-lane fallback); confirm at drafting.
- Items 6/7/10: cited line numbers may have drifted post-#4765; navigate by symbol.
