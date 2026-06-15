### FINDING_1: `step-2-post-dispatch.sh` lacks plugin-root bootstrap before sourcing libs
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: blocking
- **Concern**: The planned wrapper sources `lib-quiet.sh` and `lib-phantom-probe.sh` from `$PLUGIN_ROOT/scripts`, but the plan never defines `PLUGIN_ROOT`, `SCRIPT_DIR`, or `CLAUDE_PLUGIN_ROOT` rehydration. Under `larch-run.sh` (which sets `CLAUDE_PLUGIN_ROOT`, not `PLUGIN_ROOT`) and `set -u`, the wrapper fails or sources the wrong tree before it can emit `PHANTOM_*`, `BRANCH=`, or `COMMIT_SHA=`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Mirror step-2-entry.sh: derive PLUGIN_ROOT from CLAUDE_PLUGIN_ROOT with SCRIPT_DIR/../../.. fallback and source "$CLAUDE_PLUGIN_ROOT/scripts/lib-quiet.sh" plus lib-phantom-probe.sh
  - From Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements: Mirror step-2-entry.sh bootstrap: SCRIPT_DIR PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}" plugin-root.env/session-env rehydration IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:?...}" then source "$CLAUDE_PLUGIN_ROOT/scripts/lib-quiet.sh" and lib-phantom-probe.sh


### FINDING_3: Merged Step 2.2 SKILL.md fence drops foreground-required guard
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan's merged Step 2.2 Bash fence for the new wrapper omits the existing `Foreground required — do NOT set run_in_background: true` annotation that today's phantom-probe call carries. Without it, the orchestrator may run post-dispatch work in immediate-background mode, moving `PHANTOM_*`, `BRANCH=`, and `COMMIT_SHA=` parsing (and the `main-branch-post-dispatch` bail) off the sanctioned foreground boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Keep one bash larch-run.sh skills/implement/scripts/step-2-post-dispatch.sh fence with the existing Foreground required — do NOT set run_in_background: true annotation unchanged from the current Step 2.2 block


### FINDING_4: Unguarded `git rev-parse` under `set -e` can falsely route to Step 12d
- **Reviewer(s)**: Cursor-Requirements, Cursor-dyn-post-dispatch-correctness
- **Severity**: important
- **Concern**: The plan pairs `set -euo pipefail` with a bare `COMMIT_SHA=$(git rev-parse --short HEAD)` after `BRANCH=` emission. A rev-parse failure exits the wrapper with rc 1 even when branch read succeeded. Step 2.2 treats any non-zero wrapper exit as detached HEAD / branch failure and routes `main-branch-post-dispatch` to Step 12d, changing today's behavior where only Step 4's breadcrumb would lose `sha=`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Make SHA read non-fatal: COMMIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || true); emit COMMIT_SHA only when non-empty; exit 0 after successful BRANCH= even when SHA is absent
  - From Cursor-dyn-post-dispatch-correctness: Specify rev-parse must be guarded (if/commit_sha= pattern or || true); wrapper exit 1 only for symbolic-ref failure; emit COMMIT_SHA only when rev-parse succeeds; still exit 0 when branch is valid but SHA is unavailable


### FINDING_5: `test-implement-structure.sh` wrappers list omits new script
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan updates `require()` pins for the new launcher path but does not add `step-2-post-dispatch` to the `wrappers` array (line 126) that enforces executable `.sh` plus `.md` sibling coverage. Because `larch-run.sh` execs `*.sh` directly (`python/bootstrap.py:140`), the harness will not enforce `chmod +x` or the `.md` sibling for the new wrapper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add step-2-post-dispatch to the wrappers array (line 126) alongside step-2-entry; ship the new .sh chmod +x so the loop passes




### FINDING_1: Parse PHANTOM_* from wrapper stdout before exit-code routing
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The planned Step 2.2 merge (one `step-2-post-dispatch.sh` call replacing separate phantom probe + `git-current-branch.sh`) does not yet require parsing `PHANTOM_*` (and optionally `COMMIT_SHA=`) from wrapper stdout **before** evaluating wrapper exit code or branch assertion. Today’s two-call flow always token-scans `PHANTOM_*` from the successful probe call first; on detached HEAD the branch script exits non-zero but phantom advisory telemetry is already consumed. A combined wrapper that emits `PHANTOM_*` then exits 1 on branch read failure can drop phantom telemetry and related execution-issues warnings if the orchestrator gates stdout parsing on `rc=0`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add explicit Step 2.2 prose: always token-scan PHANTOM_* (and optional COMMIT_SHA=) from wrapper stdout before evaluating wrapper exit code or BRANCH_NAME comparison; only then route non-zero exit or mismatch to main-branch-post-dispatch
  - From Cursor-Pragmatic: In Step 2.2 STATUS=complete prose, require parsing PHANTOM_* from wrapper stdout regardless of exit code; gate BRANCH=/COMMIT_SHA= binding and BRANCH_NAME comparison on rc=0 only; then apply existing main-branch-post-dispatch bail when rc!=0 or branch mismatches
  - From Cursor-Requirements: In the Step 2.2 SKILL.md edit, require token-scanning PHANTOM_* from wrapper stdout regardless of exit code, then apply existing branch compare / main-branch-post-dispatch bail logic



