## Proposed Design Outline

### Goals
- Create `python/checks.py`: a parity-faithful port of the local "Lint and Tests" step — run the consumer's checks, parse into a typed record, drive a capped fixer loop with explicit escalation.
- Port the **full** local fixer (prompt compose + codex→cursor→main-agent waterfall via `agents.py` + forbidden-path reversion + auto-commit) and **both** loop shapes (check-first + dispatch-first).
- Fold in the "gap": map terminal loop states to `outcomes.Outcome` (three-way), returning a typed `StepResult`.

### Non-goals
- No change to the live `/implement` path; do **not** delete `lint-fix-loop.sh` / `run-relevant-checks-captured.sh` (strangler-fig; cutover is Phase 7).
- No CI-fix orchestration (gh-log fetch, per-job iteration, `run_ci_fix_vendor`, rebase) — that is a later CI phase.
- No executable bash golden-diff test; parity is asserted semantically in Python.

### Approach sketch
- `checks.py` mirrors `run-relevant-checks-captured.sh`: shell out to `scripts/relevant-checks.sh`, capture+redact, parse → frozen `ChecksResult`.
- Port `run_captured_cmd_then_fix_loop` accounting: cap clamp (1–6, default `RCC_MAX_ITER_DEFAULT=3`), check-first + dispatch-first, empty-failure counter, `no-changes-stale`.
- Fixer step ports `lint-fix-loop.sh`: compose prompt, dispatch via `agents.run_waterfall`, revert forbidden paths (`.gitmodules` + submodules), auto-commit the delta; reuse the injectable `proc.run` seam + `redact.py`.
- Terminal → `Outcome`: `ok`→OK; `exhausted`/`no-changes-stale`→STALLED; `main-agent-required`→NEEDS_USER_INPUT; `dispatch-failed`/`head-changed`→TRANSIENT.

### Surfaces in scope
- New: `python/checks.py`, `python/test_checks.py`.
- Read/port only: `scripts/run-relevant-checks-captured.sh`, `scripts/lint-fix-loop.sh`, `ship-pr.sh` `run_checks_phase` / `run_captured_cmd_then_fix_loop`.
- Reuse (no edits): `python/{agents,outcomes,config,proc,redact,git,errors}.py`.

### Open questions
- Fixer tier order: `lint-fix-loop.sh` dispatches codex→cursor, but `config.FIXER_TIER_ORDER` is `cursor,codex,claude`. Resolve which to honor for parity (lean: preserve lint-fix-loop's codex-first for local-checks parity).
- Auto-commit path: shell out to `scripts/git-commit.sh` vs a `git.py` helper. Resolve in the plan (lean: shell out to `git-commit.sh` for byte-parity with the bash commit message + trailer behavior).
