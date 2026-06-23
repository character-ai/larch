### FINDING_1: `_git_status_porcelain()` masks failed `git status` as a clean tree
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: `_git_status_porcelain()` (via `_git_output()`) returns empty stdout on non-zero `git status --porcelain` exit, so a failed probe looks like a clean tree. With `COMMIT_OUTCOME` authoritative at Step 7 and self-review after prompt-side porcelain probes are removed, the post-commit `--stage-all` success branch and the existing pre-commit clean-tree gate can emit `COMMIT_OUTCOME=ok` or `COMMIT_OUTCOME=noop` and return `0` without verifying cleanliness. The run can advance with an unknown or still-dirty tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the `--stage-all` success branch only, probe porcelain with `_run` (or equivalent) and fail closed on non-zero git status: emit `COMMIT_OUTCOME=failed`, keep `COMMITTED=true`/`SHA=` when present, set a concise `ERROR=`, return `1`. Add a commit_fixes regression test that monkeypatches post-commit `git status` failure after commit success.

### FINDING_2: Step 5 lacks-envelope routing has overlapping exit rules without precedence
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: important
- **Concern**: When stdout lacks `STEP5_REVIEW_STATUS=` and `COMMIT_OUTCOME` is absent, malformed, or `failed`, the wrapper exits non-zero. Overlapping bullets route that case both to `resume-handoff-commit-failed` (commit-phase durable bail) and to generic Step 18 preflight. An implementer who checks wrapper exit code first can skip the commit-failure handoff and seed the wrong stall reason or recovery path, breaking the fail-closed handoff stall contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Rewrite the lacks-`STEP5_REVIEW_STATUS` block as explicit if/elif order: (1) `COMMIT_OUTCOME` not exactly `ok` or `noop` -> `resume-handoff-commit-failed`; (2) `COMMIT_OUTCOME` `ok|noop` without status -> Step 5 preflight to Step 18; drop or narrow the standalone non-zero-exit bullet so it cannot override (1). Pin that ordering in `scripts/test-implement-structure.sh`.
  - From Cursor-Requirements: State explicit precedence in the lacks-envelope branch: evaluate COMMIT_OUTCOME allowlist first; use resume-handoff-commit-failed whenever COMMIT_OUTCOME is not exactly ok or noop; reserve the line 102 preflight rule only for ok/noop without STEP5_REVIEW_STATUS= (or delete line 102 as redundant with line 101).

### FINDING_3: Self-review Step 5 item 7 lacks a `test-implement-structure.sh` pin
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan requires self-review Step 5 item 7 to parse `COMMIT_OUTCOME` with the same allowlist and `review-fix-commit-failed` stall wiring as Step 7, but `scripts/test-implement-structure.sh` only pins Step 7 `STALL_REASON=review-fix-commit-failed` and Step 5 resume prose. No `require()` pin covers self-review `COMMIT_OUTCOME` routing, so an implementer can omit the self-review SKILL update and lint still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add a test-implement-structure.sh require() pin for self-review item 7 COMMIT_OUTCOME allowlist and review-fix-commit-failed stall wiring, parallel to the existing Step 7 pin at line 332.

### FINDING_4: Token-aware `COMMIT_OUTCOME` parsing can be spoofed by `ERROR` text
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: `commit-fixes` keeps free-form `ERROR` output from git stderr. A failing pathspec or filename can contain a whitespace token like `COMMIT_OUTCOME=ok`. Token-aware scanning at SKILL callers can read that token from `ERROR` instead of the helper's newline-delimited `COMMIT_OUTCOME=failed` record, so Step 5 or Step 7 can continue after a failed commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Parse COMMIT_OUTCOME only from newline-delimited records whose key is exactly COMMIT_OUTCOME at the start of the line, and make step-5-resume.sh use the same line-anchored rule for its internal gate. Keep token-aware parsing only for the Step 5 review-loop envelope keys that need it.
