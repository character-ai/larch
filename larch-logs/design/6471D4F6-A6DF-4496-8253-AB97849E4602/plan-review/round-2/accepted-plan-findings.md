### FINDING_1: Upgrade-larch docs still treat same-version reconcile as no-restart
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: `skills/upgrade-larch/SKILL.md` is missing the same-version sparse-cone reconcile behavior. If the command reports an already-latest release before performing uninstall/reinstall to fix cone drift, Step 2 may tell operators no reinstall or restart is needed, leaving them in a stale session.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Cursor-Innovation: Add skills/upgrade-larch/SKILL.md to the change list: early-exit/no-restart only when latest and cone match; reconcile-on-drift needs reinstall plus restart messaging
  - From Cursor-Requirements: Add skills/upgrade-larch/SKILL.md to Files to modify: update Step 2 for early-exit only when latest and cone match; document the reconcile advisory and require restart after a reconcile reinstall even when the version string is unchanged


### FINDING_2: SessionStart drift probe can break non-blocking exit contract
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Cursor-Edge, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The proposed `sessionstart-health.sh` drift probe is not sufficiently isolated from `set -euo pipefail`. Missing `HOME`, failed `source`/`git` calls, or empty sparse-checkout output could abort before the final `exit 0` or emit a false drift warning, violating the SessionStart best-effort/non-blocking contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch, Codex-Edge: Use a local home_dir=${HOME:-} guard and skip the drift probe when empty; keep fixture HOME injection for drift cases without relying on HOME being globally present
  - From Cursor-Edge: Mirror marketplace_sparse_cone_matches: wrap the whole probe in a set +e block or subshell; use source ... || true; append git ... || true; skip silently when configured is empty ([ -n "$configured" ] before comparing)
  - From Cursor-Pragmatic: Wrap the drift probe in a best-effort block (set +e or subshell) and use source ... || true plus guarded git/compare, mirroring the lib-resolve source at line 127


### FINDING_3: Sourced shell helper may fail ShellCheck without shell directive
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: A new sourced-only `.sh` helper without a shebang also needs an explicit ShellCheck shell directive; otherwise repo lint may fail with SC2148 before behavioral tests run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Start `scripts/lib-sparse-dirs.sh` with `# shellcheck shell=bash` and list that invariant in `scripts/lib-sparse-dirs.md`, while keeping the file non-executable and sourced-only.


### FINDING_4: Plan references a non-existent SessionStart make target
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The testing strategy names `make test-sessionstart-health`, but the existing target is apparently `make test-sessionstart`; implementers may hit a missing-target error or skip the intended regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Replace make test-sessionstart-health with existing make test-sessionstart; do not add a new alias unless needed elsewhere

