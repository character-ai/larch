# Review Round 1

- Mode: `diff`
- 1 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Ancestor-skip regression test does not exercise grandparent chain
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-teardown-safety-output.txt
- **Severity**: important
- **Concern**: The new ancestor-skip regression in `scripts/test-implement-finalize.sh` configures the fake ancestor as the teardown shell’s immediate parent (`STUB_PS_PPID="$FAKE_ANCESTOR_PID"`), so the fake ancestor stays in the skip set even if `collect_ancestor_pids` is removed and only legacy direct-`ppid` skip remains. The production failure mode was a grandparent wrapper (e.g. `step-18-finalize.sh` → `larch-run.sh` → `implement-finalize.sh`) with `IMPLEMENT_TMPDIR` in argv being signalled; this test would pass on the old parent-only logic and would not catch a regression of grandparent protection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Stub a three-level parent map (teardown shell -> intermediate -> fake ancestor), list only the grandparent in the process output with tmpdir argv, and assert it survives while a stale non-ancestor is killed.
  - From cursor-specialist-testing-output.txt: Model an intermediate parent PID (not in the kill list) between $$ and FAKE_ANCESTOR_PID via STUB_PS_PARENT_MAP; keep only the grandparent in STUB_PS_PROCESS_LIST; assert stale kill + grandparent survival and verify the test fails on parent-only skip.
  - From dyn-teardown-safety-output.txt: Stub a three-level chain (teardown PID → intermediate parent → grandparent with tmpdir in argv), assert only the stale non-ancestor is killed, and assert the grandparent survives when `collect_ancestor_pids` is the sole source of that skip (no direct-ppid shortcut to the grandparent).


