### FINDING_1: Pure Claude fallback lacks prelaunch porcelain baseline
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Innovation, Codex-Requirements
- **Severity**: blocking
- **Concern**: On `STATUS=claude_fallback` paths (`coder=claude`, missing-binary, `--force`), `step2-prelaunch-porcelain.nul` and digest artifacts are never written because early branches return before worktree resolution and `run_dispatch_main` calls `_capture_prelaunch_porcelain` without a filesystem `repo_root`. Step 2.4 `recovery-paths` and recovery recompute then fail closed or include unrelated pre-existing dirt.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `run_dispatch_main`, after the child exits and before relaying stdout: parse captured child stdout for `STATUS=claude_fallback` plus `ORCHESTRATOR_EDIT_AUTHORITY=allowed`; resolve `repo_root` with the same `git rev-parse --show-toplevel` contract as `step2_dispatch_main`; call `_capture_prelaunch_porcelain` only when prelaunch artifacts are absent; fail closed (non-zero) when git root resolution fails.
  - From Codex-Arch: Move `_capture_prelaunch_porcelain` into each early fallback branch before the `return 0`, not only after the launcher-backed path.
  - From Codex-Innovation: Derive the git toplevel in run_dispatch_main before spawning step2-dispatch, or thread the root through the fallback branch before returning, then call `_capture_prelaunch_porcelain` with that path.
  - From Codex-Requirements: Derive `repo_root` in `run_dispatch_main` before the lock, or thread it through from the child, and pass it into `_capture_prelaunch_porcelain` before returning on `claude_fallback`.


### FINDING_2: Missing external binaries hard-fail before Claude fallback can run
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: blocking
- **Concern**: `run_dispatch_main` still exits early when the selected Cursor/Codex binary is absent, so the planned `STATUS=claude_fallback` path and its prelaunch-capture hook never run for the explicit missing-binary scenario the feature targets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Remove or convert the early binary checks in `run_dispatch_main` so missing `cursor`/`codex` binaries flow through `step2_dispatch_main`'s fallback, and replace the cursor-missing test with fallback coverage for both binaries.


### FINDING_5: Structure test still pins obsolete Step 3 `10800000` timeout
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Concern**: The plan moves Step 3 to `checks-commit-route` with `timeout: 15600000`, but `scripts/test-implement-structure.sh` still requires `skill_text.count('timeout: 10800000') >= 1`. After the fold, SKILL will have zero `10800000` literals and `make test-implement-structure` fails even when runtime routing is correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Replace lines 343-344 with a Step 3 composite pin matching Step 6 (require `timeout: 15600000` on the `checks-commit-route --checks-site step3 --commit-site step4 --rebase-checkpoint-4r` fence) or delete the 10800000 tier check entirely; add the Step 3 composite entry to the timeout `for script, timeout in [...]` loop at lines 229-236.


### FINDING_7: Step 2 token mark double-counts on external launcher redispatch
- **Reviewer(s)**: Codex-Innovation
- **Severity**: blocking
- **Concern**: `run_dispatch_main` is adding a first-dispatch Step 2 token row, but Codex and Cursor launchers still mark the same token on every external run and Q/A redispatch, so telemetry will double-count Step 2 instead of becoming once-only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Remove or gate the launcher token mark behind the same once-only sentinel, or move the Step 2 token mark entirely into run_dispatch_main and update the launcher contract.


