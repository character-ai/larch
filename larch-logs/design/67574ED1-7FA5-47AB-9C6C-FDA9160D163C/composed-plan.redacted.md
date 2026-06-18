## Plan

## Approach

- **Port only Step 5b orchestration.**
- Add `step5b_prepare_main` and `step5b_annotate_main` in `python/design_lifecycle.py`.
- Preserve the current Bash contracts:
  - session env rehydration
  - `CLAUDE_PLUGIN_ROOT` validation
  - `DESIGN_TMPDIR` validation (bash parity; see below)
  - pause-save handoff
  - `.completed/step-4b` and `.completed/step-5b` sentinels
  - timing mark
  - stdout and stderr capture files
  - `STEP5B_*`, `OOS_*`, and `FILE_DESIGN_OOS_*` rows
  - run-log failure append behavior
- Call `design_oos.file_oos_prepare_main` and `design_oos.file_oos_annotate_main` in-process under stdout and stderr capture.
- Do not change `design_oos.py` prepare or annotate semantics.
- Keep the Bash files as thin compatibility wrappers because they remain live launcher targets in `skills/design/SKILL.md`.
- Do not add migrated-script manifest rows for live thin wrappers. Add manifest rows only if a follow-up hard-deletes the wrapper files and updates all references.

**Bash parity, `DESIGN_TMPDIR` guards:** Do not call `_require_design_tmpdir` in Step 5b entrypoints. That helper requires an absolute, existing directory; today's Bash only rejects an empty `DESIGN_TMPDIR`. Prepare then runs `mkdir -p "$DESIGN_TMPDIR/.completed"`, which can create a missing tmpdir root. Add a small `_require_design_tmpdir_nonempty(env) -> Path` helper that rejects only empty values (same stderr message style as prepare/annotate wrappers) and returns `Path(raw)` without `is_absolute()` or `is_dir()` checks.

**Bash parity, in-process failure boundary:** Add `_capture_stdout_stderr(callable_obj, argv, *, stderr_path: Path) -> tuple[int, str]` that preserves today's subprocess boundary:
- redirect stdout to a string buffer
- redirect stderr to the target log file (truncate/create like Bash `2>`)
- treat a normal return value as `int(rc)`
- catch `SystemExit` and use `exc.code` when it is an `int`, else `1`
- catch any other `BaseException`, write `traceback.format_exc()` to the stderr log file, return `1`
- never let callable crashes escape `step5b_prepare_main` / `step5b_annotate_main` before the existing non-zero branches emit `STEP5B_STATUS`, `OOS_*` rows, and completion sentinels

Reuse `_capture_stdout` only where exception swallowing is not required; Step 5b prepare and annotate must use `_capture_stdout_stderr`.

**Wrapper env binding:** Both Step 5b mains must assign `env = _rehydrate_wrapper_env(parsed)` immediately after `_parse_common_wrapper_args`. Use that returned `env` mapping for `_require_design_tmpdir_nonempty(env)` and for any other reads of session keys before touching `os.environ` directly. `_rehydrate_wrapper_env` still exports into `os.environ` for `_call_pause_save` and `_maybe_timing_mark`.

## Files to modify/create

### UPDATED: python/design_lifecycle.py

Add Step 5b helpers near the existing Step 2 lifecycle helpers.

Implementation details:

- Add `_require_design_tmpdir_nonempty(env: Mapping[str, str], *, site: str) -> Path`:
  - read `DESIGN_TMPDIR` from `env`
  - if empty, print `/design Step 5b prepare: DESIGN_TMPDIR required` or `/design Step 5b annotate: DESIGN_TMPDIR required` (site-specific message) and raise `SystemExit(1)`
  - return `Path(raw)` with no absolute/existence validation
- Add `_capture_stdout_stderr(callable_obj, argv, *, stderr_path: Path) -> tuple[int, str]` per the failure-boundary rules above
- Add a small helper for Step 5b completion:
  - `mkdir(parents=True, exist_ok=True)` on `$DESIGN_TMPDIR/.completed`
  - touch `step-5b`
- Add `step5b_prepare_main(argv)`:
  - parse with `_parse_common_wrapper_args`
  - bind `env = _rehydrate_wrapper_env(parsed)`
  - require plugin root
  - bind `design_tmpdir = _require_design_tmpdir_nonempty(env, site="prepare")` (not `_require_design_tmpdir`)
  - `mkdir(parents=True, exist_ok=True)` on `design_tmpdir / ".completed"` before touching `step-4b` (matches Bash `mkdir -p`)
  - touch `.completed/step-4b`
  - if `.pause-requested` exists, return `_call_pause_save(design_tmpdir)` immediately (do not continue into prepare work)
  - call `_maybe_timing_mark("design Step 5 — finalize")`
  - run `design_oos.file_oos_prepare_main(["--design-tmpdir", str(design_tmpdir), "--issue-number", env.get("ISSUE_NUMBER", "") if present])` inside `_capture_stdout_stderr` with stderr at `oos-filing-prepare.stderr.log`
  - write captured stdout to `oos-filing-prepare.env`
  - on non-zero prepare rc:
    - append run-log failure when stderr log is non-empty
    - print the current warning line
    - emit `STEP5B_STATUS=prepare-failed-continue`
    - emit `OOS_PREP_RC=<rc>`
    - emit `OOS_ISSUE_STDOUT_PATH=<tmpdir>/oos-issue.stdout.txt`
    - mark `.completed/step-5b`
    - return 0
  - parse captured stdout with `_parse_stdout_kv`
  - replay pass-through `FILE_DESIGN_OOS_*` rows and `WARN=` rows exactly as the wrapper does now
  - emit:
    - `STEP5B_STATUS=<FILE_DESIGN_OOS_STATUS>`
    - `OOS_PREP_RC=0`
    - `OOS_ISSUE_STDOUT_PATH=<tmpdir>/oos-issue.stdout.txt`
    - optional combined/deps/deps-available rows
  - emit `STEP5B_NEEDS_ANNOTATE=true` for `ready` and `skip-already-filed-sentinel`
  - mark `.completed/step-5b` for `skip-sentinel`, `skip-no-items`, and `skip-all-security`
- Add `step5b_annotate_main(argv)`:
  - parse with `_parse_common_wrapper_args`
  - bind `env = _rehydrate_wrapper_env(parsed)`
  - require plugin root
  - bind `design_tmpdir = _require_design_tmpdir_nonempty(env, site="annotate")` (same non-empty-only guard as Bash annotate prelude)
  - bind `oos_issue_stdout = design_tmpdir / "oos-issue.stdout.txt"` immediately after the tmpdir guard (Bash parity: `design-step5b-annotate.sh` line 91)
  - if `.pause-requested` exists, return `_call_pause_save(design_tmpdir)` immediately (do not continue into annotate work; matches Bash `exec` handoff at `design-step5b-annotate.sh` line 90)
  - call `design_oos.file_oos_annotate_main(["--design-tmpdir", str(design_tmpdir), "--issue-stdout-file", str(oos_issue_stdout), "--issue-number", env.get("ISSUE_NUMBER", "") if present])` inside `_capture_stdout_stderr` with stderr at `oos-filing-annotate.stderr.log`
  - capture stdout to `oos-filing-annotate.stdout.txt`
  - print captured stdout
  - emit `OOS_ANN_RC=<rc>`
  - parse `FILE_DESIGN_OOS_STATUS` and `WARN`
  - on non-zero rc:
    - detect `ISSUES_FAILED=[1-9][0-9]*` by reading `oos_issue_stdout` (same path as `--issue-stdout-file`; Bash `grep` parity at `design-step5b-annotate.sh` line 111)
    - append run-log failure when stderr log is non-empty
    - print the partial-failure warning when applicable
    - emit `STEP5B_STATUS=annotate-failed`
    - return the annotate rc
  - on zero rc with `FILE_DESIGN_OOS_STATUS=annotate-skipped-empty-stdout` and a warning:
    - append a `Warnings` run-log entry
    - print the current skipped-annotate warning
  - mark `.completed/step-5b`
  - emit `STEP5B_STATUS=annotate-complete`
  - return 0
- Use existing `_append_failure`, `_parse_stdout_kv`, `_maybe_timing_mark`, and `_call_pause_save` where practical

### UPDATED: python/cli.py

- Add registry rows:
  - `("design", "step5b-prepare"): ("design_lifecycle", "step5b_prepare_main")`
  - `("design", "step5b-annotate"): ("design_lifecycle", "step5b_annotate_main")`
- Add both keys to `_DESIGN_LIFECYCLE_STDOUT_KEYS`.

### UPDATED: skills/design/scripts/design-step5b-prepare.sh

Replace the fat body with a thin delegation wrapper.

Keep it minimal:

- derive `CLAUDE_PLUGIN_ROOT` from the environment or from the script location
- export `CLAUDE_PLUGIN_ROOT`
- exec:
  - `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design step5b-prepare "$@"`

### UPDATED: skills/design/scripts/design-step5b-annotate.sh

Replace the fat body with a thin delegation wrapper.

Keep it minimal:

- derive `CLAUDE_PLUGIN_ROOT` from the environment or from the script location
- export `CLAUDE_PLUGIN_ROOT`
- exec:
  - `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design step5b-annotate "$@"`

### UPDATED: skills/design/scripts/design-step5.sh

Update only the final delegation target.

- Keep the legacy argument parser unless the edit can safely remove it.
- Replace the final exec of `design-step5b-prepare.sh` with:
  - `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design step5b-prepare "${_delegate_args[@]}"`

### UPDATED: skills/design/scripts/design-step5.md

Update the sibling doc in the same PR as the `design-step5.sh` delegation change (script-md-siblings rule).

- State that `design-step5.sh` remains a deprecated compatibility wrapper for older paused `/design` sessions.
- Update **Invariants** so the live delegation target is direct `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design step5b-prepare` with reconstructed `--session-env-path` and `--claude-pid` flags, not `design-step5b-prepare.sh`.
- Note that `design-step5b-prepare.sh` remains a thin launcher-compat wrapper for `skills/design/SKILL.md` fences; behavior lives in `python/cli.py design step5b-prepare`.
- Preserve existing invariants about optional session-env sourcing, `CLAUDE_PLUGIN_ROOT` validation, and not deriving the root Claude PID from `$PPID` internally.

### UPDATED: python/test_design_oos.py

Add orchestration tests without changing `design_oos.py` behavior.

Cover:

- prepare ready:
  - monkeypatch `design_lifecycle.design_oos.file_oos_prepare_main`
  - assert `oos-filing-prepare.env` is written
  - assert `STEP5B_STATUS=ready`
  - assert `STEP5B_NEEDS_ANNOTATE=true`
  - assert `.completed/step-5b` is not written
- prepare skip:
  - status `skip-no-items`
  - assert `.completed/step-5b` is written
- prepare failure:
  - fake rc non-zero and stderr
  - assert warning and `STEP5B_STATUS=prepare-failed-continue`
  - assert `.completed/step-5b` is written
- prepare tmpdir guard parity:
  - set `DESIGN_TMPDIR` to a non-empty relative path that does not exist yet
  - monkeypatch prepare callable to return success
  - assert prepare does not fail at guard
  - assert `.completed` (and thus tmpdir root) is created before `step-4b`
- prepare pause:
  - touch `.pause-requested` before prepare work
  - monkeypatch `_call_pause_save` to return a non-zero rc
  - assert `file_oos_prepare_main` is not called
  - assert return rc matches pause-save rc
- prepare callable crash:
  - monkeypatch `file_oos_prepare_main` to raise `RuntimeError`
  - assert `oos-filing-prepare.stderr.log` contains traceback text
  - assert `STEP5B_STATUS=prepare-failed-continue` and `.completed/step-5b` is written
- annotate success:
  - fake `FILE_DESIGN_OOS_STATUS=annotate-complete`
  - assert stdout capture file is written
  - assert `.completed/step-5b` is written
  - assert `STEP5B_STATUS=annotate-complete`
- annotate failure:
  - fake non-zero rc
  - assert `STEP5B_STATUS=annotate-failed`
  - assert `.completed/step-5b` is not written
- annotate failure with partial issue stdout:
  - write `ISSUES_FAILED=1` into `design_tmpdir / "oos-issue.stdout.txt"` before annotate
  - fake non-zero annotate rc
  - assert partial-failure warning is printed
  - assert `file_oos_annotate_main` received `--issue-stdout-file` pointing at that same path
- annotate pause:
  - touch `.pause-requested` before annotate work
  - monkeypatch `_call_pause_save` to return a non-zero rc
  - assert `file_oos_annotate_main` is not called
  - assert return rc matches pause-save rc
- annotate callable crash:
  - monkeypatch `file_oos_annotate_main` to raise `RuntimeError`
  - assert stderr log contains traceback
  - assert `STEP5B_STATUS=annotate-failed` and `.completed/step-5b` is not written

### UPDATED: python/test_design_cli_ports.py

- Add the new verbs to `EXPECTED`:
  - `step5b-prepare`
  - `step5b-annotate`
- Keep the machine-stdout assertion.

### UPDATED: skills/design/scripts/design-step5b-prepare.md

Update the docs to state that the `.sh` file is now a thin wrapper and that `python/cli.py design step5b-prepare` owns the behavior. Document the non-empty-only `DESIGN_TMPDIR` guard, `.completed` mkdir parity with the retired Bash prelude, `env = _rehydrate_wrapper_env(parsed)` binding, and immediate return on `.pause-requested`.

### UPDATED: skills/design/scripts/design-step5b-annotate.md

Update the docs to state that the `.sh` file is now a thin wrapper and that `python/cli.py design step5b-annotate` owns the behavior. Document the non-empty-only `DESIGN_TMPDIR` guard matching Bash annotate, `oos_issue_stdout = design_tmpdir / "oos-issue.stdout.txt"` binding immediately after the guard (Bash `_oos_issue_stdout` parity), and immediate halt after pause-save when `.pause-requested` exists.

## Edge cases

- **Pause request (prepare):** preserve pause-save before prepare work starts; return pause-save rc immediately and do not call `file_oos_prepare_main`.
- **Pause request (annotate):** preserve pause-save before annotate work starts; return pause-save rc immediately and do not call `file_oos_annotate_main` (Bash `exec` parity).
- **Empty `DESIGN_TMPDIR`:** fail closed with the existing wrapper message style; do not fall through to `mkdir`.
- **Non-empty but missing tmpdir root (prepare):** `mkdir(parents=True, exist_ok=True)` on `.completed` creates the root, matching Bash `mkdir -p`.
- **Relative `DESIGN_TMPDIR`:** allowed on both prepare and annotate, matching Bash; do not upgrade to `_require_design_tmpdir` absoluteness checks in this slice.
- **`oos_issue_stdout` binding (annotate):** always set `oos_issue_stdout = design_tmpdir / "oos-issue.stdout.txt"` after the tmpdir guard; use that single `Path` for `--issue-stdout-file` and for `ISSUES_FAILED` detection on failure so annotate I/O cannot diverge from Bash.
- **Prepare failure:** continue to Step 5c and mark Step 5b complete, matching current wrapper behavior.
- **Ready prepare:** do not mark Step 5b complete until annotate succeeds.
- **Already-filed sentinel:** keep `STEP5B_NEEDS_ANNOTATE=true`.
- **Annotate failure:** return non-zero and do not write `.completed/step-5b`.
- **Callable crash inside `design_oos`:** `_capture_stdout_stderr` writes traceback to the stderr log, returns rc `1`, and lets the existing non-zero branches emit the same stdout contract as a subprocess failure.
- **Empty issue stdout:** preserve warning and run-log behavior.
- **Missing plugin root:** fail closed with the existing wrapper message style.
- **Stale env mapping:** always bind `env = _rehydrate_wrapper_env(parsed)` before reading `DESIGN_TMPDIR` or `ISSUE_NUMBER` from the rehydrated wrapper env.
- **Sibling doc drift:** update `design-step5.md` whenever `design-step5.sh` delegation changes so the documented compatibility path matches the shipped exec target.

## Failure modes

- **Run-log append can fail:** keep it best-effort and do not mask the Step 5b control-flow result.
- **Captured stderr can be empty:** do not append a failure entry that points at an empty stderr log; callable crashes should still populate the stderr log via traceback before the non-zero branch runs.
- **Malformed KV output:** ignore unrelated lines, as the Bash case parser does now.
- **Uncaught exception escaping Step 5b mains:** prevented by `_capture_stdout_stderr`; if it regresses, prepare/annotate can exit before `STEP5B_STATUS` or sentinel writes.
- **Unbound `env` after rehydrate:** prevented by assigning `env = _rehydrate_wrapper_env(parsed)` in both mains; if it regresses, tmpdir guard or issue-number forwarding can raise `NameError` or read stale values.
- **Unbound `oos_issue_stdout` in annotate:** prevented by binding `oos_issue_stdout = design_tmpdir / "oos-issue.stdout.txt"` immediately after the annotate tmpdir guard; if it regresses, annotate can `NameError` or pass the wrong `--issue-stdout-file` while `ISSUES_FAILED` detection reads a different path.
- **Annotate continues after pause-save:** prevented by immediate return on `.pause-requested`; if it regresses, annotate can run while a pause is pending.
- **Stale `design-step5.md`:** if omitted, the script-md-siblings contract documents the wrong delegation target and misleads resume/debug paths for legacy sessions.

## Testing strategy

Run:

- `python3 -m pytest python/test_design_oos.py`
- `python3 -m pytest python/test_design_cli_ports.py`
- `make py-lint`
- `make py-test`
- `make lint`

Also run the existing structure harness if the implementer touches launcher or wrapper shape:

- `scripts/test-design-structure.sh`

## Notes

- Do not port Step 5c, Step 6, final summary, clarify, or failure-report bodies in this slice.
- Do not change `design_oos.file_oos_prepare_main` or `design_oos.file_oos_annotate_main`.
- Do not add `python/migrated-scripts.tsv` rows while the wrapper files remain live.
diff_added: 340
diff_deleted: 275
mechanical_churn: true
diff_lines: 615

## Acceptance

- `step5b_prepare_main` and `step5b_annotate_main` added to `python/design_lifecycle.py` with all Bash-contract behaviors preserved
- `("design", "step5b-prepare")` and `("design", "step5b-annotate")` registered in `python/cli.py` `_REGISTRY` and `_MACHINE_STDOUT_KEYS`
- `design-step5b-prepare.sh`, `design-step5b-annotate.sh`, and `design-step5.sh` replaced with thin wrappers delegating to `python3 cli.py design step5b-{prepare,annotate}`
- `design-step5.md` updated to reflect new delegation target
- `python/test_design_oos.py` covers all orchestration scenarios including crash paths, pause, and tmpdir guard parity
- `python/test_design_cli_ports.py` has entries for both new verbs
- `make py-lint`, `make py-test`, and `make lint` all pass

review_status: complete
rounds_completed: 5
diff_lines: 615
