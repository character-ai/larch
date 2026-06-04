### FINDING_1: Python default can still route Step 8+ continuations through bash ship-pr.sh
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Cursor-dyn-selector-routing, Codex-dyn-selector-routing, Cursor-dyn-stale-reference-sweep
- **Severity**: important
- **Concern**: After flipping the Step 8+ default to `python/ship.py`, multiple load-bearing routing, anti-halt, recovery, and continuation instructions still tell the orchestrator to parse `ship-pr-state.sh`, follow the bash exit matrix, or re-invoke the fenced `ship-pr.sh` block. A default Python run can therefore switch drivers mid-run, ignore JSON routing, or route from stale/missing bash state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add one load-bearing sentence to the flipped **Python driver selector** (within the two routing sentences): on the default Python path, any Step 8+ bullet that says re-invoke the fenced `Invoke:` block or `ship-pr.sh` means re-invoke the Python foreground command from the selector; matrix and `Invoke:` apply only when `LARCH_SHIP_PR_IMPL=bash`
  - From Cursor-Edge: Add one minimal sentence to the flipped selector (or edit this critical boundary): on the default Python path, after `python/ship.py` returns, route from JSON stdout + selector exit routing only—do not parse `ship-pr-state.sh` for driver continuation and do not treat the bash exit table as authoritative unless `LARCH_SHIP_PR_IMPL=bash`
  - From Cursor-Innovation: Default-path runs can mis-route exits (e.g. read stale/missing `PHASE`/`BAIL_REASON`, re-enter bash matrix) despite a successful `python/ship.py` JSON envelope Add one anti-halt qualifier: unless `LARCH_SHIP_PR_IMPL=bash`, after Step 8+ ship driver return use Python selector JSON + exit routing, not `ship-pr-state.sh` / bash exit table
  - From Cursor-Pragmatic: Add one minimum sentence (same pattern as the planned pre-`Invoke:` guard): on the default Python path, re-invoke the selector’s `python3 …/python/ship.py` foreground call; use the fenced `Invoke:` block only when `LARCH_SHIP_PR_IMPL=bash`
  - From Codex-Pragmatic: Keep the bash matrix, but label it bash-only and add minimal Python-path continuation rules: use JSON fields, re-invoke python/ship.py with the same argv after OOS or main-agent CI fix, and avoid ship-pr-state.sh for Python routing.
  - From Cursor-Requirements: Add one load-bearing override in the flipped Python driver selector: autonomous sub-procedure step 12 re-invokes the active Step 8+ driver (python/ship.py foreground argv unless LARCH_SHIP_PR_IMPL=bash, then fenced Invoke)
  - From Cursor-dyn-selector-routing: Pre-Invoke routing alone is insufficient. Add one bash-only gate immediately before line 1020 (e.g. apply the following exit matrix only when LARCH_SHIP_PR_IMPL=bash; otherwise follow the Python driver selector JSON exit routing and reinvoke python/ship.py) without rewriting the matrix bullets. Keeps the fenced Invoke: block byte-stable per plan scope.
  - From Codex-dyn-selector-routing: Add a minimal selector-neutral rewrite for these specific reminders: after the Step 8+ ship driver exits, use Python JSON routing unless LARCH_SHIP_PR_IMPL=bash; only the bash branch parses ship-pr-state.sh and re-invokes the fenced ship-pr.sh contract.
  - From Cursor-dyn-stale-reference-sweep: Add a bash-only qualifier on the recovery bullet (or point recovery at the selector’s Python re-invocation) so default-path recovery never names the fenced `ship-pr.sh` `Invoke:` block as authoritative

### FINDING_2: Python path can restore stale seeded ship-pr-state into finalize-state during teardown
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: The planned Python-default path still seeds `ship-pr-state.sh`, but `python/ship.py` is invoked without `--state-file`, so that state file is not refreshed. Step 18 restore can later rebuild or overwrite `finalize-state.sh` from stale bash-shaped values, masking Python-written PR, stall, cleanup, or terminal state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Make restore-finalize-state.sh invocation bash-path only, or otherwise ensure Python-path teardown ignores the seeded ship-pr-state.sh; if the state file must remain for OOS helpers, do not use it to restore finalize-state on the Python path
  - From Codex-Edge: Add --state-file "$IMPLEMENT_TMPDIR/ship-pr-state.sh" to the Python argv list so python/ship.py replaces the seeded state before teardown, or gate ship-pr-state seeding and restore to the bash opt-in path only
  - From Codex-Innovation: Pass --state-file "$IMPLEMENT_TMPDIR/ship-pr-state.sh" to python/ship.py in the selector argv, or skip ship-pr-state seeding/restore on the Python path; passing the existing supported flag is the smaller fix
  - From Codex-Requirements: Add --state-file "$IMPLEMENT_TMPDIR/ship-pr-state.sh" to the Python selector invocation and pin or validate it, or explicitly skip creating/restoring ship-pr-state.sh on the Python path; keep the bash fenced block byte-stable

### FINDING_3: Stall recovery reference still hard-codes bash ship-pr.sh re-entry
- **Reviewer(s)**: Codex-Edge, Codex-dyn-selector-routing
- **Severity**: important
- **Concern**: `stall-recovery.md` still tells `step8-shippr` recovery to re-invoke `scripts/ship-pr.sh` as a foreground bash call. A Python-default run that enters Step 18a recovery can therefore switch back to the legacy bash driver instead of re-entering the active Step 8+ selector and JSON routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Update only the step8-shippr bullet and safety constraint to re-enter Step 8+ through the same selector: Python unless LARCH_SHIP_PR_IMPL=bash; keep the foreground writer_rc routing for the bash opt-in path
  - From Codex-dyn-selector-routing: Extend the plan to update only the step8-shippr bullet and safety constraint: re-enter the Step 8+ driver selector; use python/ship.py plus JSON routing unless LARCH_SHIP_PR_IMPL=bash, and keep the existing writer_rc/ship-pr-state wording scoped to the bash branch.

### FINDING_4: Pre-Invoke phantom-probe lead-in still names only ship-pr.sh
- **Reviewer(s)**: Cursor-dyn-selector-routing
- **Severity**: latent
- **Concern**: The lead-in immediately before the Invoke fence still says the next foreground call is `ship-pr.sh`. With Python as default, that wording can imply the wrong driver even though the selector should choose `python/ship.py` unless `LARCH_SHIP_PR_IMPL=bash`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-selector-routing: Reword line 957 to a driver-neutral lead-in (before the Step 8+ foreground driver: Python per selector unless LARCH_SHIP_PR_IMPL=bash) in the same SKILL edit hunk; no change to the fenced argv block.

### FINDING_5: Security-helper prose still describes Python scrub path as in-progress parity
- **Reviewer(s)**: Codex-dyn-stale-reference-sweep
- **Severity**: latent
- **Concern**: `scripts/scrub-log-secrets.md` still implies the Python ship-pr scrub path is not live. Since the default Python ship driver relies on that path, stale wording can mislead security review of run-log secret scrubbing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-stale-reference-sweep: Add scripts/scrub-log-secrets.md to the update list and reword this sentence to describe the default Python ship driver scrub path rather than in-progress parity

### FINDING_6: Upgrade notice omits cached-plugin/restart timing for the default flip
- **Reviewer(s)**: Cursor-dyn-operator-upgrade
- **Severity**: latent
- **Concern**: The planned operator notice says users who never set `LARCH_SHIP_PR_IMPL` switch drivers on the next plugin upgrade, but the default lives in cached `SKILL.md` and changes only after the upgraded plugin is loaded. Without tying the notice to restart/cache refresh timing, operators may expect Python default behavior while still running the old bash-default skill.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-operator-upgrade: Tie the notice to the existing restart rule at docs/installation-and-setup.md:38 and the cached-plugin note at docs/installation-and-setup.md:77-82 (e.g. the Python default applies on the first /implement after the upgraded plugin is loaded; set LARCH_SHIP_PR_IMPL=bash before starting Claude Code to pin legacy behavior during rollout).
