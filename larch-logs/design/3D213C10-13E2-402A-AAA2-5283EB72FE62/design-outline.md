## Proposed Design Outline

### Goals
- Bound the worst-case hang when an installed Codex/Cursor binary is unhealthy at launch time, instead of waiting the full 20-30 min `--timeout`.
- Reuse the existing `check-reviewers.sh` probe and its per-tool stamp cache; add no parallel probe logic.
- Stay on by default in production; keep every current test and CI job green.

### Non-goals
- No generic no-output stall watchdog in `run-external-agent.sh` (Cursor buffers stdout to 0 bytes until exit).
- No sub-cache-TTL mid-run detection (a tool degrading inside the freshness window is caught on the next launch past TTL).
- No wiring of the `python/` ship-pr rework into the live `/implement` path (stays dev/CI-only until Phase 7).

### Approach sketch
- Add a launch-time health gate at the shared chokepoint `run-external-agent.sh`, gated by a new `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT`.
- The gate consults the per-tool stamp cache; trusts a fresh+healthy verdict, skips on a fresh+unhealthy verdict, and re-probes (bounded) only when the stamp is stale.
- On unhealthy, skip the real launch and emit a health-class failure so the existing waterfall degrades to Claude.
- Audit `plan-review-loop.sh` and the launcher libs for parity; mirror the env var + a parity assertion in the `python/` tree.

### Surfaces in scope
- `scripts/run-external-agent.sh`, `scripts/check-reviewers.sh`, `scripts/lib-external-launcher-common.sh`, `scripts/lib-cursor-launcher-common.sh`, `scripts/lib-codex-launcher-common.sh`
- `skills/design/scripts/plan-review-loop.sh`
- `python/config.py`, `python/checks.py`/`python/agents.py`, `python/test_checks_bash_parity.py`
- `docs/configuration-and-permissions.md`; `SECURITY.md` if security-relevant

### Open questions
- Exact default timeout value and the precise test/CI disable signal — settle in the plan.
