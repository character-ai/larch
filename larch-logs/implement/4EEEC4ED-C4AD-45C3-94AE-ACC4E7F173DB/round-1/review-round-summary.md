# Review Round 1

- Mode: `diff`
- 2 accepted, 5 rejected (2 neutral)

## Accepted Findings

### FINDING_1: Clean-tree lint-fix path skips pre-lint snapshot and stalls Step 5
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `pre_lint_head` is only captured when the tree is already dirty at lint-loop entry. After a clean review-fix commit, lint-fix can apply edits and return `main-agent-required` with `lint_applied_ever` true and a dirty tree, but `_lint_loop_successful_break` skips commit because `pre_lint_head` is empty. Step 5 then stalls toward ship with uncommitted lint deltas, recreating the dirty-tree stall-recovery bug.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: On first lint_status == applied, if pre_lint_head is empty and porcelain is non-empty, call _write_pre_lint_snapshot before _lint_loop_successful_break can run.
  - From codex-specialist-correctness-output.txt: Always capture the pre-lint HEAD before the lint-fix loop and keep filtering commit paths through the existing delta logic
  - From cursor-specialist-edge-cases-output.txt: Always call _write_pre_lint_snapshot at lint-loop entry (including clean trees), or snapshot lazily on first applied before delta comparison; add a test with empty initial porcelain and applied→main-agent-required asserting commit.
  - From codex-specialist-edge-cases-output.txt: Capture the pre-lint snapshot unconditionally or before the first applied lint-fix; add a clean-baseline regression


### FINDING_3: Rebase-probe failure flush can stage larch logs during an in-progress conflict
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: On checkpoint-probe exit 1, the repo can remain in an in-progress rebase with unresolved conflicts. A failure-path flush that stages `larch-logs` before commit can leave those paths staged when `rebase --continue` replays the commit, accidentally including run-log files in conflict recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Use a non-staging flush on probe failure, or reset staged log paths and defer commit until the repo is clean


