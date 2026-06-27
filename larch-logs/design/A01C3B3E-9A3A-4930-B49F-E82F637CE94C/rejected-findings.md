### [Plan Review] FINDING_3

### FINDING_3: Orchestrator `recovery-paths` calls lack pinned filesystem `REPO_ROOT`
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: important
- **Concern**: Orchestrator-side `implement recovery-paths` invocations (Step 2.4 ordinary fallback and Step 3 checks-repair refresh) omit a bound `--repo-root`. Session `REPO` is the GitHub slug, not the filesystem root `recovery_paths_main` requires, so calls can argparse-fail, use an empty/wrong root, or leave `implementation-commit-paths.nul` stale before the folded Step 3/4/4.r composite commits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `skills/implement/SKILL.md` Step 2.4 (ordinary fallback and retained recovery prose), pin one bind immediately before any orchestrator `recovery-paths` call, e.g. `REPO_ROOT="$(git rev-parse --show-toplevel)"` with fail-closed abort when empty/non-zero; state explicitly that `REPO` must not substitute for `REPO_ROOT`.
  - From Cursor-Requirements: Add `--repo-root "$REPO_ROOT"` to the section 4 repair-refresh pin (bind `REPO_ROOT` via `git rev-parse --show-toplevel` in SKILL prose) and mirror the full absolute argv from the Step 2.4 ordinary-fallback wire: prelaunch porcelain, fresh postlaunch porcelain, prelaunch digests, and `implementation-commit-paths.nul` out-file.


### [Plan Review] FINDING_4

### FINDING_4: `commit_route_main` rejects valid `noop` outcome
- **Reviewer(s)**: Codex-Arch
- **Severity**: blocking
- **Concern**: The new `noop` commit-route outcome is required for the Step 4 external no-op path, but `commit_route_main` still returns exit code 1 unless the outcome is `continue` or `seeded-stall`. Direct callers (including `_step5_resume_commit_phase`) treat a valid no-op as failure and halt the fold.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Include `noop` in the zero-exit branch of `commit_route_main` so the subprocess exit code matches the widened outcome contract.


### [Plan Review] FINDING_6

### FINDING_6: Post-dispatch `--expected-branch` change lacks fenced SKILL example
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan describes passing `--expected-branch "$BRANCH_NAME"` to post-dispatch in prose only. The current SKILL fence still calls `step-2-post-dispatch.sh` with no args, so a literal edit from fenced examples alone can ship routing prose while omitting the required flag and weakening the branch assertion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add an explicit SKILL fenced bash block in the plan showing `bash "$IMPLEMENT_TMPDIR/larch-run.sh" skills/implement/scripts/step-2-post-dispatch.sh --expected-branch "$BRANCH_NAME"` and require removing the old exit-code-first branch-compare cascade in the same edit.


