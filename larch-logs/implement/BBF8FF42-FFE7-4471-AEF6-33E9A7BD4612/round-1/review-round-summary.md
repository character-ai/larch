# Review Round 1

- Mode: `diff`
- 6 accepted, 5 rejected (4 neutral)

## Accepted Findings

### FINDING_1: Empty cwd disables repository filtering for live-run discovery
- **Reviewer(s)**: cursor-specialist-security-output.txt, codex-specialist-security-output.txt
- **Severity**: important
- **Concern**: If the UserPromptSubmit payload omits or supplies an empty `cwd`, progress discovery can fall back to the newest live run from another repository, leaking or blocking on unrelated repo progress.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, codex-specialist-security-output.txt: Address the concern above.


### FINDING_10: Cwd discovery requires exact string match without canonicalization
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `REPO_CWD` is stored and compared as raw strings, so symlink or `/var` vs `/private/var` path differences can make an active implement run undiscoverable; the planned fallback to a newest valid pointer is also missing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_11: Cleanup does not reap stale implement pointer files
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-pointer-lifecycle-output.txt
- **Severity**: important
- **Concern**: `/cleanup` only reaps dangling design symlinks, so crashed implement runs can leave `current-implement-env-*.sh` pointer files indefinitely when tmpdirs disappear or become invalid.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-pointer-lifecycle-output.txt: Address the concern above.


### FINDING_15: Step 5 done marker persists into resumed review loops
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Loop mode writes `progress/done` on exit but does not clear stale markers at the next loop start, so resumed Step 5 review loops can run while `progress_report.py` suppresses the Step 5 renderer and falls back to generic output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_16: Ship-pr progress rendering omits real phases and CI status fields
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Actual ship phases such as `rebase` and `stalled` are not recognized, and available CI status fields are omitted, so `p` can fall through to generic output or underreport CI state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_33: CI in-progress timeout is misclassified as fix exhaustion
- **Reviewer(s)**: dyn-ci-inprogress-block-output.txt
- **Severity**: important
- **Concern**: When waiting for CI logs times out while the run remains `in_progress`, `evaluate_failure()` returns `fix-exhausted` even if no fixer ran, causing persisted counters to treat a wait timeout as a failed fix cycle.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-inprogress-block-output.txt: Address the concern above.


