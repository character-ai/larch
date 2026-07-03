## Plan

## Approach

Add a thin PID-keyed `/implement` launcher that mirrors `/design`'s `design-run-$PPID.sh` pattern, and close two correctness gaps plan review found: caller-shell argv expansion (FINDING_1), and a fail-silent Step 0 write path (FINDING_4). Also fix a PID-consistency bug identified during drafting (related to OOS_3/FINDING_3 discussion): the pid that names the pointer/launcher must be captured at the same nesting depth every post-Step-0 fence will later read it from.

- Keep Step 0 as the only place that discovers and persists `IMPLEMENT_TMPDIR`.
- Extend `session write-implement-env` so it writes both:
  - `~/.cache/larch/sessions/current-implement-env-$PID.sh`
  - `~/.cache/larch/sessions/implement-run-$PID.sh`
- Make `implement-run-$PID.sh` read `IMPLEMENT_TMPDIR` from the pointer file, export it, then `exec "$IMPLEMENT_TMPDIR/larch-run.sh" "$@"`.
- Replace prompt-side post-Step-0 launcher prefixes with:
  - `"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" <relative-script-path> ...`
- **PID consistency fix**: `step-0-bootstrap.sh` currently computes `LARCH_CLAUDE_PID="${LARCH_CLAUDE_PID:-$PPID}"` using its *own* `$PPID`, one process hop deeper than the top-level Bash-tool shell every later fence reads `$PPID` from. Fix this at the call site instead of inside the script: prefix the Step 0 fence itself with `LARCH_CLAUDE_PID="$PPID"` so the value is captured at the same top-level depth every later fence uses. `step-0-bootstrap.sh`'s existing `${LARCH_CLAUDE_PID:-$PPID}` line needs no change: an inherited non-empty `LARCH_CLAUDE_PID` short-circuits the fallback. Apply the same prefix to the `--mode resume` fence in `bootstrap-recovery.md`.
- **Argv-empty-shell fix (FINDING_1)**: a fresh Bash tool call still expands `--implement-tmpdir "$IMPLEMENT_TMPDIR"` and similar tokens to empty strings before any launcher process starts, because the caller shell computes argv before `exec`-ing the launcher. Teach the affected CLI entrypoints to fall back to `os.environ.get("IMPLEMENT_TMPDIR", "")` when their tmpdir argv value is empty, mirroring the existing `args.implement_tmpdir or os.environ.get("IMPLEMENT_TMPDIR", "")` pattern already used by `commit_route_main` in `dispatch_commit_route.py`. This works because the launcher chain (`implement-run-$PID.sh` -> `larch-run.sh` -> the Python entrypoint) always exports a correct `IMPLEMENT_TMPDIR` into the process environment via fork/exec inheritance, even when the outer argv slot is empty. Scope is limited to `--implement-tmpdir`/`--tmpdir`, the specific tokens the accepted finding named; other session-bound argv tokens (`$coder`, `$RUN_ID`, `$REPO_ROOT`, ...) stay the orchestrator's literal-substitution responsibility, unchanged by this plan.
- **Fail loudly on Step 0 launcher-write failure (FINDING_4, extended)**: once `session write-implement-env` owns the stable launcher, a failed write must stop Step 0 instead of warning and continuing, because every later fence depends on that launcher existing. Extend this to the case where `LARCH_CLAUDE_PID` itself is empty when the implement bootstrap path is reached: `_phase_infra` must fail loudly there too, not silently skip the write (round-2 finding, self-identified from the same code path as FINDING_4).
- **Step 8 handoff robustness (FINDING_2)**: the Step 8 handoff probe (`test -f "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc"`) and the stale-handoff `rm -f` clear are raw shell fences, not launcher invocations, so a fresh shell still expands `$IMPLEMENT_TMPDIR` to an empty prefix (producing a root-relative path) in both. Resolve `IMPLEMENT_TMPDIR` from the same `current-implement-env-$PPID.sh` pointer the new runner reads, inline, immediately before each command, preserving the existing trailing `test -f .../.step-8-ship-handoff.rc` and `rm -f .../.step-8-ship-handoff.rc .../.step-8-ship-handoff.json` shape so `scripts/hook-bg-poll-guard.sh`'s pattern match and `scripts/test-implement-anti-polling-rule.sh`'s pinned literal keep recognizing the sanctioned Step 8 probe. Verify both against the actual hook and test before finalizing the exact inline resolution text.
- **Route-exit json-file simplification (FINDING_7)**: `ship_route_exit_main` already falls back to `implement_tmpdir / ".step-8-ship-handoff.json"` when `--json-file` is empty, but a fresh shell expands `--json-file "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.json"` to a *non-empty* root-relative path (not empty), which defeats that fallback. Drop the redundant `--json-file` argument from the route-exit fence entirely; the existing default already points at the same path, so this is a pure simplification with no behavior change on the happy path and no code change needed in `dispatch_ship.py`.
- Do not change `larch-run.sh`'s internal dispatch, cleanup, or plugin-root recovery logic.
- Do not add Step 18 cleanup for `implement-run-$PID.sh` (parity with `/design`'s own never-cleaned `design-run-$PID.sh`).

## Files to modify/create

### UPDATED: python/larch/state/session_env.py

Add implement launcher helpers near the existing design launcher helpers:

- `_implement_run_path(pid: str) -> Path`
- `_implement_run_launcher_text(pid: str) -> str`
- `_write_implement_run_sh(pid: str) -> None`

Wire `_write_implement_run_sh()` into `write_implement_env_main()` after the current-env pointer write succeeds.

Launcher requirements:

- Use `"$HOME/.cache/larch/sessions/current-implement-env-$PID.sh"` as the only pointer source.
- Parse `IMPLEMENT_TMPDIR=` from the pointer without shell-sourcing arbitrary content.
- Reject missing pointer, missing `IMPLEMENT_TMPDIR`, non-absolute tmpdir, missing `larch-run.sh`, and non-executable `larch-run.sh` with exit `2`.
- Export `IMPLEMENT_TMPDIR` before `exec`.
- Preserve argv exactly after launcher rehydration.
- Reuse existing PID validation, symlink guards, atomic write, and mode `0o755`.

Keep `clear_implement_pointer_main()` limited to the pointer. Do not remove the new runner there.

### UPDATED: python/larch/state/bootstrap.py

In `_phase_infra`, when `_cli("session", "write-implement-env", ...)` returns non-zero:

- Keep writing the diagnostic log and the `run-log append-failure` call exactly as today.
- After logging, call `st.emit_step_failed("write-implement-env")` instead of continuing, so bootstrap exits before `BOOTSTRAP_NEXT=step2` rather than leaving a dangling or missing launcher for Step 2+ to trip over later.
- Leave the existing `if pid and st.implement_tmpdir:` guard unchanged for the write-attempt branch; only that failure's outcome changes from warn-and-continue to fatal.

Additionally, when `st.implement_tmpdir` is set but `pid` is empty (so the guard's condition is false and `write-implement-env` is never even attempted), also call `st.emit_step_failed("write-implement-env")` instead of silently proceeding to `BOOTSTRAP_NEXT=step2` with no stable launcher written.

### UPDATED: python/larch/implement/dispatch_step2.py

`run_dispatch_main`: change `--implement-tmpdir` from `required=True` to `default=""`. After parsing, resolve `raw_tmpdir = args.implement_tmpdir or os.environ.get("IMPLEMENT_TMPDIR", "")`; if empty, print a clear error and return `2` before constructing any `Path`, so an empty value can never silently resolve to the current working directory.

### UPDATED: python/larch/implement/dispatch_ship.py

`ship_route_exit_main`: same `--implement-tmpdir` fallback-and-empty-check pattern as `dispatch_step2.py`.

### UPDATED: python/larch/implement/step_7a.py

`main()`: the existing `default=os.environ.get("IMPLEMENT_TMPDIR", "")` only applies when `--implement-tmpdir` is omitted from argv, not when it is passed with an empty string (the fresh-shell case). Add the same post-parse `args.implement_tmpdir or os.environ.get("IMPLEMENT_TMPDIR", "")` resolution and empty-check used elsewhere in this plan.

### UPDATED: python/larch/implement/dispatch_step18.py

`step_18_gate_finalize_main`: same `--implement-tmpdir` fallback-and-empty-check pattern.

### UPDATED: python/larch/issue/execution_issues.py

`refresh_execution_issues_main`: same `--implement-tmpdir` fallback-and-empty-check pattern.

### UPDATED: python/larch/implement/dispatch_manifest.py

`normalize_coder_scout_main`: same fallback-and-empty-check pattern for `--tmpdir` (already checks `.is_dir()`; add the env fallback before that check so an empty argv value does not fall through to a not-a-directory error against `Path("")`/cwd).

### UPDATED: python/larch/implement/dispatch_recovery.py

`recovery_paths_main`: same fallback-and-empty-check pattern for `--tmpdir` only. `--repo-root` and the porcelain/digest file arguments are unaffected by this finding and stay `required=True`.

### UPDATED: python/tests/state/test_session_env.py

Extend `test_write_and_clear_implement_env_pointer` or add focused tests for the new runner.

Cover:

- `write_implement_env_main()` writes an executable `implement-run-12345.sh`.
- The runner can be invoked with `IMPLEMENT_TMPDIR` absent from the environment.
- A fixture `larch-run.sh` receives the original argv and sees exported `IMPLEMENT_TMPDIR`.
- Clearing the pointer removes only `current-implement-env-$PID.sh`; the run script may remain.
- Bad PID paths still write neither pointer nor run script.

### UPDATED: python/tests/state/test_bootstrap.py

Rename `test_write_implement_env_failure_logs_warning_and_continues` to reflect fatal behavior (for example `test_write_implement_env_failure_is_fatal`). Assert `bootstrap._phase_infra(st)` now raises `bootstrap.BootstrapExit` with code `2` instead of returning normally, while keeping the existing assertions that the diagnostic log is written and `run-log append-failure` is called.

Add one more test: `LARCH_CLAUDE_PID` unset (or empty) with a valid `implement_tmpdir` also raises `bootstrap.BootstrapExit` with code `2`, and `session write-implement-env` is never invoked in that case.

### UPDATED: python/tests/implement/test_implement_dispatch.py

Add one execution test per hardened entrypoint (`run_dispatch_main`, `ship_route_exit_main`, `step_18_gate_finalize_main`, `normalize_coder_scout_main`, `recovery_paths_main`): invoke with the tmpdir argv value set to `""` (mirroring a verbatim expanded-empty fence) while only `IMPLEMENT_TMPDIR`/`os.environ` carries the real path, and assert the call succeeds against the real tmpdir instead of failing or resolving to `.`.

### UPDATED: python/tests/implement/test_step_7a.py

Add the same empty-argv-with-env-fallback execution test for `main()`.

### UPDATED: python/tests/issue/test_execution_issues.py

Add the same empty-argv-with-env-fallback execution test for `refresh_execution_issues_main`.

### UPDATED: skills/implement/SKILL.md

Update the Bash block prelude contract and every prompt-side post-Step-0 fence.

Replace the launcher prefix only:

- From: `bash "$IMPLEMENT_TMPDIR/larch-run.sh" `
- To: `"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" `

Keep the rest of each command unchanged, including `--implement-tmpdir "$IMPLEMENT_TMPDIR"` and other argument values (the Python-side fallback added in this plan makes those tokens safe even when the caller shell expands them to empty strings).

Prefix the Step 0 `--mode initial` fence with `LARCH_CLAUDE_PID="$PPID" ` immediately before the script path, so the pid baked into the pointer/launcher matches every later top-level fence's own `$PPID`.

Update prose to state:

- Step 0 writes both `$IMPLEMENT_TMPDIR/larch-run.sh` and the PID-keyed stable launcher, using the top-level Bash-tool `$PPID` captured at the Step 0 fence.
- Post-Step-0 fences call the stable launcher because Bash tool calls do not preserve exported variables.
- Fences remain exactly one nonblank, noncomment physical line.
- No inline sourcing, exports, continuations, or shell logic are allowed (the `LARCH_CLAUDE_PID="$PPID" ` prefix on the Step 0 fence is a plain environment-variable-prefix assignment, not shell logic, and Step 0 already keeps its existing multi-line exemption).

Do not change the Step 16-17 direct Python CLI exception unless an existing harness requires a related wording update.

Drop `--json-file "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.json"` from the `ship route-exit` fence; keep `--implement-tmpdir "$IMPLEMENT_TMPDIR"` and the rest unchanged. `ship_route_exit_main` already defaults to the same path when `--json-file` is empty.

Fix the Step 8 handoff probe and stale-handoff clear (in the "Post-ship durable handoff" prose and the pre-launch stale-clear line) so each resolves `IMPLEMENT_TMPDIR` from `current-implement-env-$PPID.sh` inline immediately before the existing `test -f`/`rm -f` command, instead of trusting a bare `$IMPLEMENT_TMPDIR` reference. Preserve the exact trailing `test -f ".../.step-8-ship-handoff.rc"` and `rm -f ".../.step-8-ship-handoff.rc" ".../.step-8-ship-handoff.json"` text so existing hook/CI matching on that substring keeps working; verify against `scripts/hook-bg-poll-guard.sh` and `scripts/test-implement-anti-polling-rule.sh` (see their own file sections below) before finalizing the exact inline-resolution syntax.

### UPDATED: skills/implement/references/bootstrap-recovery.md

Prefix the `--mode resume` fence with `LARCH_CLAUDE_PID="$PPID" ` for the same reason as the Step 0 initial fence.

### UPDATED: skills/shared/orchestrator-never.md

Apply the same Step 8 handoff probe inline-resolution fix as `skills/implement/SKILL.md` to both occurrences of `test -f "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc"` in this file, keeping the trailing substring identical for the reason described there.

### MAY_UPDATE: scripts/hook-bg-poll-guard.sh

Read the hook's pattern-matching for the Step 8 probe/marker before changing any probe text. Update only if the hook matches on more than the trailing `.step-8-ship-handoff.rc` substring (for example if it also anchors on the exact `test -f "$IMPLEMENT_TMPDIR...` prefix); otherwise no change is needed.

### UPDATED: scripts/test-implement-anti-polling-rule.sh

Update the pinned probe literal if this harness asserts the exact `test -f "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc"` string rather than a trailing-substring match.

### UPDATED: skills/review/SKILL.md

Update the nested `/implement` MAV cross-reference launcher example to use `"$HOME/.cache/larch/sessions/implement-run-$PPID.sh"`.

### UPDATED: skills/implement/references/checks-repair-loop.md

Update the prompt-side recovery-paths launcher example.

### UPDATED: skills/implement/references/self-review.md

Update prompt-side self-review launcher examples.

Keep any explicit best-effort `|| true` exception only if the harness still allows it after the prefix change.

### UPDATED: skills/implement/references/step5-review-branches.md

Update Step 5 branch launcher examples, including MAV and stall-seed examples.

### UPDATED: skills/implement/references/architectural-guidelines-present.md

Update the write-staged launcher example.

### UPDATED: skills/implement/references/step2-dispatch.md

Update example commit launcher lines if they are intended as orchestrator-issued fences.

If those lines are only illustrative shell examples for code-generated commands, keep them only if reviewers confirm they are not part of the prompt-side fence contract.

### UPDATED: skills/implement/scripts/step-2-post-dispatch.md

Update the script doc launcher example.

### UPDATED: skills/implement/scripts/step-18.md

Update the script doc launcher examples.

### MAY_UPDATE: skills/implement/scripts/step-8-ship.sh

Leave the internal `run_and_capture_stdout bash "$IMPLEMENT_TMPDIR/larch-run.sh" ...` call unchanged unless tests prove it is prompt-side or variable-free-shell exposed.

This call runs inside an already rehydrated script context, so it is not part of the reported failure.

### UPDATED: scripts/test-implement-fence-shape.sh

Update the structural harness for the new launcher prefix.

Required assertions:

- New-shape prompt-side fences start with `"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" `, or match the existing Step 16-17 direct Python exception.
- The first token is the stable runner path, not `bash`.
- The second token remains the repo-relative `.sh` or `.py` target.
- Inline shell logic remains forbidden.
- The generated `larch-run.sh` sandbox still tests the unchanged tmpdir-local launcher.
- Add or adapt a sandbox test that proves the PID-keyed runner reaches `larch-run.sh` when `IMPLEMENT_TMPDIR` is unset.
- The Step 0 initial and resume old-shape fences require the `LARCH_CLAUDE_PID="$PPID" ` prefix.

Update `EXPECTED_OLD` / `EXPECTED_NEW` only if the replacement changes the counted fence total.

### UPDATED: scripts/test-implement-fence-shape.md

Document the new prompt-side launcher contract, the `LARCH_CLAUDE_PID="$PPID" ` Step 0 prefix requirement, and keep the generated `larch-run.sh` sandbox description separate.

### UPDATED: scripts/test-implement-structure.sh

Update pinned launcher literals and ordering checks to the stable runner prefix. Update the pinned Step 0 wrapper literal to include the `LARCH_CLAUDE_PID="$PPID" ` prefix.

Keep assertions for:

- Required prompt-side launch sites.
- Step 16-17 direct Python exception.
- Step 18 composite and finalize routing.
- Step 8 pre-driver and route-exit ordering.

### UPDATED: scripts/test-implement-structure.md

Update the documented post-Step-0 launcher shape.

### UPDATED: scripts/test-implement-timing-rehydration.sh

Update grep literals for Step 18 launcher checks.

Keep older guard/export assertions scoped to old-shape pre-bootstrap fences only.

### UPDATED: scripts/test-render-cost-line-callsites.sh

Update Step 18 launcher and composite pinned strings.

Update the awk block that extracts the Step 18 fence so it matches the new prefix.

### UPDATED: skills/implement/scripts/test-architectural-guidelines-step.sh

Update pinned launcher strings for the prepare and write-staged fences.

## Edge cases

- **Fresh Bash shell:** `IMPLEMENT_TMPDIR` is absent. The stable runner must still find the pointer by `$HOME` and `$PPID`.
- **Missing pointer:** fail with a clear exit `2` before invoking `larch-run.sh`.
- **Stale pointer:** fail if the pointed tmpdir no longer has executable `larch-run.sh`.
- **Symlink attack:** keep current symlink ancestor checks before writing pointer and runner paths.
- **Empty tmpdir argv:** hardened Python entrypoints must reject an empty resolved tmpdir with a clear error, never silently treat it as the current working directory.
- **Non-empty but wrong tmpdir-derived argv:** an argument like `--json-file "$IMPLEMENT_TMPDIR/x.json"` does not expand to empty in a fresh shell; it expands to a root-relative path (`/x.json`), which a plain `if arg:` truthy fallback cannot catch. Prefer dropping such redundant, tmpdir-derived arguments in favor of the callee's own default over adding path-validity heuristics.
- **PID mismatch:** the pid baked into `implement-run-$PID.sh` must match the pid every later fence's own `$PPID` resolves to; capturing `$PPID` at the Step 0 fence itself (not inside `step-0-bootstrap.sh`) keeps them consistent.
- **Hook/CI pattern drift:** changing the Step 8 handoff probe's literal text can silently desync `scripts/hook-bg-poll-guard.sh`'s live gating logic from the documented contract; verify the hook's actual matching before changing probe text, not just the test harness.
- **Internal script-to-script calls:** do not mechanically replace calls that happen after `larch-run.sh` has already exported `IMPLEMENT_TMPDIR` (for example `step-8-ship.sh`'s internal call to `step-8-python-guard.sh`).

## Failure modes

- A partial prompt update can leave one Step 2 through Step 18 fence on the old `bash "$IMPLEMENT_TMPDIR/larch-run.sh"` prefix.
- A too-broad grep replacement can break internal same-process calls.
- A runner that sources the pointer file can import unexpected shell content. Parse only the needed key instead.
- A runner that omits `exec` can alter signal and exit-code behavior.
- A test update that only changes string literals can miss the original variable-free-shell failure; execution tests against the real entrypoints catch this class where string-literal tests cannot.
- Rewriting the Step 8 handoff probe's shell text without checking `scripts/hook-bg-poll-guard.sh` first can desync the hook's Monitor/TaskOutput gating from the documented contract, silently weakening an anti-polling guard rather than fixing a launcher bug.

## Testing strategy

Run targeted checks for changed surfaces:

- `python3 -m pytest python/tests/state/test_session_env.py python/tests/state/test_bootstrap.py python/tests/implement/test_implement_dispatch.py python/tests/implement/test_step_7a.py python/tests/issue/test_execution_issues.py`
- `bash scripts/test-implement-fence-shape.sh`
- `bash scripts/test-implement-structure.sh`
- `bash scripts/test-implement-timing-rehydration.sh`
- `bash scripts/test-render-cost-line-callsites.sh`
- `bash skills/implement/scripts/test-architectural-guidelines-step.sh`
- `bash scripts/test-implement-anti-polling-rule.sh`
- `make test-hook-bg-poll-guard` (confirm the Step 8 probe rewrite still gates Monitor/TaskOutput denial correctly)

Also run a grep gate after edits:

- Search prompt docs and harnesses for `bash "$IMPLEMENT_TMPDIR/larch-run.sh"`.
- Confirm only the intentional internal script-to-script call and generated `larch-run.sh` tests remain.
- Search for `implement-run-$PPID.sh` and confirm all prompt-side post-Step-0 fences use the new prefix.
- Search for `step-0-bootstrap.sh` invocation sites and confirm both the initial and resume fences carry the `LARCH_CLAUDE_PID="$PPID" ` prefix.
- Search for `.step-8-ship-handoff.rc` across `skills/implement/SKILL.md` and `skills/shared/orchestrator-never.md` and confirm every occurrence resolves `IMPLEMENT_TMPDIR` inline rather than trusting a bare reference.
- Confirm `--json-file` no longer appears on the `ship route-exit` fence.

## Acceptance

Run targeted checks for changed surfaces:

- `python3 -m pytest python/tests/state/test_session_env.py python/tests/state/test_bootstrap.py python/tests/implement/test_implement_dispatch.py python/tests/implement/test_step_7a.py python/tests/issue/test_execution_issues.py`
- `bash scripts/test-implement-fence-shape.sh`
- `bash scripts/test-implement-structure.sh`
- `bash scripts/test-implement-timing-rehydration.sh`
- `bash scripts/test-render-cost-line-callsites.sh`
- `bash skills/implement/scripts/test-architectural-guidelines-step.sh`
- `bash scripts/test-implement-anti-polling-rule.sh`
- `make test-hook-bg-poll-guard` (confirm the Step 8 probe rewrite still gates Monitor/TaskOutput denial correctly)

Also run a grep gate after edits:

- Search prompt docs and harnesses for `bash "$IMPLEMENT_TMPDIR/larch-run.sh"`.
- Confirm only the intentional internal script-to-script call and generated `larch-run.sh` tests remain.
- Search for `implement-run-$PPID.sh` and confirm all prompt-side post-Step-0 fences use the new prefix.
- Search for `step-0-bootstrap.sh` invocation sites and confirm both the initial and resume fences carry the `LARCH_CLAUDE_PID="$PPID" ` prefix.
- Search for `.step-8-ship-handoff.rc` across `skills/implement/SKILL.md` and `skills/shared/orchestrator-never.md` and confirm every occurrence resolves `IMPLEMENT_TMPDIR` inline rather than trusting a bare reference.
- Confirm `--json-file` no longer appears on the `ship route-exit` fence.

review_status: complete
rounds_completed: 2
difficulty: HARD
diff_lines: 560
