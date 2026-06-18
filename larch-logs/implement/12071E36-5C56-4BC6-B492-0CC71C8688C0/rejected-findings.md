### [rejected] FINDING_10

**Rejected subtype:** dismissed (0 YES)

### FINDING_10: Weakened `SKILL.md` launcher fence enforcement
- **Reviewer(s)**: dyn-launcher-cutover-output.txt
- **Severity**: important
- **Concern**: The branch replaces a large Python fence scanner with a handful of `contains` checks on `SKILL.md`. Only four launcher fences are spot-checked; nothing scans all `design-run-$PPID.sh` invocations to enforce "bare verb for Step 0/1, `*.sh` for clarify/Step 2+", and nothing verifies Step 0a stays off the launcher. A mistaken reintroduction of `design-step0-route.sh` (or launcher-dispatched `step0-session`) in a new fence would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-launcher-cutover-output.txt: Restore a mechanical scanner over `skills/design/SKILL.md` (and `references/brainstorm.md`) that classifies every `design-run-$PPID.sh` first argument against the retired-path denylist and the 11-verb allowlist.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** dismissed (0 YES)

### FINDING_11: Stale per-PID launcher after plugin upgrade mid-session
- **Reviewer(s)**: dyn-launcher-cutover-output.txt
- **Severity**: important
- **Concern**: `design-run-$PPID.sh` is regenerated only when `session write-design-env` runs (Step 0a `step0-session`, then again from `design init-runparams`). The hard cutover deletes the retired `.sh` bodies with no stubs. A pre-upgrade launcher only knows `exec …/skills/design/scripts/$script`; after a plugin upgrade, an in-flight `/design` session that already finished Step 0a on the old build will call Step 0b+ through a stale launcher and either exec missing scripts or lack the verb-dispatch branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-launcher-cutover-output.txt: Regenerate the per-PID launcher at the top of every ported verb entry (cheap rewrite), or document and enforce "restart `/design` after upgrading larch" in the Step 0 prelude with a launcher version/hash check that fails closed when stale.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_13: Relevant-check routing splits router-flag recovery from `design_lifecycle.py`
- **Reviewer(s)**: dyn-retirement-coverage-output.txt
- **Severity**: important
- **Concern**: Relevant-check routing splits router-flag recovery from the ported surface. Changes to `python/design_lifecycle.py` (including `route_main` OR-merge) trigger `test-design-step0-init` but not `test-step0b-router-flag-recovery`, while `test-step0b-router-flag-recovery` is still tied only to `python/plan_quality.py`. The deleted shell harness exercised init/route wiring together; `test_design_route_merges_flags_for_already_planned` in `python/test_design_lifecycle.py:96-137` now falls outside the `design_lifecycle.py` relevant-check path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-retirement-coverage-output.txt: Add `test-step0b-router-flag-recovery` (or `py-test` with a `-k design_route or resolve_repo` selector) to the `python/design_lifecycle.py` direct-target rule, or broaden the `test-design-step0-init` pytest `-k` expression so `route_main` regression tests run whenever Step 0/1 Python changes.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: Degraded-tools-gate stderr dropped on success path
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `step0_session_main` captures degraded-tools-gate stderr and does not relay it on the success path; only stdout is relayed. On a degraded-tools path, operator-visible rehydration `ERROR` lines that bash printed to the terminal are dropped unless the gate exits non-zero, slowing diagnosis of miswired presence keys.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: After relaying gate stdout, print non-empty gate.stderr to the operator stream (or merge stderr into relay input on success), matching bash visibility.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: Pause request lost when `DESIGN_TMPDIR` is invalid
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `check_pause_and_exit` calls `_require_design_tmpdir` before checking `.pause-requested`, so an invalid `DESIGN_TMPDIR` aborts without `pause_save_main`. A pause request during Step 0c/0 route/init can be lost and the run hard-fails instead of persisting pause state when session env has a bad tmpdir path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Check `.pause-requested` first with minimal path checks, invoke `pause_save_main`, then `sys.exit(rc)`; keep strict tmpdir validation for mutating verbs only.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (0 YES)

### FINDING_9: Launcher verb allowlist not mechanically synced with `_REGISTRY`
- **Reviewer(s)**: dyn-launcher-cutover-output.txt
- **Severity**: important
- **Concern**: The 11 ported verb tokens are duplicated in three places (`_design_run_launcher_text`, `python/cli.py` `_REGISTRY`, and `scripts/test-design-structure.sh:30`) with no mechanical sync test. If a future slice registers a verb in `_REGISTRY` but omits the launcher allowlist (or the reverse), `design-run-$PPID.sh <verb>` will fail with `ERROR=unknown design wrapper verb` while `python3 python/cli.py design <verb>` still works, breaking Step 0/1 fences mid-run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-launcher-cutover-output.txt: Add a pytest (or extend `test_design_lifecycle_registry_entries_are_machine_stdout`) that extracts the launcher verb case arm and asserts it equals the `design step0-*` / `step0c` / `step1d5` / `step1d7` / `step1e-reentry` subset of `_REGISTRY`.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

