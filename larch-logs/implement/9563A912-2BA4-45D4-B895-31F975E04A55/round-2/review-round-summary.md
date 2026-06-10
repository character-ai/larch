# Review Round 2

- Mode: `diff`
- 5 accepted, 3 rejected (3 neutral)

## Accepted Findings

### FINDING_1: Step 0 wrapper drops required run context after fence refactor
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-kv-forwarding-output.txt
- **Severity**: important
- **Concern**: `step-0-bootstrap.sh` only accepts `--mode` and relies on ambient env, while the SKILL Step 0 fence no longer exports `TARGET_ISSUE_NUMBER`, `PREFLIGHT_TMPDIR`, coder, or flags. Fresh `/implement` runs can omit issue/preflight/coder routing and fail to materialize the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From dyn-kv-forwarding-output.txt: Address the concern above.


### FINDING_16: Fence-shape harness allows inline shell control logic after script calls
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The harness can pass while SKILL fences still contain inline constructs such as `|| true`, violating the no-inline-logic acceptance criterion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_3: Step 18a stall-tracking KV reads subprocess env instead of orchestrator memory
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `STALL_TRACKING_MEMORY` is usually emitted false because the shell subprocess cannot see orchestrator memory, so recovery gating can disagree with the orchestrator’s actual `STALL_TRACKING=true` state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_6: Step 8 wrapper cannot forward bash ship-pr resume phases
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: With `LARCH_SHIP_PR_IMPL=bash`, `step-8-ship.sh` does not pass `--resume-phase` to `ship-pr.sh`, so conflict-resolution continuation phases can skip the intended rebase/push continuation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_7: Ship-pr exit matrix still routes re-invocations around step-8 wrapper
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-reference-completeness-output.txt
- **Severity**: important
- **Concern**: `ship-pr-exit-matrix.md` still tells agents to invoke `ship-pr.sh` or raw `python3 python/cli.py ship pr`, bypassing `step-8-ship.sh` state rehydration, argv assembly, Python 3.11 guard, and wrapper contracts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-reference-completeness-output.txt: Address the concern above.


