### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/implement_dispatch.py:78
- **Concern**: pinned `OOS_PENDING=false` merge uses invalid `_write_ship_state` `extra_fields`. Scenario: `ship._ALLOWED_EXTRA_FIELDS` is only `CONFLICT_FILES` (`python/ship.py:78`). Passing `extra_fields={"OOS_PENDING": "false"}` raises `ShipError: invalid ship state extra field: OOS_PENDING`, so the disposition-rc-0 success tail never clears `OOS_PENDING` and always falls into the bookkeeping-failure stall path.
- **Proposed resolution**: Pin a single-key merge: read existing `ship-pr-state.sh`, set only `OOS_PENDING=false`, filter to `ship._ALLOWED_SHIP_STATE_KEYS`, reject symlinked paths, atomic write. Do not use `_write_ship_state` `extra_fields` for `OOS_PENDING`, and do not call full `_write_ship_state` without a complete `RunContext` loaded from existing state.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/implement_dispatch.py:67-69
- **Concern**: Transient retry counter increment is not pinned to persist to disk. Scenario: `ship_route_exit_main` says read/increment `ship-pr-net-retries-python.count` (absent means 0) but never requires writing the incremented value back. Without a persisted count, every exit 6 stays at retry 1, sleep+`reship` loops forever, and retry-4 stall seeding never runs.
- **Proposed resolution**: After increment, atomically write the new integer to `$IMPLEMENT_TMPDIR/ship-pr-net-retries-python.count` before emitting `NEXT_ACTION=reship`; on retry 4 after seeding, emit `NEXT_ACTION=stall` without resetting the file unless an existing reset rule applies. Add a unit test that two consecutive exit-6 handoffs leave the count file at 2.

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/ship.py:77-80
- **Concern**: [ALREADY_ADDRESSED partial] FINDING_2 merge path still pins `ship._write_ship_state` with `extra_fields={"OOS_PENDING": "false"}` but `_ALLOWED_EXTRA_FIELDS` is only `CONFLICT_FILES`. Scenario: Implementer follows the plan's primary API and `_write_ship_state` raises `ShipError: invalid ship state extra field: OOS_PENDING` before any merge write; disposition rc 0 success never clears `OOS_PENDING`, breaking the reship loop and violating NEVER #15
- **Proposed resolution**: Drop the `extra_fields` recipe. Add a minimal `_patch_ship_state_keys(state_file, {"OOS_PENDING": "false"})` that reuses `_write_ship_state`'s read-filter-validate-atomic-write loop (allowed keys only, symlink rejection) without a full `RunContext`, or reconstruct `RunContext` from existing state with `oos_pending=False` and call `_write_ship_state` with preserved phase/counters

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-8-oos-checkpoint.sh:17-22
- **Concern**: Thin-wrapper migration drops explicit `--design-tmpdir` forwarding that today's bash passes to `oos disposition-checkpoint`. Scenario: Today's wrapper passes `--design-tmpdir "$DESIGN_TMPDIR"` when the shell variable is set even if it is not exported. The planned relay calls only `implement step-8-oos-checkpoint`, whose Python helper forwards `DESIGN_TMPDIR` only from `os.environ`. Shell-local `DESIGN_TMPDIR` no longer reaches disposition-checkpoint, so `oos-accepted-design.md` resolves from the wrong path and disposition can false-fail or false-pass
- **Proposed resolution**: Pin `step8_oos_checkpoint_main` argparse `--design-tmpdir` (optional) forwarded to the disposition-checkpoint subprocess, and have the thin bash wrapper pass the same conditional arg the current script uses at line 18

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/implement_dispatch.py
- **Concern**: `ship route-exit` required-field table covers only driver rc {0,1,3,4,6}; behavior for other rc values when `.json` exists is undefined. Scenario: If stale-json hygiene or a capture bug leaves `.step-8-ship-handoff.json` present while `.rc` is 2 (or another unlisted value), SKILL still invokes route-exit; the router has no fail-closed branch and may emit the wrong `NEXT_ACTION` instead of absent-token Tool Failures
- **Proposed resolution**: Pin fail-closed: when rc sidecar value is not in {0,1,3,4,6}, emit stderr diagnostic, exit non-zero, emit no `NEXT_ACTION`, and write no `.ship-route-exit-handoff.env`; add one router test for rc=2 with parseable json

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/implement_dispatch.py:66-69
- **Concern**: Transient retry counter is read and incremented but never persisted to disk. Scenario: The plan makes `ship route-exit` the sole post-driver transient authority and removes orchestrator count maintenance from SKILL, but only specifies read `$IMPLEMENT_TMPDIR/ship-pr-net-retries-python.count`, treat missing as 0, then increment. It never requires writing the incremented value back. Each exit 6 would re-read a missing or stale file as 0, classify retry 1 forever, never reach retry-4 `NEXT_ACTION=stall`, and bypass the cap seeding the issue depends on.
- **Proposed resolution**: Pin atomic persist immediately after increment (write `ship-pr-net-retries-python.count` with the post-increment value before sleep/`reship`); add a test that a second exit-6 handoff reads count 1 and a fourth reads 3 then emits `stall`.

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/implement_dispatch.py:38-60
- **Concern**: `ship route-exit` lacks fail-closed handling for handoff rc values outside {0,1,3,4,6}. Scenario: Round-4 FINDING_3 noted undefined behavior for wrapper rcs like 2 (setup/`require_value`) when a `.json` sidecar is present. The plan adds a SKILL gate that skips `route-exit` when `.json` is absent and stale-json unlink on rc-only EXIT, but `ship_route_exit_main` still only defines validation tables for 0/1/3/4/6 and does not require rejecting unsupported rc values before classification. A mismatched rc+json pair (stale sidecar bug, partial trap failure, or manual invoke) can fall through to wrong `NEXT_ACTION` instead of fail-closed Tool Failures.
- **Proposed resolution**: After reading `.step-8-ship-handoff.rc`, fail closed (no `NEXT_ACTION`, non-zero exit) when rc is not in {0,1,3,4,6}; document the rule in `ship-pr-exit-matrix.md`; add a test with rc=2 plus valid JSON that asserts no routing output.

### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:58-60
- **Concern**: NEVER #14/#15 still mandate orchestrator-owned `oos disposition-checkpoint` and manual `OOS_PENDING=false` clearing.. Scenario: Plan moves disposition, `run-statistics`, manifest stamp, and `OOS_PENDING=false` into `implement step-8-oos-checkpoint` with `NEXT_ACTION` routing, but NEVER #15 still tells the orchestrator to invoke `python/cli.py oos disposition-checkpoint` and rewrite `OOS_PENDING=false` itself. Partial SKILL edits leave dual contracts: prose may still clear state or call disposition-checkpoint directly while the verb also owns bookkeeping.
- **Proposed resolution**: Rewrite NEVER #15 (and the bash-path sentence in #14) to require `step-8-oos-checkpoint.sh` / `implement step-8-oos-checkpoint` success (`NEXT_ACTION=reship`) before `OOS_PENDING` may clear; forbid orchestrator-side `run-statistics` composition and direct `OOS_PENDING=false` writes on the post-pipeline path.

### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/implement_dispatch.py:38-60
- **Concern**: `ship route-exit` lacks fail-closed handling for handoff rc values outside {0,1,3,4,6}.. Scenario: Required JSON fields and action mapping are enumerated only for 0/1/3/4/6. Setup failures are gated by absent `.json`, but a corrupted `.rc` sidecar paired with valid guard/`ship pr` JSON has undefined classification and may emit the wrong `NEXT_ACTION` instead of failing closed.
- **Proposed resolution**: Pin explicit validation: if `.step-8-ship-handoff.rc` is not in {0,1,3,4,6}, emit stderr diagnostic, exit non-zero, emit no `NEXT_ACTION`, and do not write `.ship-route-exit-handoff.env`; add a router test for rc=2 with valid JSON.

### FINDING_11:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:819; python/implement_dispatch.py
- **Concern**: Planned route-exit mapping regresses exact local-unfixable from autonomous ci-fix to operator-bail. Scenario: Current Step 8 routing sends needs_user_reason=local-unfixable through the autonomous main-agent CI-fix path before AskUserQuestion. The plan maps exact local-unfixable to operator-bail and adds a test for that, so a driver exit 3 with local-unfixable would skip the required automated repair attempt and ask the operator immediately.
- **Proposed resolution**: Map exact local-unfixable to NEXT_ACTION=ci-fix with first-fixer-non-health, ship-pr-internal-lint-fix, and ci-local-unfixable:*; keep the existing FORKED_TARGET and REPO_UNAVAILABLE skip to operator-bail.

### FINDING_12:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:78
- **Concern**: The accepted OOS_PENDING merge fix still permits a broken _write_ship_state(extra_fields={"OOS_PENDING":"false"}) path. Scenario: python/ship.py currently allows only CONFLICT_FILES in _ALLOWED_EXTRA_FIELDS. If the implementation follows the plan's suggested _write_ship_state extra_fields route literally, the success tail raises ShipError, emits OOS-checkpoint stall, and never clears OOS_PENDING after a valid disposition checkpoint.
- **Proposed resolution**: Pin one safe implementation: either add OOS_PENDING to _ALLOWED_EXTRA_FIELDS and call _write_ship_state from a state-overlay context with the current phase, or remove the extra_fields option from the plan and require a dedicated allowed-key merge helper.

### FINDING_13:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/file_oos.py:583-613; python/implement_dispatch.py:717-723
- **Concern**: OOS checkpoint capture can erase child-written validation diagnostics. Scenario: The disposition-checkpoint child writes validation details directly to oos-disposition-checkpoint.stderr.log before returning rc 2. The planned Python-owned wrapper captures stderr, and the existing helper pattern rewrites that same log from captured stderr. When the child logged to the file but emitted no stderr, the parent can replace the useful diagnostic with an empty file while skipping fallback logging because execution-issues.md already has the row.
- **Proposed resolution**: Preserve the child-owned log on rc 2 and similar validation paths: do not truncate or overwrite a non-empty oos-disposition-checkpoint.stderr.log with empty captured stderr; merge captured stderr only when present.
