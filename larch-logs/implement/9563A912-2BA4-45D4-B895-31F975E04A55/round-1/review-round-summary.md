# Review Round 1

- Mode: `diff`
- 10 accepted, 4 rejected (3 neutral)

## Accepted Findings

### FINDING_1: Step 5 resume success path can double-record review timing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `SKILL.md` still instructs the orchestrator to run prompt-side review-round timing before `step-5-resume.sh`, while the wrapper now records that timing internally. Following both paths can duplicate timing rows and inflate Step 5 duration/cost reports.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_10: Step 8 ship wrapper is not self-rehydrating
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `step-8-ship.sh` dereferences transient prompt variables under `set -u` and defaults merge/draft/fork flags instead of rehydrating from state. Timeout or recovery invocations can abort before JSON routing or pass incorrect flags such as `--merge false`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_11: Release dry-run can mutate local main via real rebase sync
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `/release --dry-run` now performs a real rebase/sync despite the dry-run preview-only/no-write contract. On a stale local main, a dry run can mutate the branch or worktree before release preparation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_13: Dirty-tree recovery prose still names the old bootstrap entrypoint
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Dirty-tree recovery prose and routing tables still refer to `implement-bootstrap-invoke.sh --mode resume`, while the fence uses `step-0-bootstrap.sh --mode resume`. Following the prose can bypass Step 0 wrapper behavior such as `--preserve-coder`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_18: Step 16 wrapper can abort on unbound RUN_ID
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `step-16.sh` expands `RUN_ID` under `set -u`, but `SKILL.md` invokes it without exporting `RUN_ID`. Terminal Step 16 can abort before rejected-findings reporting and block final report/cleanup continuation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_2: Step 5 terminal-stall record-only path is missing or too late
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The Step 5 terminal-stall path is not consistently routed through `step-5-resume.sh --record-only`, and the wrapper may reach commit/reinvoke behavior before honoring record-only mode. Terminal stalls can therefore omit handoff timing or perform unintended resume/commit actions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_20: Forked-target rebase checkpoint flag lacks offline harness coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The new `--forked-target` flag on `rebase-checkpoint-probe.sh` has no offline harness case. A broken `--forked-target true` mapping to `upstream/main` could pass CI and break fork-mode rebase checkpoints.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_3: Wrapper fences may run without exported IMPLEMENT_TMPDIR
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The removed per-fence `IMPLEMENT_TMPDIR` export preambles can leave wrapper invocations without required environment state. Guard-plus-wrapper fences may abort at Step 3+ with `IMPLEMENT_TMPDIR required`, and the timing rehydration harness no longer enforces this invariant.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_7: Step 8 OOS checkpoint wrapper exits non-zero on success
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `step-8-oos-checkpoint.sh` can return status 1 after a successful `oos-disposition-checkpoint.sh` run because a final false test becomes the script exit status. This can stop Step 8+ as though the checkpoint failed even after printing `OOS_CHECKPOINT_RC=0`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_8: Fork bootstrap metadata is emitted but not parsed before invoke
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `step-0-bootstrap.sh` does not capture and parse `implement-fork-env.sh` stdout into `CALLER_ENV_PATH`, `UPSTREAM_REPO`, and related fork keys before bootstrap invocation. `/implement --forked` can therefore run without `--caller-env` and target the wrong repo/context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


