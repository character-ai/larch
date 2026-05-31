## Goal
Implement issue #3237: [IMPLEMENTING] ship-pr -> Python Phase 4: Local checks & fixer loop\n\n> Part of the **ship-pr.sh → Python** rework. **Full plan, research findings, and cross-phase context: #3132.**.

## Implementation Plan
## Plan

ship-pr → Python **Phase 4: Local checks & fixer loop**. Create `python/checks.py`: a parity-faithful port of the local "Lint and Tests" step. It runs the consumer's checks, parses a typed record, and drives a capped fixer loop (both check-first and dispatch-first) with explicit three-way escalation. **Full** local-fixer port — prompt composition, codex→cursor fixer dispatch via `run-external-agent.sh` (parity with `run_codex` / `run_cursor` in `lint-fix-loop.sh`, not `launch-*-ci.sh`), forbidden-path reversion, and auto-commit. Additive only: no live `/implement` change, no `.sh` deletions (strangler-fig; cutover is Phase 7). Blocked by Phase 1.

**Files to modify/create:**

### NEW: `python/checks.py`

The Phase-4 module. Imports stdlib + siblings only (`config`, `proc`, `agents`, `outcomes`, `redact`, `git`, `errors`); must import cleanly with no import-time side effects (enforced by `test_stdlib_only.py`). Members:

- **`ChecksResult` (frozen dataclass)** — typed port of `run-relevant-checks-captured.sh` machine output: `ok: bool`, `exit_code: int`, `site: str`, `redacted_log_path: str | None`, `phase: str` (`agent-lint` / `pre-commit` / `unknown`), `coverage: str` (`full` / `post-check-only` / `changed-file-only`), `skipped: bool` (RELEVANT_CHECKS_SKIPPED), `warn: str | None`.
- **`FixOutcome` (frozen dataclass)** — typed port of `lint-fix-loop.sh` machine output: `status: str` (`applied` / `no-changes` / `main-agent-required` / `failed`), `delta_paths: tuple[str, ...]`, `failure_reason: str | None`, `commit_sha: str | None`, `head_changed: bool`, `coder_tool: str | None`.
- **`run_relevant_checks(runner, *, site, tmpdir, repo_root) -> ChecksResult`** — port of `run-relevant-checks-captured.sh` orchestration. Validate `tmpdir` (absolute, non-symlink session dir); locate `repo_root/scripts/relevant-checks.sh` (absent → `skipped=True`; broken symlink / non-exec → fail-closed); run it via `runner.run([...], cwd=repo_root)`; write the raw log under `tmpdir/relevant-checks/<site>-<n>.log` (umask 077, mode 0600, collision-safe attempt counter); parse `coverage` / `phase` from log markers (`=== Running pre-commit`, `=== Running agent-lint ===`, agent-lint-missing WARN); on failure produce `redacted_log_path` via `redact.redact()`.
- **`run_lint_fix(runner, *, site, checks_log, repo_root, codex_present, cursor_present, run_parent) -> FixOutcome`** — port of `lint-fix-loop.sh` single dispatch. Require executable `scripts/run-external-agent.sh` (missing/non-exec → `failed` / `missing-run-external-agent` parity). Empty `checks_log` → `no-changes`; neither tool present → `main-agent-required`. Compose the fix prompt (untrusted-log notice, the `FIXED:` / `UNFIXABLE:` final-line contract, submodule prohibition, bounded 60000-byte tail); route log→prompt through `redact.redact()`. Capture baseline tracked/untracked paths + `HEAD` and the forbidden list (`.gitmodules` + submodule paths). **Dispatch codex→cursor by shelling out through `run-external-agent.sh` with argv parity to `run_codex` / `run_cursor` (`lint-fix-loop.sh:234-310`):** per-attempt `run_dir` under `run_parent`, serial-lock acquire/release, codex leaf (`codex exec --full-auto`, events JSONL, telemetry sidecar), cursor preflight (`cursor-wrap-prompt.sh`, model/auth wrapper scripts), `--timeout 1800`, stderr-tail capture on failure. **Do not** call `agents.build_launch_argv`, `agents.launch_tier`, `agents.run_waterfall`, `launch-*-ci.sh`, or `agents.classify_launch_failure` (bash #3207: non-zero dispatch → `main-agent-required` / `dispatch-failed` without CI-style failure classification). After a winning dispatch: forbidden-path reversion (reset-to-baseline on a committed forbidden delta; working-tree `git checkout --` / `rm -f` for untracked), then auto-commit the delta via `scripts/git-commit.sh --no-trailer -m "Apply relevant-checks fixes (<site label>)"` when baseline was clean. Emit `applied` / `no-changes` + `delta_paths` + `commit_sha` / `head_changed` + `coder_tool`. The `head-changed-after-dispatch` ancestry guard → `failed` with `failure_reason=head-changed`.
- **`normalize_max_iter(raw) -> int`** — exact port of `normalize_rcc_max_iter`: non-numeric/empty → 3; multi-digit → 6; `<1` → 3; `>6` → 6; default `config.RCC_MAX_ITER_DEFAULT`.
- **`run_check_fix_loop(*, checks_runner, fixer, dispatch_first, max_iter, initial_redacted_log=None) -> LoopResult`** — port of `run_captured_cmd_then_fix_loop` dual-mode accounting. `checks_runner: Callable[[], ChecksResult]` and `fixer: Callable[[str], FixOutcome]` are injectable seams. Track `attempt`, accumulated `delta_paths`, `empty_failures` (two consecutive → `exhausted`), and the terminal status string (`ok` / `exhausted` / `no-changes-stale` / `main-agent-required` / `dispatch-failed` / `head-changed`) with parity to the bash transitions: `applied` / `no-changes` → continue; on dispatch-first, `no-changes` then still-failing → `no-changes-stale`; `main-agent-required` / `failed` → terminal.
- **`escalate(status, *, delta_paths) -> outcomes.StepResult`** — three-way mapping: `ok` → `OK`; `exhausted` / `no-changes-stale` → `STALLED`; `main-agent-required` → `NEEDS_USER_INPUT`; `dispatch-failed` / `head-changed` → `TRANSIENT`. Returns `StepResult(outcome, detail, payload=delta_paths)`.
- **`run_checks_phase(runner, *, tmpdir, repo_root, codex_present, cursor_present, dispatch_first=False, max_iter=None) -> StepResult`** — thin top-level wiring `run_relevant_checks` (as `checks_runner`) and `run_lint_fix` (as `fixer`) into `run_check_fix_loop`, then `escalate(...)`. Does NOT port ship-pr phase glue (`advance_phase` / `run_recovery_waterfall` / `exit_stall`) — out of scope.

### NEW: `python/test_checks.py`

pytest unit tests (colocated). Stub `Runner`, stub `checks_runner`, stub `fixer` returning scripted sequences. Semantic Python-only parity — no bash executed. Cases listed under Testing strategy.

### UPDATED: `python/README.md`

Add one `checks.py` bullet to the Layout list (port of local checks + fixer loop). Doc-only; no count edits.

### Approach

- Reuse the injectable `proc.Runner` seam for all subprocess work (including `run-external-agent.sh`, `cursor-wrap-prompt.sh`, and `git-commit.sh`); reuse `redact.redact()`, `outcomes.Outcome` / `outcomes.StepResult`. **Do not** import `agents` on the local fixer path (bash #3207 parity); `agents` remains CI-only.
- **`git.py` stays unedited**. The git verbs git.py lacks (`diff --name-only [--cached]`, `add`, `checkout --`, `merge-base --is-ancestor`) run through the injected `Runner` inside `checks.py`; reuse `git.rev_parse` / `git.status` / `git.reset` where they already exist. (Alternative: extend `git.py` with these typed helpers for the CI fixer phase — deferred to keep the change surgical.)
- **Commit parity**: shell out to `scripts/git-commit.sh` (as `lint-fix-loop.sh` does) so commit message + trailer behavior match byte-for-byte; porting `git-commit.sh` itself is a later phase.
- **Local fixer dispatch surface**: mirror `lint-fix-loop.sh`'s `run_codex` / `run_cursor` → `run-external-agent.sh` leaf argv, NOT `agents.build_launch_argv` / `launch-*-ci.sh` (CI fixer). Ordered codex→cursor fallback with `main-agent-required` when both present tiers fail; `agents.run_waterfall` and `config.FIXER_TIER_ORDER` (`cursor,codex,claude`) are CI-only. Non-zero dispatch maps to `main-agent-required` / `dispatch-failed` without `agents.classify_launch_failure` (bash #3207).
- Dual-mode loop mirrors `run_captured_cmd_then_fix_loop`: `dispatch_first=False` is the check-first Step-6 shape (`run_checks_phase`); `dispatch_first=True` is the dispatch-first per-job shape (with `no-changes-stale`).

### Edge cases

- `relevant-checks.sh` absent → `ChecksResult(skipped=True)`; loop treats as clean (no fixer). Broken symlink / non-exec → fail-closed.
- Empty checks log on failure → `no-changes`; two consecutive empty-failure reruns → `exhausted`.
- `dispatch_first=True` + `no-changes` + still failing → `no-changes-stale`.
- Neither external present → `main-agent-required` → `NEEDS_USER_INPUT`.
- Forbidden-path edits (`.gitmodules`, submodule paths): committed delta → reset HEAD to baseline + forbidden `failed`; working-tree → checkout / rm; either → `forbidden-path-violation`.
- `run-external-agent.sh` missing or non-executable → fail-closed (`missing-run-external-agent` parity).
- `max_iter` clamps: 0 → 3, 7+ → 6, non-numeric → 3.
- Redaction runs before any log content reaches a fixer prompt.

### Failure modes

1. **Launcher-surface / waterfall divergence** — routing local fixes through `agents.launch_tier` / `launch-*-ci.sh` / `agents.run_waterfall` would diverge from `lint-fix-loop.sh`'s `run-external-agent.sh` wrappers. Earliest signal: a dispatch-argv parity test sees `launch-codex-ci.sh` or a waterfall short-circuit. Mitigation: shell out `run-external-agent.sh` with `run_codex`/`run_cursor` argv shapes; ordered codex→cursor only; classifiers-only from `agents`.
2. **Forbidden-path / commit git side effects under test** — raw git via `Runner` risks mutating the real tree in tests. Earliest signal: a test touches the working tree. Mitigation: inject a stub `Runner` for unit tests; gate any real-git integration test behind a `tmp_path` git fixture or skip it.
3. **Redaction gap** — a fixer prompt could leak an unredacted path/secret. Earliest signal: a redaction test on a seeded secret fails. Mitigation: route all log→prompt content through `redact.redact()` and assert it in tests.

### Testing strategy

`python/test_checks.py` (pytest, stubs only):

- `normalize_max_iter`: table raw→clamped (`0`, `1`, `3`, `6`, `7`, `99`, empty, `x`) matching `normalize_rcc_max_iter`.
- `run_check_fix_loop` check-first: clean-first → OK (0 dispatches); fail→applied→clean → OK (1 dispatch); applied-but-still-failing ×3 → `exhausted` → STALLED (cap 3); empty-failure ×2 → `exhausted`.
- `run_check_fix_loop` dispatch-first: applied→clean → OK; no-changes→still-failing → `no-changes-stale` → STALLED; applied→applied→clean → OK.
- Transitions: `main-agent-required` → NEEDS_USER_INPUT; `failed`(head-changed) → TRANSIENT; `dispatch-failed` → TRANSIENT.
- `run_relevant_checks` parse: stub `Runner` returns canned check stdout → assert `coverage` / `phase` / `ok` / `redacted_log_path`; absent script → `skipped`; non-exec → fail-closed.
- `run_lint_fix`: stub `Runner` — neither tool → `main-agent-required`; empty log → `no-changes`; missing/non-exec `run-external-agent.sh` → fail-closed; applied path → `delta_paths` + `git-commit.sh` argv + first `run-external-agent.sh` invocation matches the codex leaf argv (`lint-fix-loop.sh:245-252`) and cursor fallback matches (`lint-fix-loop.sh:290-296`), with no `launch-*-ci.sh` in any argv; forbidden-path → reverted + violation; prompt routed via `redact.redact()`.
- `escalate` mapping table: status → `Outcome`.
- stdlib-only + clean-import auto-covered by `test_stdlib_only.py`.

## Acceptance

- `python/checks.py` exists and exposes `run_checks_phase`, `run_check_fix_loop` (dual-mode), `run_relevant_checks`, `run_lint_fix`, `normalize_max_iter`, `escalate`, `ChecksResult`, `FixOutcome`; imports stdlib + siblings only and passes `test_stdlib_only.py` (stdlib-only + clean import).
- Loop convergence, cap enforcement (clamp 1–6, default `RCC_MAX_ITER_DEFAULT=3`), and the three-way escalation (`OK` / `STALLED` / `NEEDS_USER_INPUT` / `TRANSIENT`) are unit-tested in `python/test_checks.py` with a **stub checks runner** and **stub fixer/waterfall** — no bash executed.
- Semantic parity vs `lint-fix-loop.sh` / `run_captured_cmd_then_fix_loop` fix-attempt accounting: `applied` / `no-changes` / `main-agent-required` / `failed` transitions, empty-failure→`exhausted` (two consecutive), and `no-changes-stale` on the dispatch-first path.
- `run_lint_fix` dispatch argv parity is asserted against the `run-external-agent.sh` codex/cursor leaf shapes (`lint-fix-loop.sh:234-310`); no `launch-*-ci.sh` appears in any dispatch argv; local fixer dispatch does not call `agents.classify_launch_failure` (bash #3207 parity).
- Fixer prompt content is routed through `redact.redact()` (asserted on a seeded secret).
- `make py-lint` (ruff + pylint + pyright) and `make py-test` (pytest) pass.
- Additive only: the live `/implement` path is unchanged; `scripts/lint-fix-loop.sh` and `scripts/run-relevant-checks-captured.sh` are not deleted (Phase-7 cutover only).

diff_lines: 870

## Test plan
(no test plan section in plan-file)
