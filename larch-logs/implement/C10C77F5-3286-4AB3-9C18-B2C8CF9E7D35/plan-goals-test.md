## Goal
Implement issue #6286: [IMPLEMENTING] [OOS] Latent hardening: bg-wait & hook parity, marker dedup, write_tally staging (8 items).

## Implementation Plan
## Plan

## Approach

Use the approved outline. `approach-synthesis` is `NO_SKETCHES`, so base the plan on direct repo inspection. Round 1 resolved the two main choices: extract shared Python bg-wait marker code, and compare renamed hook helper pairs semantically.

Keep the change narrow. Do not edit `hook-bg-poll-guard.sh`, `hook-no-progress-guard.sh`, or `run-step-checks.sh`.

## Files to modify/create

### NEW: python/larch/implement/bg_wait.py

Create one shared helper module for bg-wait marker writes.

Include:
- `_clear_no_progress_sidecars(tmpdir: Path) -> None`
- `_read_keepalive_clone_path(tmpdir: Path) -> str`
- `_write_bg_wait_marker(*, tmpdir: Path, step: str, timeout_s: int) -> None`

Preserve the current marker field order exactly:
1. `PID`
2. `CLAUDE_PID`
3. `START_EPOCH`
4. `STEP`
5. `TIMEOUT_S`
6. `CLONE_PATH`

Keep the current best-effort write behavior:
- ignore `.larch-keepalive` read errors
- ignore `.bg-wait-active` write errors
- use `LARCH_BG_POLL_GUARD_SESSION_PID` or `os.getppid()`

Do not move terminal-sentinel context managers into this module unless needed. They are not duplicated in the same way.

### UPDATED: python/larch/implement/dispatch_commit_route.py

Import `_write_bg_wait_marker` from `larch.implement.bg_wait`.

Remove the local duplicate `_clear_no_progress_sidecars`, `_read_keepalive_clone_path`, and `_write_bg_wait_marker`. Remove imports that are no longer needed; do NOT remove `import time` without first verifying no other function in the file still uses it (e.g. `step5_resume_main` uses `int(time.time())`). [FINDING_4]

Keep `_bg_wait_marker`, `_optional_bg_wait_marker`, and `_checks_commit_route_marker` local.

Update `run_step_checks_main` to arm the bg-wait marker for step3 only:

- Only arm when `args.site == "step3"`.
- Do not arm for `step5-self-review` or other sites; `checks_commit_route_main` owns those.
- Use `STEP=implement-step3-checks`, `TIMEOUT_S=10800`, and terminal sentinel `.completed/step-3-terminal`. These match `run-step-checks.sh`; do not use the composite-route 15600 timeout. [FINDING_6]
- Before arming, clear the stale step-3 terminal sentinel and its probe-denial counter:
  - delete `$IMPLEMENT_TMPDIR/.completed/step-3-terminal` (suppress errors)
  - delete `$IMPLEMENT_TMPDIR/bg-poll-guard-probe-denials.step-3-terminal.count` (suppress errors)
  This matches the cleanup that `run-step-checks.sh` performs before writing the marker. [FINDING_5]
- Wrap the `_run_cli_forward(["checks", "run-relevant", ...])` call inside `_bg_wait_marker` so the terminal sentinel is written and the marker is removed on exit. Use a conditional: only enter the context manager for `step3`; call `_run_cli_forward` directly for other sites.

### UPDATED: python/larch/implement/step_7a.py


Remove the local duplicate `_clear_no_progress_sidecars`, `_read_keepalive_clone_path`, and `_write_bg_wait_marker`. [FINDING_3]

Keep the local `_bg_wait_marker` context manager. It should call the imported helper.

### UPDATED: python/tests/implement/test_implement_dispatch.py

Update the existing bg-wait marker test to import or call the shared helper through the module under test in a way that still proves dispatch uses the shared writer.

Add a focused test for `run_step_checks_main`:
- create an `IMPLEMENT_TMPDIR`
- write `.larch-keepalive` with `CLONE_PATH`
- monkeypatch `_run_cli_forward` to inspect `.bg-wait-active` while the command runs
- call `run_step_checks_main(["--site", "step3"])`
- assert the marker contains `STEP=implement-step3-checks` and `CLONE_PATH=...`
- assert `.completed/step-3-terminal` exists after return
- assert `.bg-wait-active` is gone after return

Add a second small assertion or param case that a non-marker site (e.g. step5) does not create `.bg-wait-active`.

### UPDATED: python/tests/implement/test_step_7a.py

Update the existing marker test (`test_step7a_bg_wait_marker_copies_keepalive_clone_path` or equivalent) to exercise `larch.implement.bg_wait._write_bg_wait_marker` directly, or enter `step_7a._bg_wait_marker` (the context manager) and assert marker fields. Do NOT reference `step_7a._write_bg_wait_marker`; that symbol is removed by the extraction. [FINDING_6]

Keep the assertions for `STEP=implement-step7a` and `CLONE_PATH`.

### UPDATED: python/larch/lint/lint_bg_wait_writer_parity.py

Narrow `_has_clone_path_emission`. [FINDING_1]

Replace the current file-wide `CLONE_PATH=` scan with a write-scoped adjacency check:
- split the file into lines
- iterate lines; for each non-comment line, check if it contains `.bg-wait-active` in a write context:
  - write-context indicators: `write_text(`, `printf`, `> `, `>>` (redirect to the marker), `.replace(`
  - skip lines that only mention `.bg-wait-active` in a cleanup context: `rm `, `.unlink()`, `del `
- for each qualifying write-context line, inspect a window of ≥15 lines before and after
- require at least one non-comment line in that window containing `CLONE_PATH=`

Add a repo-root acceptance test to `test_lint_bg_wait_writer_parity.py` that runs the lint against the live WRITERS files under the real repo root. This ensures the rule cannot ship while real writer shapes (e.g. multiline `printf` in `design-step3-review.sh`, `write_text` in `design_core.py`) still pass.

Keep `_has_writer_evidence` as the broad guard for known writer files.

Update `WRITERS` for the new shared module after extraction:
- keep shell writer files
- keep `python/larch/design/design_core.py`
- replace the two implement Python writer entries with `python/larch/implement/bg_wait.py`
- use a label such as `implement Python bg-wait helper`

Do not keep `dispatch_commit_route.py` and `step_7a.py` in `WRITERS` after extraction; this lint checks file text, not the call graph.

### UPDATED: python/tests/lint/test_lint_bg_wait_writer_parity.py

Update inventory fixtures for the new `bg_wait.py` writer entry.

Add a regression test for Item 1:
- writer evidence includes a `.bg-wait-active` write-context line but no nearby `CLONE_PATH=`
- add an unrelated non-comment `CLONE_PATH=` far away (outside the window)
- assert lint fails with `does not emit CLONE_PATH=`

Add a test confirming that a cleanup-only `.bg-wait-active` mention (e.g. `rm -f .bg-wait-active`) does not trigger a false failure when `CLONE_PATH=` is elsewhere in the file.

Add the repo-root acceptance test: run `lint_writers(repo_root)` on the live tree and assert zero violations. Keep the existing missing-path and cleanup-only tests.

### UPDATED: python/larch/review/voting.py

Add a small helper to resolve the temp staging directory for `write_tally_main`, for example `_write_tally_stage_dir(log_root: str) -> Path`.

Contract:
- compute `parent = Path(log_root).parent`
- reject or fail closed when the parent is not safe for staging
- accept the normal path `<IMPLEMENT_TMPDIR>/larch-logs`, where parent is `IMPLEMENT_TMPDIR`
- reject root parent, empty relative parent, nonexistent parent, non-directory parent, and symlink parent

Prefer raising via `_die(...)` for invalid staging roots. This is simpler and safer than falling back to `/tmp`.

Use the helper as `dir=_write_tally_stage_dir(args.log_root)` in `NamedTemporaryFile`.

Add a short comment near the helper: `write_tally` stages the record beside `larch-logs` so downstream redaction and rebasing stay under the implement tmpdir.

### UPDATED: python/tests/review/test_voting.py

Strengthen `test_write_tally_stages_record_under_log_root_parent`.

Use an in-process test seam instead of relying only on the subprocess:
- monkeypatch `voting.proc.run`
- capture the `--input-file` value passed to `run-log write`
- while the fake `proc.run` executes, assert that the captured temp file exists and its parent is `tmp_path`
- return a `CommandResult`-compatible object with `returncode=0`, `stdout="LOG_WRITTEN=true\n"`, `stderr=""`

Keep the existing subprocess-level happy path if useful, but add the staging assertion that fails if `dir=` is removed.

Add a new rejection test for root or unsafe parent, such as `--log-root /larch-logs`, expecting a non-zero return and a clear diagnostic.

### UPDATED: scripts/test-hook-clone-ownership-parity.sh

Replace `extract_function` with a brace-depth extractor.

Implementation shape:
- start when the exact function header line matches `name() {` (awk pattern: `$0 == name "() {"`)
- print each line in the function
- count `{` and `}` characters after entry
- exit only after the function depth returns to zero

This harness only needs to parse the style used in these hooks. It does not need a full Bash parser.

**Step-completion renamed pair (item 7)**: `marker_step_completed` vs `is_step_completed`.
These bodies have comment-only drift. Add `compare_renamed_pair`:
- extract both functions
- strip comment-only lines (lines whose first non-whitespace character is `#`) from each body
- strip the differing header line (first line of each function)
- diff the remaining comment-stripped body
- pass if the bodies are identical; fail if they differ

**Liveness renamed pair (item 8)**: `marker_is_live` vs `is_marker_live`.
These functions diverge intentionally in parent-guard, reset helper, marker-step metadata, and missing-marker handling. [FINDING_2]
Do not add `compare_renamed_pair` for this pair. Instead add a documented exclusion comment in the harness (and in the `.md` sibling) explaining:
- `marker_is_live` (`hook-bg-poll-guard.sh`) and `is_marker_live` (`hook-no-progress-guard.sh`) serve the same semantic role but differ in: parent-guard return codes, missing-marker reset behavior (`reset_no_progress_state`), and `LIVE_MARKER_DIR` side-effect owned by no-progress-guard. Byte-identical comparison is not applicable.
- Coverage of each function's logic remains within its respective hook's own test suite.

Keep existing byte-identical comparisons unchanged.

Add explicit invocation of `compare_renamed_pair` for the step-completion pair alongside the existing `compare_function` calls: [FINDING_1]
```
compare_renamed_pair "$BG_HOOK" marker_step_completed "$NO_PROGRESS_HOOK" is_step_completed
This call must appear in the harness body (not just in the helper definition) so one-sided drift in `marker_step_completed`/`is_step_completed` is caught on every run.

### UPDATED: scripts/test-hook-clone-ownership-parity.md

Update the invariant list:
- mention brace-depth function extraction
- mention comment-stripped semantic comparison for `marker_step_completed`/`is_step_completed`
- document the explicit exclusion rationale for the liveness pair
- keep the self-contained hook rationale

## Edge cases

- Python marker extraction must not drop `CLONE_PATH` from the field order.
- `run_step_checks_main` must not arm markers for sites other than `step3`.
- `run_step_checks_main` must clear stale `.completed/step-3-terminal` and probe-denial counters before arming.
- The lint must ignore comments that mention `CLONE_PATH=`.
- The lint must not pass when `CLONE_PATH=` appears far from a write-context `.bg-wait-active` line.
- The lint must not false-fail when `.bg-wait-active` appears only in cleanup lines (rm/unlink) and `CLONE_PATH=` is elsewhere in the file.
- `write_tally_main` must not stage temp files in `/`, a symlink parent, or a missing parent.
- The hook harness brace counter may see braces in strings. Keep the implementation scoped to current hook style and covered by the live harness.
- Comment-stripped comparison for `marker_step_completed`/`is_step_completed` must not hide real logic drift.

## Failure modes

- A write-context lint anchor that is too narrowly defined could miss novel Python or shell writer shapes. Tune anchor patterns against the live WRITERS inventory.
- Moving writer code to `bg_wait.py` can make the parity lint lose evidence if `WRITERS` is not updated.
- Importing the new module can create unused import failures if old imports remain.
- `write_tally_main` can become too strict for valid tests with relative `--log-root`. Prefer explicit tests for the accepted contract.
- Hook harness normalization can create false passes if it rewrites too much. Normalize only header and comment lines; preserve executable body byte-for-byte.

## Testing strategy

Run changed-file checks only.

Python unit tests:
- `python3 -m pytest python/tests/lint/test_lint_bg_wait_writer_parity.py -q`
- `python3 -m pytest python/tests/implement/test_implement_dispatch.py python/tests/implement/test_step_7a.py -q`
- `python3 -m pytest python/tests/review/test_voting.py -q`

Harness:
- `make test-hook-clone-ownership-parity`
- `make test-lint-bg-wait-writer-parity`

Relevant lint:
- `python3 python/cli.py lint bg-wait-writer-parity`
- run ruff or the repo's relevant-checks path for changed Python files if available in the implementation environment

Manual negative checks:
- temporarily remove nearby `CLONE_PATH=` from a fixture writer and confirm the lint test fails
- temporarily add a cleanup-only `.bg-wait-active` reference and confirm it does not cause a false failure
- temporarily add a nested `{ ...; }` block inside a compared hook helper and confirm the parity harness fails on drift or still extracts the whole function
- temporarily remove `dir=` from `write_tally_main` and confirm the strengthened staging test fails

## Acceptance

Run changed-file checks only.

Python unit tests:
- `python3 -m pytest python/tests/lint/test_lint_bg_wait_writer_parity.py -q`
- `python3 -m pytest python/tests/implement/test_implement_dispatch.py python/tests/implement/test_step_7a.py -q`
- `python3 -m pytest python/tests/review/test_voting.py -q`

Harness:
- `make test-hook-clone-ownership-parity`
- `make test-lint-bg-wait-writer-parity`

Relevant lint:
- `python3 python/cli.py lint bg-wait-writer-parity`
- run ruff or the repo's relevant-checks path for changed Python files if available in the implementation environment

Manual negative checks:
- temporarily remove nearby `CLONE_PATH=` from a fixture writer and confirm the lint test fails
- temporarily add a cleanup-only `.bg-wait-active` reference and confirm it does not cause a false failure
- temporarily add a nested `{ ...; }` block inside a compared hook helper and confirm the parity harness fails on drift or still extracts the whole function
- temporarily remove `dir=` from `write_tally_main` and confirm the strengthened staging test fails

review_status: complete
rounds_completed: 2
difficulty: MODERATE
mechanical_churn: false
diff_lines: 210

## Test plan
(no test plan section in plan-file)
