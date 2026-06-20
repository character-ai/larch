## Plan

Port Step 6 with parity only.

- Add three Python entrypoints:
  - `python/cli.py design step6`
  - `python/cli.py design step6-prelude`
  - `python/cli.py design step6-cleanup`
- Mirror the current shell behavior:
  - Combined flow rehydrates session env before touching `.pause-save-complete`, removes the marker from the resolved tmpdir only when `design_tmpdir_raw` is non-empty, runs prelude, exits early if `.pause-save-complete` reappears after prelude (non-empty tmpdir only), then runs cleanup.
  - Prelude and cleanup run pause/in-flight/sidecar gates before any plugin-root requirement.
  - Prelude writes `.completed/step-5d` only after Step 5c sidecar gates pass.
  - Cleanup writes `.completed/step-6` after pause-check and before `session cleanup-tmpdir`, and only on the deletion-eligible path (all preserve gates must pass first).
  - Missing sidecar preserves tmpdir and exits 0.
  - `.bg-wait-active` plus missing sidecar exits 1 with the existing stderr diagnostic **only when `design_tmpdir_raw` is non-empty** (shell conjunct at `design-step6-prelude.sh:96-98` and `design-step6-cleanup.sh:96-98`).
  - `PLAN_WRITE_OK`, `PUBLISH_OK`, `STANDALONE_HEAVY_FAILED`, and `CLEANUP_ELIGIBLE` preserve the same skip/preserve paths in **both** prelude and cleanup.
  - Pause requests call `design_pause.pause_save_main` before in-flight checks.
  - The timing mark remains `design Step 6 — cleanup` and stays best-effort (`|| true` parity).
  - Skip/preserve paths must **not** hard-validate `DESIGN_TMPDIR`; only the cleanup-deletion path validates before tmpdir removal.
  - **Never construct `Path("")` for Step 6 probes** — empty rehydrated `DESIGN_TMPDIR` must fall through to missing-sidecar skip/preserve with rc 0, not cwd-relative marker checks.

## Files to modify/create

### UPDATED: python/design_lifecycle.py

Add Step 6 helpers near `step5c_main` or the Step 5/6 lifecycle cluster.

- Add `_read_step5c_status_sidecar(design_tmpdir: Path) -> dict[str, str]` using `_read_simple_env` with allowlisted keys only:
  - `PLAN_WRITE_OK`
  - `PUBLISH_OK`
  - `STANDALONE_HEAVY_FAILED`
  - `SESSION_ID`
  - `PUBLISH_RC`
  - `PUBLISH_STDOUT_FALLBACK`
  - `CLEANUP_ELIGIBLE`
  - Do not shell-source the file.
- Add `_resolve_design_tmpdir_raw(env: Mapping[str, str]) -> str`.
  - Return `env.get("DESIGN_TMPDIR", "")` unchanged.
  - Do **not** call `_validate_design_tmpdir_arg` here.
  - Match shell: empty or unset `DESIGN_TMPDIR` after rehydration is allowed to reach missing-sidecar skip/preserve branches with rc 0.
- Add `_design_tmpdir_path_or_none(design_tmpdir_raw: str) -> Path | None`.
  - Return `Path(design_tmpdir_raw)` only when `design_tmpdir_raw` is non-empty.
  - Return `None` when empty; callers must not coerce `None` to `Path("")` (which resolves to cwd and breaks parity).
- Add `_step6_sidecar_path(design_tmpdir_raw: str) -> Path | None`.
  - Return `Path(design_tmpdir_raw) / ".design-step5c-status.env"` when `design_tmpdir_raw` is non-empty; else `None`.
- Add `_step6_in_flight(design_tmpdir_raw: str) -> bool`.
  - Exact shell predicate: sidecar path absent **and** `design_tmpdir_raw` non-empty **and** `(Path(design_tmpdir_raw) / ".bg-wait-active").is_file()`.
  - When `design_tmpdir_raw` is empty, return `False` immediately without any `Path` construction.
- Add `step6_prelude_core(argv)` and `step6_prelude_main(argv)`.
  - Reuse `_parse_common_wrapper_args`, `_rehydrate_wrapper_env`, `_call_pause_save`, `_touch`, and `_maybe_timing_mark`.
  - Do **not** call `_validate_design_tmpdir_arg` or `_design_require_plugin_root` at entry. Match shell: run pause, in-flight, and sidecar-existence gates first.
  - After rehydration, bind `design_tmpdir_raw = _resolve_design_tmpdir_raw(env)`.
  - **Empty-tmpdir rule:** when `design_tmpdir_raw` is empty, do not construct `Path("")` for `.pause-requested`, `.bg-wait-active`, `.design-step5c-status.env`, `.pause-save-complete`, or `.completed/*` probes. After the first pause check, emit the missing-sidecar skip rows and exit 0.
  - **Non-empty tmpdir only:** use `_design_tmpdir_path_or_none(design_tmpdir_raw)` for marker and sentinel path operations.
  - After `.design-step5c-status.env` exists, bind gate decisions **exclusively** from `_read_step5c_status_sidecar` output. Do **not** read `PLAN_WRITE_OK`, `PUBLISH_OK`, `STANDALONE_HEAVY_FAILED`, or `CLEANUP_ELIGIBLE` from `os.environ` for gate logic; `_rehydrate_wrapper_env` may seed stale session-env values that disagree with Step 5c's authoritative sidecar.
  - Preserve the current message text and rows:
    - `STEP6_PRELUDE_STATUS=skipped`
    - `**⚠ Step 6 prelude: design-step5c.sh appears still in-flight (.bg-wait-active present); do not proceed until <task-notification> fires.**`
    - all existing informational skip lines.
  - Gate order after first pause check:
    1. `_step6_in_flight(design_tmpdir_raw)` → stderr diagnostic, exit 1
    2. sidecar missing (`_step6_sidecar_path` is `None` or not a file) → missing-sidecar skip, exit 0
    3. parse sidecar; apply prelude gates using sidecar-bound values:
       - `PLAN_WRITE_OK != true`
       - `SESSION_ID` non-empty and `PUBLISH_OK != true`
       - `CLEANUP_ELIGIBLE == false`
  - Touch `.completed/step-5d` before the second pause check (non-empty tmpdir only).
  - After the second pause check, call `_maybe_timing_mark("design Step 6 — cleanup")` directly with no preceding `_design_require_plugin_root`. Timing remains best-effort like the shell `|| true` path.
- Add `step6_cleanup_core(argv)` and `step6_cleanup_main(argv)`.
  - Reuse `_parse_common_wrapper_args`, `_rehydrate_wrapper_env`, `_call_pause_save`, `_touch`, and `_design_require_plugin_root`.
  - **Empty-tmpdir rule:** same as prelude — no `Path("")` construction; after first pause check, emit missing-sidecar preserve rows and exit 0.
  - After `.design-step5c-status.env` exists, bind gate decisions **exclusively** from `_read_step5c_status_sidecar` output, not from rehydrated `os.environ`.
  - Preserve the current message text and row:
    - `CLEANUP_STATUS=preserved`
    - `**⚠ Step 6: design-step5c.sh appears still in-flight (.bg-wait-active present); do not proceed until <task-notification> fires.**`
    - all existing preserve lines (verbatim from `design-step6-cleanup.sh`):
      - `**ℹ Step 6: missing Step 5c status sidecar; preserving $DESIGN_TMPDIR for recovery.**`
      - `**ℹ Step 6: plan write did not succeed; preserving $DESIGN_TMPDIR.**`
      - `**ℹ Step 6: standalone heavy failed; preserving $DESIGN_TMPDIR.**`
      - `**ℹ Step 6: publish did not complete; preserving $DESIGN_TMPDIR for recovery.**`
      - `**ℹ Step 6: cleanup not eligible per Step 5c status; preserving $DESIGN_TMPDIR.**`
  - Gate order after first pause check:
    1. `_step6_in_flight(design_tmpdir_raw)` → stderr diagnostic, exit 1
    2. sidecar missing → `CLEANUP_STATUS=preserved`, exit 0
    3. parse sidecar; apply cleanup preserve gates in **exact shell order** using sidecar-bound values:
       - `PLAN_WRITE_OK != true`
       - `STANDALONE_HEAVY_FAILED == true`
       - `SESSION_ID` non-empty and `PUBLISH_OK != true`
       - `CLEANUP_ELIGIBLE == false`
  - Only when all preserve gates pass:
    - call `_validate_design_tmpdir_arg(design_tmpdir_raw)` immediately before `_design_require_plugin_root`
    - touch `.completed/step-6`
    - call `_design_require_plugin_root`
    - invoke `session_env.cleanup_tmpdir_main(["--dir", str(design_tmpdir)])`
  - Do **not** touch `step-6`, validate tmpdir, or call cleanup on any preserve branch.
- Add `step6_main(argv)`.
  - Parse argv with `_parse_common_wrapper_args`.
  - Call `_rehydrate_wrapper_env` and resolve `design_tmpdir_raw = _resolve_design_tmpdir_raw(env)` **before** reading or removing `.pause-save-complete`.
  - Do **not** call `_validate_design_tmpdir_arg` in the combined entrypoint.
  - Remove `.pause-save-complete` from `Path(design_tmpdir_raw)` **only when** `design_tmpdir_raw` is non-empty and the marker is present (shell: `[ -n "${DESIGN_TMPDIR:-}" ] && rm -f ...`).
  - Run `step6_prelude_core(argv)`.
  - Return the prelude rc if non-zero.
  - Return 0 when `design_tmpdir_raw` is non-empty and `.pause-save-complete` exists on that tmpdir after prelude (shell: `[ -n "${DESIGN_TMPDIR:-}" ] && [ -f "$DESIGN_TMPDIR/.pause-save-complete" ]`).
  - Otherwise run `step6_cleanup_core(argv)`.
- Initialize quiet mode in the three `*_main` wrappers with argv0 values matching the retired basenames:
  - `design-step6.sh`
  - `design-step6-prelude.sh`
  - `design-step6-cleanup.sh`

### UPDATED: python/cli.py

Register the new verbs.

- Add registry rows:
  - `("design", "step6"): ("design_lifecycle", "step6_main")`
  - `("design", "step6-prelude"): ("design_lifecycle", "step6_prelude_main")`
  - `("design", "step6-cleanup"): ("design_lifecycle", "step6_cleanup_main")`
- Add all three to `_DESIGN_LIFECYCLE_STDOUT_KEYS` so status rows stay visible under quiet mode.

### UPDATED: python/session_env.py

Update the design-run launcher text.

- Route retired Step 6 basenames to Python:
  - `design-step6.sh` -> `python/cli.py design step6`
  - `design-step6-prelude.sh` -> `python/cli.py design step6-prelude`
  - `design-step6-cleanup.sh` -> `python/cli.py design step6-cleanup`
- Add bare verbs to the ported-design allowlist:
  - `step6`
  - `step6-prelude`
  - `step6-cleanup`
- Add an explicit `step6|step6-prelude|step6-cleanup)` case arm to `_design_run_launcher_text` that execs `python3 "$PLUGIN_ROOT/python/cli.py" design "$script"` (mirror the step0 bare-verb case), using the same `--session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"` forwarding pattern used by other ported design wrappers. Without this arm, a bare `step6` invocation falls through to the default `*)` `ERROR=unknown design wrapper verb` branch and cleanup never runs.

### UPDATED: python/test_design_lifecycle.py

Port `skills/design/scripts/test-design-step6.sh` into pytest.

Cover the five shell harness cases:

- Prelude in-flight guard:
  - `.bg-wait-active` present.
  - no `.design-step5c-status.env`.
  - **non-empty** `DESIGN_TMPDIR`.
  - rc 1.
  - diagnostic on stderr.
  - no `STEP6_PRELUDE_STATUS=skipped`.
- Cleanup in-flight guard:
  - same setup.
  - no `CLEANUP_STATUS=preserved`.
- Missing sidecar:
  - prelude rc 0 with `STEP6_PRELUDE_STATUS=skipped`.
  - cleanup rc 0 with `CLEANUP_STATUS=preserved`.
  - no in-flight diagnostic.
  - unset `CLAUDE_PLUGIN_ROOT` to prove skip/preserve paths do not require plugin root at entry.
- Stale `.bg-wait-active` plus sidecar:
  - sidecar wins.
  - `PLAN_WRITE_OK=false` preserves/skips with rc 0 on **both** prelude and cleanup (shell harness D4).
  - cleanup emits `CLEANUP_STATUS=preserved` and the plan-write preserve message; must not call `cleanup_tmpdir_main`.
- Pause wins over in-flight:
  - `.pause-requested` and `.bg-wait-active` present.
  - monkeypatch `design_pause.pause_save_main`.
  - both prelude and cleanup call pause-save and skip in-flight diagnostics.

Add focused positive-path tests:

- Prelude writes `.completed/step-5d`, then honors a pause request if one appears before the second pause check.
- Cleanup writes `.completed/step-6` before cleanup.
  - Monkeypatch `session_env.cleanup_tmpdir_main`.
  - Assert the sentinel exists when the cleanup function is called.
- Combined `step6_main` skips cleanup when prelude produces `.pause-save-complete`.
- Combined `step6_main` removes a stale `.pause-save-complete` before prelude.
  - Invoke `step6_main` through `--session-env-path` only.
  - Do not pre-set `DESIGN_TMPDIR` in the process environment.
  - Seed a stale `.pause-save-complete` in the session-env tmpdir and assert cleanup still runs when prelude does not recreate the marker.

Add sidecar-authority regression tests:

- Seed `.design-step5c-status.env` with `PLAN_WRITE_OK=false` while rehydrated session env carries conflicting `PLAN_WRITE_OK=true`.
  - Assert prelude/cleanup skip/preserve per sidecar, not session env.
- Seed sidecar with `PLAN_WRITE_OK=true`, `PUBLISH_OK=false`, non-empty `SESSION_ID`.
  - Assert cleanup preserves with publish-failure message; no `step-6` sentinel; no `cleanup_tmpdir_main` call.
- Seed sidecar with `PLAN_WRITE_OK=true`, `CLEANUP_ELIGIBLE=false`.
  - Assert cleanup preserves with cleanup-ineligible message; no deletion path.
- Seed sidecar with `PLAN_WRITE_OK=true`, `STANDALONE_HEAVY_FAILED=true`.
  - Assert cleanup preserves before publish/cleanup-eligible checks would matter.

Add tmpdir-validation deferral regression tests:

- Rehydrate with empty `DESIGN_TMPDIR` and no sidecar.
  - Assert prelude emits `STEP6_PRELUDE_STATUS=skipped` and cleanup emits `CLEANUP_STATUS=preserved` with rc 0.
  - Assert no usage error from `_validate_design_tmpdir_arg`.
- On deletion-eligible path only, assert `_validate_design_tmpdir_arg` is called immediately before `_design_require_plugin_root` and `cleanup_tmpdir_main`.

Add empty-tmpdir in-flight guard regression tests (FINDING_1):

- Rehydrate with empty `DESIGN_TMPDIR`, no sidecar, and `.bg-wait-active` present in **process cwd** (not under any design tmpdir).
  - Assert prelude rc 0 with `STEP6_PRELUDE_STATUS=skipped`, cleanup rc 0 with `CLEANUP_STATUS=preserved`.
  - Assert no in-flight stderr diagnostic on either path.
  - Assert `_step6_in_flight("")` is `False` and no `Path("")` marker probes run (monkeypatch or spy on path construction if needed).
- Rehydrate with **non-empty** tmpdir, no sidecar, `.bg-wait-active` under that tmpdir.
  - Assert prelude/cleanup rc 1 with in-flight diagnostic (harness D1/D2 parity).

### UPDATED: python/test_upgrade_larch.py

Remove retired-path literals before adding the Step 6 manifest rows.

- In `_populate_cleanup_fixture`, replace the `test-design-step6.sh` / `.md` fixture paths with a live non-retired harness such as `skills/design/scripts/test-design-step5c.sh`.
  - Do not embed the retired full path literal in source.
- In `test_clean_test_files_from_cache_removes_dev_test_infrastructure`, update the matching `removed` expectation tuple to the same live harness path.
- Drop the `.md` companion expectation if no tracked doc exists for the replacement harness.

### UPDATED: Makefile

Change `test-design-step6` to run pytest instead of the deleted shell harness.

- Use:
  - `python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_design_lifecycle.py -k step6`
- Leave unrelated harness targets unchanged.

### UPDATED: skills/design/SKILL.md

Update Step 6 references only.

- In the retired-script/reference list:
  - remove `test-design-step6.sh`
  - remove `_dbg5c2.sh`
  - remove `_dbg-validator.sh`
  - remove the three `design-step6*.sh` paths
  - remove the three `design-step6*.md` paths
  - add the Python Step 6 authorities.
- Change the Step 6 fence to invoke the ported launcher verb:
  - `"$HOME/.cache/larch/sessions/design-run-$PPID.sh" step6`
- Keep the sentinel table text intact, especially:
  - `step-5d` before pause-check.
  - `step-6` after pause-check.

### UPDATED: scripts/test-design-structure.sh

Pin the migration with a dedicated Step 6 block mirroring the Step 2 pattern.

- Add:
  - `step6_verbs='step6 step6-prelude step6-cleanup'`
  - `step6_retired_paths='design-step6.sh design-step6.md design-step6-prelude.sh design-step6-prelude.md design-step6-cleanup.sh design-step6-cleanup.md test-design-step6.sh _dbg-validator.sh _dbg5c2.sh'`
- Loop `step6_verbs` for:
  - `python/cli.py` registry `("design", "<verb>")` pins
  - `_DESIGN_LIFECYCLE_STDOUT_KEYS` pins
  - `python/session_env.py` bare-verb allowlist tokens
- Loop `step6_retired_paths` for:
  - absent-on-disk checks
  - `python/migrated-scripts.tsv` rows
  - `skills/design/SKILL.md` must not reference deleted Step 6/debug script paths
- Add explicit `contains` pins for retired `.sh` basename mappings in `python/session_env.py`, mirroring the Step 2 block:
  - `design-step6.sh)` -> `design step6 --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"`
  - `design-step6-prelude.sh)` -> `design step6-prelude --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"`
  - `design-step6-cleanup.sh)` -> `design step6-cleanup --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"`
- Pin `skills/design/SKILL.md` Step 6 fence uses bare `step6` launcher verb.

### UPDATED: python/migrated-scripts.tsv

Add rows for deleted Step 6 and debug files, using `#4678` (this implementation issue) in column 2:

- `skills/design/scripts/design-step6.sh`
- `skills/design/scripts/design-step6.md`
- `skills/design/scripts/design-step6-prelude.sh`
- `skills/design/scripts/design-step6-prelude.md`
- `skills/design/scripts/design-step6-cleanup.sh`
- `skills/design/scripts/design-step6-cleanup.md`
- `skills/design/scripts/test-design-step6.sh`
- `skills/design/scripts/_dbg-validator.sh`
- `skills/design/scripts/_dbg5c2.sh`

### UPDATED: skills/design/scripts/design-step6.sh

Delete this retired wrapper after the Python `design step6` entrypoint is tested.

### UPDATED: skills/design/scripts/design-step6.md

Delete this retired wrapper doc.

### UPDATED: skills/design/scripts/design-step6-prelude.sh

Delete this retired wrapper after the Python `design step6-prelude` entrypoint is tested.

### UPDATED: skills/design/scripts/design-step6-prelude.md

Delete this retired wrapper doc.

### UPDATED: skills/design/scripts/design-step6-cleanup.sh

Delete this retired wrapper after the Python `design step6-cleanup` entrypoint is tested.

### UPDATED: skills/design/scripts/design-step6-cleanup.md

Delete this retired wrapper doc.

### UPDATED: skills/design/scripts/test-design-step6.sh

Delete this retired shell harness after its cases land in `python/test_design_lifecycle.py`.

### UPDATED: skills/design/scripts/_dbg-validator.sh

Delete this retired debug scaffold.

### UPDATED: skills/design/scripts/_dbg5c2.sh

Delete this retired debug scaffold.

## Edge cases

- **Rehydrate before pause-complete:** `step6_main` must parse argv and rehydrate session env before removing or honoring `.pause-save-complete`.
- **No entry tmpdir validation:** Prelude, cleanup, and combined entry must resolve raw `DESIGN_TMPDIR` from rehydrated env without calling `_validate_design_tmpdir_arg`. Empty tmpdir must reach missing-sidecar skip/preserve branches with rc 0, matching shell.
- **No `Path("")` construction:** When `design_tmpdir_raw` is empty, never build `Path("")` for `.bg-wait-active`, `.design-step5c-status.env`, `.pause-save-complete`, `.pause-requested`, or `.completed/*`. `Path("")` resolves to cwd in Python; shell `"$DESIGN_TMPDIR/..."` with empty tmpdir probes under `/`, not cwd. Stray cwd markers must not steer Step 6 branches.
- **In-flight requires non-empty tmpdir:** Fatal in-flight exit 1 fires only when sidecar is missing, `design_tmpdir_raw` is non-empty, and `.bg-wait-active` exists under that tmpdir. Empty tmpdir plus cwd `.bg-wait-active` must skip/preserve with rc 0.
- **Deletion-only tmpdir validation:** Invalid or empty tmpdir may fail only on the cleanup-deletion path, immediately before `_design_require_plugin_root` and `cleanup_tmpdir_main`.
- **Pause before guards:** Pause must still win over `.bg-wait-active` (pause probe uses the same non-empty tmpdir guard as shell when tmpdir is set).
- **Pause after `step-5d`:** Prelude must still write `step-5d` before the second pause check.
- **Stale background marker:** A valid Step 5c sidecar must override stale `.bg-wait-active` when tmpdir is non-empty.
- **Sidecar over session env:** After the sidecar exists, gate keys must come only from parsed `.design-step5c-status.env`, even when rehydrated session env disagrees.
- **Missing sidecar:** Do not clean up. Exit 0 with preserved/skipped status rows even when `CLAUDE_PLUGIN_ROOT` is unset. Empty tmpdir counts as missing sidecar.
- **Plan write failed:** If sidecar `PLAN_WRITE_OK` is not `true`, prelude skips `step-5d` and cleanup preserves tmpdir (shell lines 107–110).
- **Log publish failed:** If sidecar `SESSION_ID` is non-empty and sidecar `PUBLISH_OK` is not `true`, prelude skips `step-5d` and cleanup preserves tmpdir (shell lines 117–120).
- **Standalone heavy failed:** Preserve tmpdir when sidecar `STANDALONE_HEAVY_FAILED=true` (cleanup only; shell lines 112–115).
- **Cleanup ineligible:** Prelude skips `step-5d` and cleanup preserves tmpdir when sidecar `CLEANUP_ELIGIBLE=false` (shell lines 122–125).
- **Deletion path only:** `step-6` sentinel and `cleanup_tmpdir_main` run only after all five cleanup preserve gates pass; preserve branches must not touch `step-6`.
- **Combined pause resume:** `.pause-save-complete` must stop cleanup only when prelude created it in the current run, using the rehydrated non-empty tmpdir rather than a stale pre-rehydration marker.
- **Best-effort timing:** Prelude timing mark must not hard-fail when `CLAUDE_PLUGIN_ROOT` is unset.

## Failure modes

- **Wrong quiet routing:** Status rows may disappear. Pin the verbs in `_DESIGN_LIFECYCLE_STDOUT_KEYS` and add at least one CLI or main-level stdout test.
- **Sentinel order regression:** Cleanup may delete the tmpdir before `step-6` is visible. Use a monkeypatched cleanup function to assert `step-6` exists before deletion.
- **Incomplete cleanup preserve gates:** Omitting `PLAN_WRITE_OK`, publish-failure, or `CLEANUP_ELIGIBLE` checks in `step6_cleanup_core` would delete recovery artifacts after failed plan write, failed publish, or cleanup-ineligible Step 5c outcomes. Mirror the full shell gate list and order; harness D4 requires cleanup preserve on `PLAN_WRITE_OK=false`.
- **Unsafe sidecar parsing:** Shell-sourcing the Step 5c sidecar would widen trust. Parse allowlisted `KEY=value` rows in Python.
- **Stale session-env gates:** Reading gate keys from `os.environ` after rehydration can preserve or delete `$DESIGN_TMPDIR` incorrectly. Bind gates only from `_read_step5c_status_sidecar`.
- **Early plugin-root abort:** Calling `_design_require_plugin_root` before skip/preserve gates would break missing-sidecar recovery. Require plugin root only on cleanup-deletion path.
- **Early tmpdir validation:** Calling `_validate_design_tmpdir_arg` at prelude/cleanup/combined entry would turn shell rc-0 skip/preserve paths into usage errors when rehydrated `DESIGN_TMPDIR` is empty or invalid. Defer validation to the cleanup-deletion path only.
- **Empty-tmpdir `Path("")` regression:** Constructing `Path("")` for marker probes can turn preserve paths into rc-1 in-flight failures or let cwd artifacts steer gates. Centralize non-empty guards in `_design_tmpdir_path_or_none` and `_step6_in_flight`.
- **Hard timing gate:** Adding `_design_require_plugin_root` before prelude timing would make standalone prelude fail when timing cannot be recorded.
- **Stale pause-complete marker:** Removing or honoring `.pause-save-complete` before session rehydration can skip cleanup incorrectly. Rehydrate first; honor/remove pause-complete only when tmpdir is non-empty.
- **Retired-path literals:** Adding manifest rows before clearing `python/test_upgrade_larch.py` will fail `make lint-retired-scripts`. Update that test before appending the Step 6 manifest rows.
- **Launcher drift:** Saved or generated launchers may still pass `design-step6.sh`. Keep basename mapping in `python/session_env.py` while SKILL.md moves to bare `step6`.
- **Incomplete structure pins:** Omitting `step6_verbs` / basename-forward pins in `test-design-structure.sh` can let registry or launcher drift pass CI.

## Testing strategy

Run focused tests first:

- `python3 -m pytest python/test_design_lifecycle.py -k step6`
- `make test-design-step6`
- `bash scripts/test-design-structure.sh`

Then run required repo checks:

- `make py-lint`
- `make py-test`
- `make lint`

## Acceptance

- `python/design_lifecycle.py` defines `step6_main`, `step6_prelude_core` / `step6_prelude_main`, `step6_cleanup_core` / `step6_cleanup_main`, plus the sidecar reader and tmpdir/path/in-flight helpers; `python/cli.py` registers all three `design step6*` verbs and lists them in `_DESIGN_LIFECYCLE_STDOUT_KEYS`.
- The design-run launcher routes the three retired `design-step6*.sh` basenames and the three bare verbs (`step6`, `step6-prelude`, `step6-cleanup`) to the Python verbs; `skills/design/SKILL.md` Step 6 fence calls bare `step6`.
- Behavioral parity holds: in-flight guard fires only with non-empty tmpdir + missing sidecar + `.bg-wait-active`; empty `DESIGN_TMPDIR` reaches missing-sidecar skip/preserve with rc 0 and never builds `Path("")`; all preserve gates (`PLAN_WRITE_OK`, `STANDALONE_HEAVY_FAILED`, `PUBLISH_OK` with non-empty `SESSION_ID`, `CLEANUP_ELIGIBLE`) are sidecar-bound; pause wins over in-flight; `step-5d` is written before pause-check, `step-6` only on the deletion-eligible path after pause-check and before `session cleanup-tmpdir`; the `design Step 6 — cleanup` timing mark stays best-effort.
- `python/test_design_lifecycle.py` covers the five ported shell harness cases plus the positive-path, sidecar-authority, tmpdir-validation-deferral, and empty-tmpdir in-flight (FINDING_1) regressions.
- The three `design-step6*.sh` wrappers, their `.md` siblings, `test-design-step6.sh`, `_dbg-validator.sh`, and `_dbg5c2.sh` are deleted; `python/migrated-scripts.tsv` lists each with `#4678`; `python/test_upgrade_larch.py` no longer embeds retired-path literals.
- `make test-design-step6` runs the pytest selection; `scripts/test-design-structure.sh` pins the registry, launcher routing, retired-path absence, and manifest rows.
- `make py-lint`, `make py-test`, and `make lint` (including `lint-retired-scripts`) pass.

review_status: complete
rounds_completed: 5
diff_added: 445
diff_deleted: 265
mechanical_churn: false
diff_lines: 710
