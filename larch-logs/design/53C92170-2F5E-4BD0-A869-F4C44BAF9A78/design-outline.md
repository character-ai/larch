## Proposed Design Outline

### Goals
- Land soak-proven canonical fixes so the Python ship path (`LARCH_SHIP_PR_IMPL=python`) runs reliably: PR-create (#3), merge convergence (#7), error→JSON contract (#4), OID-poll (#5).
- Add stderr progress breadcrumbs (#6), make the Step-0 bash helper `set -e`-safe (#1), and cover the blockers with regression tests; keep `make py-lint`/`py-test`/`lint` green.
- Apply the two operator-chosen scope expansions: lower the runtime Python floor to 3.11 (Decision 1) and re-architect post-PR flushes to avoid divergence at the root (Decision 2 / O1).

### Non-goals
- `#3446` (consume-JSON routing), `#3448` (counter resets), `#3449` (CI-fix push gate) — tracked separately; do not touch.
- No broad rewrite of bash `ship-pr.sh` beyond the #1 `set -e` fix; no new ship features beyond the soak findings.

### Approach sketch
- `python/gh.py` `pr_create`: drop the unsupported `--json`; resolve via `pr_for_branch(...)` + `gh pr view --json` fallback. Add a real-CLI/recorded-fixture test that catches unsupported flags.
- `python/ship.py` `_error_to_result`: map `ShipError`/operational errors → `Outcome.STALLED` (exit 4) with `detail`; always emit JSON, never a bare traceback.
- `python/merge.py`: poll PR head OID after force-push (#5); drop per-attempt `flush_logs_pre`, converge on the green head (#7).
- `python/run_logs.py` flush: avoid creating a divergent commit after PR creation — fast-forward post-PR flush and/or defer final logs to post-merge (O1).
- `scripts/parse-bootstrap-routing-envelope.sh` `_inv_apply_*` helpers made `set -e`-safe (#1); breadcrumbs stream to stderr, stdout stays JSON-only (#6).
- 3.11 floor: update docs, add a 3.11/3.12 CI matrix, audit `python/` for 3.11 compliance, and validate `python3 ≥ 3.11` in the selector (#2).

### Surfaces in scope
- `python/gh.py`, `python/ship.py`, `python/merge.py`, `python/run_logs.py`, `python/test_*.py`
- `scripts/parse-bootstrap-routing-envelope.sh`, `skills/implement/SKILL.md` (interpreter selector)
- `python/README.md`, `docs/installation-and-setup.md`, `.github/workflows/ci.yaml`, `Makefile`

### Open questions
- O1 mechanism: fast-forward post-PR flush vs. defer-logs-to-post-merge — settled in the plan + review panel (no sketches on SIMPLE).
