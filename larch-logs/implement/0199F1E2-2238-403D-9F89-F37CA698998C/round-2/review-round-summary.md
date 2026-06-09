# Review Round 2

- Mode: `diff`
- 9 accepted, 5 rejected (2 neutral)

## Accepted Findings

### FINDING_10: Omitted --starting-round skips unfinished in-loop pause phases
- **Reviewer(s)**: codex-specialist-correctness-output.txt, dyn-state-protocol-output.txt
- **Severity**: important
- **Concern**: When --starting-round is omitted, run-step3-review.sh defaults to review-round-count + 1. After an in-loop pause where round N has an awaiting-* phase and count=N, resume jumps to round N+1 and abandons unfinished apply/postplan/continuation work for round N.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, dyn-state-protocol-output.txt: Address the concern above.


### FINDING_11: approval-gates.md still documents retired Gate B / single-pass semantics
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The Gate B reference still says Step 3 accepted findings are not applied in-loop and that complete means plan.txt is unchanged. In loop mode, complete means the waterfall may already have applied findings, so the stale reference can cause double-apply or legacy continuation routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_12: Loop and Gate B bypass disagree on ownership of .completed/step-3.5
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt, dyn-legacy-coexistence-output.txt
- **Severity**: important
- **Concern**: The loop writes .completed/step-3.5 on terminal exits even though Step 3b / gate-b-bypass also owns that sentinel. design-step3-state.sh --gate-b-bypass can then refuse partial bypass, and the SKILL sentinel table contradicts the new ownership model.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt, dyn-legacy-coexistence-output.txt: Address the concern above.


### FINDING_15: Loop envelope overwrites durable Step 3 result env fields
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The loop persists .step3-review-result.env with a reduced key set, dropping existing handoff fields such as tally, aggregator, voting tally, panel, and round metadata required by the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_16: Step 3.5 prelude can fail when .completed is absent
- **Reviewer(s)**: dyn-state-protocol-output.txt
- **Severity**: important
- **Concern**: The Step 3.5 fence touches "$DESIGN_TMPDIR/.completed/step-3" without ensuring the .completed directory exists, so bail-out paths that did not already create the directory can fail before Gate B runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-protocol-output.txt: Address the concern above.


### FINDING_5: Per-round approval selection is consumed before validation and successful apply
- **Reviewer(s)**: cursor-specialist-security-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The approval env / FINDINGS_FILE path is consumed or deleted before validating the selected findings file and before apply+dedup succeeds. Failures can lose the user-filtered subset and later recover by applying the full accepted findings set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_6: MainAgent vote recovery still points at legacy Gate B instead of loop resume
- **Reviewer(s)**: codex-specialist-security-output.txt, dyn-state-protocol-output.txt
- **Severity**: important
- **Concern**: The MainAgent vote/re-tally prose still instructs Gate B or legacy complete-equivalent continuation instead of resuming the script-internal loop with the correct phase and starting round. This can bypass the one-call Step 3 loop contract and risk duplicate or skipped apply/postplan work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt, dyn-state-protocol-output.txt: Address the concern above.


### FINDING_7: Loop bail-outs and postplan failures can be normalized or marked as complete
- **Reviewer(s)**: codex-specialist-security-output.txt, dyn-state-protocol-output.txt, dyn-legacy-coexistence-output.txt
- **Severity**: important
- **Concern**: The Step 3 handoff/Step 3.5 prelude collapses postplan-failed and several mid-loop bail-outs into complete-like routing and writes .completed/step-3 before filtering those statuses. This can advance to Gate B/Step 3b with an invalid plan or make pause/resume re-enter the wrong surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt, dyn-state-protocol-output.txt, dyn-legacy-coexistence-output.txt: Address the concern above.


### FINDING_9: MainAgent vote resume bypasses per-round approval
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: After main-agent-vote-required, the resume path can proceed directly to awaiting-apply and rewrite plan.txt without re-emitting or persisting the required --per-round-approval decision.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


