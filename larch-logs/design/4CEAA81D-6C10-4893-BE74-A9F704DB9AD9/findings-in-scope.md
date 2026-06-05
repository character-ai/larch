### FINDING_1: Restore can clobber finalized stall metadata with preseeded false state
- **Reviewer(s)**: Cursor-Arch, Codex-dyn-bash-python-boundary
- **Severity**: important
- **Concern**: The restore path is aimed at missing stall keys, but Step 8 prewrites `ship-pr-state.sh` with `STALL_TRACKING=false`; that explicit false can overwrite Python-written `finalize-state.sh` values where `STALL_TRACKING=true`, losing the real stalled context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: When finalize-state.sh has STALL_TRACKING=true, prefer finalize STALL_TRACKING/STALL_STEP over ship-pr values (including explicit false). Seed ship-pr with STALL_TRACKING=false in restore tests and structural pins.
  - From Codex-dyn-bash-python-boundary: Define the restore branch to preserve existing finalize-state.sh STALL_TRACKING=true and non-empty STALL_STEP even when ship-pr-state.sh contains STALL_TRACKING=false or STALL_STEP=. Add that exact prewritten-state case to the restore harness or structural pin.

### FINDING_2: Gap-fill skips needed persistence when finalize-state is missing for inline-finalized stalls
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Innovation
- **Severity**: important
- **Concern**: The proposed inline-finalized no-op heuristic adds dead or unsafe branching: if an inline writer fails after returning `STALLED`, `finalize-state.sh` may be missing and the gap-fill can skip persisting stall metadata, causing later Step 18 misclassification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Keep only: STALLED + allowlisted tmpdir + no existing STALL_TRACKING=true → merge-write stall metadata; drop the missing-finalize inline-stall exception list.
  - From Cursor-Edge: Drop the missing-file inline-finalized no-op heuristic; gate only on existing finalize-state with STALL_TRACKING=true plus invalid-tmpdir allowlist exclusion
  - From Cursor-Innovation: Simplify the gap-fill predicate to: Outcome.STALLED + allowlisted tmpdir + (no finalize-state.sh or STALL_TRACKING is not true); drop the missing-file/inline-finalized carve-out

### FINDING_3: Stall recovery classifier does not read finalize-state fallback
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: Python `STALLED` routing can write `STALL_TRACKING` and `STALL_STEP` only to `finalize-state.sh`, but Step 18a classification still reads only `ship-pr-state.sh` and `session-env.sh`, so recovery can lose the stall context and choose the wrong path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Update the plan to make stall-recovery-report.sh and stall-recovery.md read finalize-state.sh as a fallback source for STALL_TRACKING and STALL_STEP, or pass the resolved finalize values into classify; add a final-only Python STALLED regression pin

### FINDING_4: Quiet log routing can raise or misroute instead of falling back
- **Reviewer(s)**: Codex-Edge, Codex-Innovation
- **Severity**: important
- **Concern**: Removing `quiet=False` bypasses leaves quiet-mode breadcrumbs vulnerable when `LARCH_QUIET_LOG_FILE` points to a missing or unwritable path; `Path.open` can raise or keep env-based routing active after degraded setup instead of falling back to fd4 or stderr.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Wrap the log-file append in suppress(OSError) and continue to the fd4 write or normal stderr fallback; add one regression with an active quiet env and an unwritable or missing log parent
  - From Codex-Innovation: Clear or mark quiet env inactive on quiet_init setup failure and wrap log-file append in best-effort OSError handling so default emit falls back to normal stderr when no route succeeds

### FINDING_5: Stall metadata gap-fill can mask the primary STALLED result
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Concern**: `_persist_stall_metadata_if_needed` is planned before result emission, but validation or I/O failures during gap-fill could replace the original `STALLED` contract JSON and exit code with an internal failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: A failed gap-fill should emit a warning breadcrumb and leave the original ShipResult and exit code unchanged; test a write_finalize_state_merged failure still emits the STALLED JSON and exit 4

### FINDING_6: Merged finalize-state validation may allow carriage returns
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Concern**: The proposed merged finalize-state reader/writer only pins newline rejection; allowing carriage returns would weaken the existing shell state-file integrity contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Validate both "\n" and "\r" in read_finalize_state and write_finalize_state_merged, and add a CR rejection regression alongside the newline test

### FINDING_7: Exit 0 OOS reinvoke still uses bash-only --resume-phase on Python path
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan covers the OOS checkpoint section but misses the Exit 0 OOS re-entry bullet; on the Python path, re-invoking with `ship-pr.sh --resume-phase pr-create` can fail because `ship.py` has no `--resume-phase` flag.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Extend A1/A1b and the FINDING_6 structural pin to split Exit 0 (~L1049) OOS reinvoke: bash keeps --resume-phase pr-create; python re-invokes the Step 8+ python fence without --resume-phase (same rule as ~L1067)
  - From Cursor-Requirements: Extend A1b with an Exit 0 (~L1049) python inline override (re-invoke the python fence without `--resume-phase`, same as FINDING_6); add a structural pin in `scripts/test-implement-structure.sh` that greps the Exit 0 bullet, not only the OOS checkpoint section

### FINDING_8: quiet_init can create or truncate logs before invalid-tmpdir rejection
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: `quiet_init` is planned before the tmpdir allowlist check, so an invalid `IMPLEMENT_TMPDIR` or quiet log path outside allowed roots can create or truncate a quiet log before the intended JSON-only `STALLED` invalid-tmpdir result.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Gate quiet_init on _tmpdir_under_allowed_root(ctx.tmpdir), or skip self-quiet for invalid tmpdirs; add an invalid-tmpdir regression that asserts no quiet log/truncation in addition to no journal/finalize-state

### FINDING_9: Exit 3 Python path still reads bash BAIL_REASON instead of JSON needs_user_reason
- **Reviewer(s)**: Cursor-dyn-bash-python-boundary
- **Severity**: important
- **Concern**: The shared Exit 3 matrix adds only a Python `failed_run_id` JSON override, but not a replacement for reading `BAIL_REASON` from `ship-pr-state.sh`; Python emits the dispatch reason as stdout JSON `needs_user_reason`, so following the shared bullets can misroute autonomous CI-fix vs user-bail handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-bash-python-boundary: In A1b Exit 3, add an inline python override: dispatch on JSON `needs_user_reason` (not `ship-pr-state.sh` `BAIL_REASON`); pin the same wording in `scripts/test-implement-structure.sh` A2/A2b

### FINDING_10: Python OOS/retry prose overstates PHASE resume behavior
- **Reviewer(s)**: Codex-dyn-bash-python-boundary
- **Severity**: latent
- **Concern**: The proposed prose says persisted `PHASE` continues Python’s main loop, but `ship.py` does not read `PHASE` from `ship-pr-state.sh` on startup; it only exposes `PHASE` for orchestrator-side budgeting and gate decisions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-bash-python-boundary: Revise the Python-path prose and pins to say PHASE is read from ship-pr-state.sh for orchestrator retry budgeting and OOS gate decisions only; do not claim ship.py consumes PHASE for resume unless this PR also adds explicit phase-loading support.

### FINDING_11: PR metadata gap-fill source order can preserve stale pre-run context over canonical state-file values
- **Reviewer(s)**: Cursor-dyn-writer-ordering, Codex-dyn-writer-ordering
- **Severity**: important
- **Concern**: The planned source order fills PR fields from `ShipResult` and pre-run context before parsing `ship-pr-state.sh`; for stalled paths where in-loop writes updated PR metadata but returned results omit those fields, stale pre-run values can block canonical state-file values from being copied to finalize-state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-writer-ordering: State explicit fill order after read_finalize_state preserve: non-empty ShipResult fields into empty slots only, then key-parse ctx.state_file, then pre-run ctx last; add/adjust regression (5) to assert PR_NUMBER comes from ship-pr-state when ShipResult and main ctx lack it.
  - From Codex-dyn-writer-ordering: Change the plan for _persist_stall_metadata_if_needed to fill absent PR/merge keys from non-empty ShipResult first, preserve non-empty existing finalize-state keys, parse ship-pr-state.sh next, and use pre-run ctx only as the last fallback.
