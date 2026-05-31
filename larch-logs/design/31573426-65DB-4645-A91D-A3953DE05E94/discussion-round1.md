# Design Discussion — Round 1 (scope & requirements)

Issue #3237 — ship-pr → Python **Phase 4: Local checks & fixer loop**.
Resolved via Step 1c clarifying questions (user-engaged). These are **binding** scope/constraints for the plan.

## Decision 1: Fixer-dispatch port depth
- **Question**: How much of `lint-fix-loop.sh`'s single-dispatch mechanics should `checks.py` port now?
- **Resolution**: **FULL local-fixer port this phase.** Port prompt composition, the codex→cursor→main-agent dispatch (via the `agents.py` waterfall seam), forbidden-path reversion, and **auto-commit of the fix**, in addition to the checks runner and the capped loop. No deferred local-checks-fixer surface.
- **Source**: user

## Decision 2: Parity-test form
- **Question**: What does "Parity vs lint-fix-loop.sh for the fix-attempt accounting" concretely require?
- **Resolution**: **Semantic, Python-only parity.** Unit tests assert the Python loop's accounting (iteration count; `applied`/`no-changes`/`main-agent-required`/`failed` transitions; cap clamp 1–6, default 3; empty-failure→`exhausted`; `no-changes-stale`; escalation) against the documented bash semantics, using a stub checks runner + stub fixer/waterfall. **No bash executed inside tests.**
- **Source**: user

## Decision 3: Loop patterns in scope
- **Question**: Port only check-first (`run_checks_phase` / local checks), or also dispatch-first (CI per-job)?
- **Resolution**: **BOTH loop shapes** — mirror `run_captured_cmd_then_fix_loop`'s dual-mode behavior, including `no-changes-stale` on the dispatch-first path.
- **Source**: user

## Decision 4: Escalation mapping (the "gap to fold in")
- **Question**: How do terminal loop conditions map to `outcomes.py` `Outcome` values?
- **Resolution**: **Three-way mapping** — `exhausted` (cap hit) + `no-changes-stale` → `STALLED`; `main-agent-required` (no external coder available / fixer declines UNFIXABLE) → `NEEDS_USER_INPUT`; `dispatch-failed` + `head-changed` (infra) → `TRANSIENT`. `ok` → `OK`.
- **Source**: user

## Decision 5: Strangler-fig boundary (additive only)
- **Question**: Does Phase 4 change the live `/implement` path?
- **Resolution**: **No.** `checks.py` is additive (dev/CI-only). The live path keeps using `ship-pr.sh` / `lint-fix-loop.sh` / `run-relevant-checks-captured.sh`; those `.sh` are **NOT deleted** (quality bar: don't delete a shared `.sh` until caller-grep is zero). No `LARCH_SHIP_PR_IMPL` cutover until Phase 7.
- **Source**: codebase / issue (#3132 locked decisions, AGENTS.md)

## Decision 6: CI-orchestration boundary
- **Question**: Does "both patterns" include the full CI fix orchestration (gh-log fetch, per-job iteration, `run_ci_fix_vendor`)?
- **Resolution**: **No.** Phase 4 ports the local checks runner, the local fixer dispatch, and the dual-mode loop **primitive** + escalation. CI-specific orchestration (gh-logs capture, per-job verification, vendor staging, rebase) stays **out of scope** for a later CI phase. *(Confirm at the Step 1d.7 outline-approval gate.)*
- **Source**: codebase / issue (phase boundaries)
