# Review Round 1

- Mode: `diff`
- 15 accepted, 7 rejected (1 neutral)

## Accepted Findings

### FINDING_10: Orchestrator-fence harness still mirrors pre-loop handoff
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-state-machine-output.txt
- **Severity**: important
- **Concern**: `test-step3-orchestrator-fence.sh` still tests the old `--no-preview` / `LOOP_STATUS` handoff and lacks coverage for `STEP3_REVIEW_LOOP_STATUS`, bail-out routing, postplan failure, and `--mode loop --starting-round` resume.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.
  - From dyn-state-machine-output.txt: Address the concern above.


### FINDING_11: Multi-round integration test still exercises legacy two-call flow
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `scripts/test-design-multi-round-integration.sh` chains two `--no-preview` invocations instead of testing the new script-internal `--mode loop` multi-round path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_12: Loop-mode status validation uses the wrong enum and stale state
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, dyn-state-machine-output.txt
- **Severity**: important
- **Concern**: Loop-mode parsing validates or falls back to legacy `LOOP_STATUS` instead of requiring a fresh closed-enum `STEP3_REVIEW_LOOP_STATUS`, so missing/mistyped envelopes or nonzero launcher exits can pass through on stale `LOOP_STATUS=complete`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From dyn-state-machine-output.txt: Address the concern above.


### FINDING_13: `awaiting-post-apply` resume can skip dedup
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: If the process dies after writing `awaiting-post-apply` but before dedup completes, resume jumps to postplan/snapshot on an undeduped plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_15: Auto-apply does not persist `awaiting-apply` before applying
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: If the process dies after review count persistence but before auto-apply, restart can advance to the next round and skip applying accepted findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_16: Terminal loop transitions lack the needed Step 3.5/bypass resume sentinel
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Terminal loop statuses write only `.completed/step-3`, so a halt before Step 3b can resume at Step 3.5 and rerun Gate B/continuation instead of respecting the completed loop transition.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_17: Continuation-helper failures are ignored
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Nonzero or malformed `plan-review-continuation.sh` results can be converted into `complete`, silently skipping required follow-up rounds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_18: Per-round approval resume ignores the operator’s filtered decision
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: After `--per-round-approval`, resume from `awaiting-apply` applies the full accepted findings set rather than the operator-approved subset.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_19: Step 3.5 prelude can mark Step 3 complete on bail-outs
- **Reviewer(s)**: dyn-state-machine-output.txt
- **Severity**: important
- **Concern**: The Step 3.5 entry fence unconditionally writes `.completed/step-3`, so a mis-routed loop bail-out can be marked complete before apply/postplan/continuation has finished.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-machine-output.txt: Address the concern above.


### FINDING_21: MAV re-tally failure does not roll back consumed round state
- **Reviewer(s)**: dyn-sole-writer-invariant-output.txt
- **Severity**: important
- **Concern**: If MainAgent re-tally fails after a `main-agent-vote-required` bail-out, the flow can leave `review-round-count.txt`, `.step3-round-N.phase`, and pre-apply state stale instead of rolling back like in-loop tally errors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sole-writer-invariant-output.txt: Address the concern above.


### FINDING_5: Predictable shared `/tmp` capture file is unsafe
- **Reviewer(s)**: cursor-specialist-security-output.txt, codex-specialist-security-output.txt
- **Severity**: important
- **Concern**: Round-body output is written to a predictable `/tmp/larch-step3-round-body.$$` path, creating symlink/truncation and information-disclosure risks on shared machines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From codex-specialist-security-output.txt: Address the concern above.


### FINDING_6: Legacy Step 3.5 / `--no-preview` routing can double-apply or re-enter retired orchestration
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-state-machine-output.txt
- **Severity**: important
- **Concern**: `SKILL.md` still contains legacy Step 3.5 Gate B and heuristic continuation prose that routes from `LOOP_STATUS` or re-runs `run-step3-review.sh --no-preview` after the new loop has already applied findings or produced a loop bail-out envelope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.
  - From dyn-state-machine-output.txt: Address the concern above.


### FINDING_7: Terminal loop status is not durably persisted to result env
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-state-machine-output.txt
- **Severity**: important
- **Concern**: `STEP3_REVIEW_LOOP_STATUS` and related terminal/bail-out keys are emitted to stdout only, leaving `.step3-review-result.env` with stale per-round `LOOP_STATUS=complete` and causing resume or env-file consumers to route incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From dyn-state-machine-output.txt: Address the concern above.


### FINDING_8: HARD snapshot helpers can be skipped while reporting success
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `post_apply` skips HARD snapshot helpers when they are missing or non-executable but still returns success, allowing the next round cursor to advance without the required snapshot.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_9: Postplan pause loses issue threading
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: The postplan pause path uses `--issue 0` when `ISSUE_NUMBER` is unset, unlike `honor_pause`, so mid-loop pause can save to the wrong issue or break the pause contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


