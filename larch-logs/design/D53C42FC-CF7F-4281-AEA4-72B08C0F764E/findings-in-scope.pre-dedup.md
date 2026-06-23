### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_and_fix.py:227-229
- **Concern**: The new post-commit `--stage-all` probe reuses `_git_status_porcelain()`, which masks non-zero `git status` as empty stdout.. Scenario: The plan makes `COMMIT_OUTCOME=ok` authoritative at Step 7 and self-review after removing prompt-side porcelain probes. If `git status --porcelain` fails after a successful pathspec commit, the helper can emit `COMMIT_OUTCOME=ok` and return `0` even though cleanliness was not verified, so the run can advance with an unknown or still-dirty tree.
- **Proposed resolution**: In the `--stage-all` success branch only, probe porcelain with `_run` (or equivalent) and fail closed on non-zero git status: emit `COMMIT_OUTCOME=failed`, keep `COMMITTED=true`/`SHA=` when present, set a concise `ERROR=`, return `1`. Add a commit_fixes regression test that monkeypatches post-commit `git status` failure after commit success.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:99-102
- **Concern**: Step 5 resume lacks-envelope routing can treat commit-phase failure as generic preflight.. Scenario: Under the planned bullets, `COMMIT_OUTCOME=failed` with wrapper exit non-zero matches both resume-handoff (`COMMIT_OUTCOME` not `ok|noop`) and the preserved rule that non-zero stdout without `STEP5_REVIEW_STATUS=` is generic Step 18 preflight. An implementer who checks wrapper rc first can skip `resume-handoff-commit-failed` durable bail and seed the wrong stall reason/recovery path.
- **Proposed resolution**: Rewrite the lacks-`STEP5_REVIEW_STATUS` block as explicit if/elif order: (1) `COMMIT_OUTCOME` not exactly `ok` or `noop` -> `resume-handoff-commit-failed`; (2) `COMMIT_OUTCOME` `ok|noop` without status -> Step 5 preflight to Step 18; drop or narrow the standalone non-zero-exit bullet so it cannot override (1). Pin that ordering in `scripts/test-implement-structure.sh`.



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_and_fix.py:227-238
- **Concern**: The plan makes `commit-fixes` authoritative for `--stage-all` cleanliness but does not harden `_git_status_porcelain()` when `git status` errors. `_git_output()` returns `""` on non-zero exit, so a failed probe looks like a clean tree. After prompt-side porcelain is removed from Step 7 and self-review, that can emit `COMMIT_OUTCOME=noop` or `COMMIT_OUTCOME=ok` and return `0` without verifying the tree. Step 7 or self-review can advance with a dirty or uncommitted tree.. Scenario: In the new post-commit `--stage-all` success branch and the existing pre-commit clean-tree gate, treat non-zero `git status --porcelain` exit as failure: emit `COMMIT_OUTCOME=failed`, set a concise `ERROR=` (for example `git status failed`), and return `1`. Add one regression test that mocks `_run(["git","status","--porcelain"])` returning non-zero with empty stdout and asserts `COMMIT_OUTCOME=failed`, not `ok` or `noop`.
- **Proposed resolution**: 



### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:99-102
- **Concern**: Step 5 lacks-envelope routing lists overlapping exit rules without precedence. Scenario: When stdout lacks STEP5_REVIEW_STATUS= and COMMIT_OUTCOME is absent, malformed, or failed, the wrapper exits non-zero. Line 100 routes that to resume-handoff-commit-failed with Tool Failures logging and ship-pr-state durable bail. Line 102 also says any wrapper non-zero exit without STEP5_REVIEW_STATUS= is a generic Step 18 preflight skip. An implementer can follow line 102 and omit STALL_REASON=resume-handoff-commit-failed, breaking the fail-closed handoff stall contract the issue targets.
- **Proposed resolution**: State explicit precedence in the lacks-envelope branch: evaluate COMMIT_OUTCOME allowlist first; use resume-handoff-commit-failed whenever COMMIT_OUTCOME is not exactly ok or noop; reserve the line 102 preflight rule only for ok/noop without STEP5_REVIEW_STATUS= (or delete line 102 as redundant with line 101).



### FINDING_5:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-structure.sh:332-141
- **Concern**: Third commit-fixes --stage-all caller lacks lint harness pin. Scenario: The plan requires self-review Step 5 item 7 to parse COMMIT_OUTCOME with the same allowlist and review-fix-commit-failed stall wiring as Step 7, but scripts/test-implement-structure.sh updates only pin Step 7 STALL_REASON=review-fix-commit-failed and Step 5 resume prose. No require() pin covers self-review COMMIT_OUTCOME routing. An implementer can omit the self-review SKILL update and make lint still pass.
- **Proposed resolution**: Add a test-implement-structure.sh require() pin for self-review item 7 COMMIT_OUTCOME allowlist and review-fix-commit-failed stall wiring, parallel to the existing Step 7 pin at line 332.



### FINDING_6:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:668,719
- **Concern**: Token-aware COMMIT_OUTCOME parsing can be spoofed by ERROR text. Scenario: commit-fixes keeps free-form ERROR output from git stderr. A failing pathspec or filename can contain a whitespace token like COMMIT_OUTCOME=ok. The planned token-aware scan at the SKILL callers can read that token from ERROR instead of the helper's newline-delimited COMMIT_OUTCOME=failed record, so Step 5 or Step 7 can continue after a failed commit.
- **Proposed resolution**: Parse COMMIT_OUTCOME only from newline-delimited records whose key is exactly COMMIT_OUTCOME at the start of the line, and make step-5-resume.sh use the same line-anchored rule for its internal gate. Keep token-aware parsing only for the Step 5 review-loop envelope keys that need it.



