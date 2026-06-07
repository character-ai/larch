### OOS_1: [OUT_OF_SCOPE] Security OOS blocks may not route as security
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `is_security_block` does not recognize the emitted `Focus area` field spelling, so accepted security OOS blocks may be published instead of held locally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] Plan review line still depends on `voting-tally.md`
- **Reviewer(s)**: dyn-contract-sync-output.txt
- **Severity**: latent
- **Concern**: `render-final-summary.sh` still gates the Plan review line on `voting-tally.md` existence, so accepted findings can render as `0 findings` if the tally file is absent on failure paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-sync-output.txt: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] Automatic re-entry leaves stale sentinels and pause/resume state
- **Reviewer(s)**: codex-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-state-flow-output.txt, dyn-contract-sync-output.txt
- **Severity**: important
- **Concern**: The automatic continuation path does not use the same Step 3 re-entry/state cleanup as manual reruns, leaving `.completed/step-3`, Gate B post-apply markers, and pause/resume fingerprints that can skip the intended follow-up review or reuse stale artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-state-flow-output.txt, dyn-contract-sync-output.txt: Address the concern above.


### OOS_4: [OUT_OF_SCOPE] Multi-round loop is prompt-only and insufficiently pinned
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-state-flow-output.txt, dyn-shell-awk-output.txt, dyn-contract-sync-output.txt
- **Severity**: important
- **Concern**: The new continuation behavior lacks script-level enforcement and structural/integration harness pins, so future edits can drop or break the loop while CI remains green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-state-flow-output.txt, dyn-shell-awk-output.txt, dyn-contract-sync-output.txt: Address the concern above.


### OOS_5: [OUT_OF_SCOPE] Single-pass documentation remains stale
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-state-flow-output.txt, dyn-shell-awk-output.txt, dyn-contract-sync-output.txt
- **Severity**: important
- **Concern**: `SKILL.md`, `plan-review.md`, `flags.md`, `plan-review-loop.md`, and approval-gate invariants still describe Step 3 as single-pass, conflicting with the new outer heuristic loop and misleading operators/contributors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-state-flow-output.txt, dyn-shell-awk-output.txt, dyn-contract-sync-output.txt: Address the concern above.


