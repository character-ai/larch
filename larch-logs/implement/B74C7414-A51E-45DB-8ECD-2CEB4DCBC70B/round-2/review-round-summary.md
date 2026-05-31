# Review Round 2

- Mode: `diff`
- 4 accepted, 4 rejected (4 exonerated)

## Accepted Findings

### FINDING_1: Step5 harness lacks shared production `pre_coder_snapshot_dir`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-bash32-output.txt, dyn-step5-flow-output.txt
- **Severity**: important
- **Concern**: `step5-starting-round` sources `review-implement-step5-loop.sh` without also defining the production `pre_coder_snapshot_dir` helper now used by fix-applied Step 5 paths. Some new cases avoid this by duplicating inline stubs, but any unstubbed path reaching the structural/MAV relocation logic can fail with `command not found`, and duplicated stubs can drift from production.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-bash32-output.txt, dyn-step5-flow-output.txt: Address the concern above.


### FINDING_10: Snapshot integrity is not enforced outside `PWD` / all Codex grants
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-snapshot-tamper-output.txt
- **Severity**: important
- **Concern**: The new invariant protects against snapshots under `round_dir`, but Codex dispatch also grants `--add-dir "$PWD"`. If `IMPLEMENT_TMPDIR` is placed inside the repo, relocated snapshots under `$IMPLEMENT_TMPDIR/.pre-coder-snapshots` are still inside the `PWD` grant and remain tamperable, weakening the carryover guard despite relocation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-snapshot-tamper-output.txt: Address the concern above.


### FINDING_12: `post_pre_head_file` leaks as a global
- **Reviewer(s)**: dyn-bash32-output.txt
- **Severity**: nit
- **Concern**: `run_implement_loop` assigns `post_pre_head_file` without declaring it `local`, unlike neighboring loop state, so sourcing the loop in harnesses can leak the variable into the parent shell.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash32-output.txt: Address the concern above.


### FINDING_6: New Step 5 acceptance tests are not wired into CI
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The relocated structural LOC and MAV relocation tests live in `step5-starting-round`, but that section lacks a Makefile recipe / harness shard, so CI may never run the new acceptance coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


