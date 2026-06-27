# Review Round 1

- Mode: `diff`
- 3 accepted, 3 rejected (1 neutral)

## Accepted Findings

### FINDING_2: Text fallback regex omits in progress
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-edge-cases
- **Severity**: important
- **Concern**: `_CHECKS_TEXT_BAD_RE` does not treat `in progress` as blocking, unlike the CI monitor text parser. A fallback `gh pr checks` line like `lint\tin progress\t0\t0` can be classified as pass in `pr_checks_all_pass`, so ship may merge while CI is still active.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add in progress to _CHECKS_TEXT_BAD_RE and add regression test
  - From codex-specialist-edge-cases: Add in progress to _CHECKS_TEXT_BAD_RE and cover it with a regression test


### FINDING_3: pr_checks_not_ready_detail discards usable stdout on non-zero gh exit
- **Reviewer(s)**: cursor-specialist-correctness, codex-generalist
- **Severity**: important
- **Concern**: `pr_checks_not_ready_detail` returns a generic `unable to read PR checks` message whenever `gh pr checks` exits non-zero, even when stdout contains usable pending-check text (for example `lint\tpending\t0\t0`). `pr_checks_all_pass` still inspects non-transient non-zero text stdout, so `merge_pr` can return `CI_NOT_READY` while the diagnostic helper omits the stuck-check detail that `ship.py` stall logic needs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Mirror pr_checks_all_pass: parse non-transient non-zero text stdout before returning generic unable-to-read message
  - From codex-generalist: Parse JSON stdout before checking `result.returncode`, and for non-transient non-zero text results, pass `text_result.stdout` to `_pr_checks_text_not_ready_detail` instead of returning the generic message. Add a regression where both JSON/text commands return a pending-check exit code with stdout.


### FINDING_4: _CiNotReadyGuard false-stalls on race diagnostic
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-ci-merge-policy
- **Severity**: important
- **Concern**: `_CiNotReadyGuard` counts consecutive identical `"no fail or pending PR checks remain"` diagnostics toward `SHIP_MERGE_CI_NOT_READY_STALL_THRESHOLD`, but that string is emitted when a follow-up read sees mergeable JSON under the new policy even though an earlier `merge_pr` call already returned `CI_NOT_READY`. This TOCTOU / transient-read race can terminal-stall an otherwise mergeable PR instead of retrying until merge succeeds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Exclude race-like diagnostics from unchanged-detail counting or reset guard when diagnostic indicates mergeable checks
  - From dyn-dyn-ci-merge-policy: Do not count `"no fail or pending PR checks remain"` (and similar race-shaped messages) toward `SHIP_MERGE_CI_NOT_READY_STALL_THRESHOLD`, or capture the blocking snapshot from the same classifier invocation that made `pr_checks_all_pass` return `False` and pass that into the guard.


