## Proposed Design Outline

### Goals
- Reduce Step 0 health check to a user-safety gate only: warn + confirm when one vendor is down; hard-fail when both are down.
- Remove probe-based health globals (`CODEX_AVAILABLE`, `CURSOR_AVAILABLE`, `CODEX_PRESENT`, `CURSOR_PRESENT`) from session-env and all caller decisions.
- Eliminate the per-launch `_external_health_gate` pre-call check; callers rely on binary presence and the existing waterfall.

### Non-goals
- Do not change probe retry counts or probe command logic.
- Do not change waterfall/fallback behavior at dispatch sites.
- Do not add new retry mechanisms at caller sites.

### Approach sketch
- `agents.py`: Remove `_external_health_gate` + its call in `run_external_agent`; stop emitting `CODEX_AVAILABLE`/`CURSOR_AVAILABLE` from `CheckReviewersResult.kv()`; update `degraded_tools_gate_main` to emit a hard-fail signal when both are down (no prompt path).
- `session_env.py`: Remove `CODEX_AVAILABLE`, `CURSOR_AVAILABLE`, `CODEX_PRESENT`, `CURSOR_PRESENT` from `WRITE_ENV_KEYS` and `WRITE_DESIGN_ENV_KEYS`; keep `CODEX_BINARY_FOUND`/`CURSOR_BINARY_FOUND`.
- `bootstrap.py`: Replace `codex_available`/`cursor_available` with `codex_binary_found`/`cursor_binary_found` throughout coder-selection and emit paths.
- Shell dispatchers (`dispatch-panel.sh`, `dispatch-code-voters.sh`, `dispatch-with-waterfall.sh`): Pass `CODEX_BINARY_FOUND`/`CURSOR_BINARY_FOUND` values instead of `CODEX_AVAILABLE`/`CURSOR_PRESENT` to waterfall flags.
- `review_and_fix.py`, `oos_filer.py`: Switch availability checks to binary-found env vars.
- `skills/design/SKILL.md`: Update degraded-tools-gate description for both-down hard-fail (no AskUserQuestion).
- Tests: Update `test_agents.py`, `test_session_env.py`, `test_bootstrap.py`, `test_review_and_fix.py`, `test_oos_filer.py` to remove health-gate tests and probe-global assertions.

### Surfaces in scope
- `python/agents.py`, `python/session_env.py`, `python/bootstrap.py`
- `python/review_and_fix.py`, `python/oos_filer.py`, `python/implement_dispatch.py`
- `scripts/dispatch-with-waterfall.sh`, `scripts/dispatch-code-voters.sh`
- `python/legacy_review_shell/dispatch-panel.sh`
- `python/test_agents.py`, `python/test_session_env.py`, `python/test_bootstrap.py`
- `python/test_review_and_fix.py`, `python/test_oos_filer.py`
- `skills/design/SKILL.md` (both-down gate description)

### Open questions
- Does the `/implement` bootstrap hard-fail path (design-step0-session.sh) also need updating for both-down → no-prompt? (Likely yes — the session wrapper reads `BOTH_DOWN` and `STEP0_STATUS`.)
