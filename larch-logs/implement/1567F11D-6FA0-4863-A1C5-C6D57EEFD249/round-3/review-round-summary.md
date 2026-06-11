# Review Round 3

- Mode: `diff`
- 16 accepted, 6 rejected (5 neutral)

## Accepted Findings

### FINDING_1: Collector infers sketch paths from tool availability instead of launched slots
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Step 2a.3 collects paths from availability flags while SKILL passes only `--mode`. It can wait for unlaunched slots, miss launched fallback slots, and build the wrong sketch set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_12: Proceed route does not write the feature description file
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The Step 0 proceed path does not write `DESIGN_TMPDIR/feature-description.txt` before sketches. Step 2a can sketch from missing or stale feature text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_13: Deleted Step 3b-to-Step 4 route guard was not restored
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `assert_no_direct_step3b_step4_routes` was removed despite the plan requiring it unchanged. SKILL prose can route directly from Step 3b to Step 4 without the completion boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_15: Postplan thin-fence behavior lost executable tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Postplan behavioral tests and negative self-tests were removed. Missing `case` arms or wrong drift-arm sentinel writes in `design-step2b-postplan.sh` can pass grep-only pins.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_17: Step 5c publish and cleanup paths lack hermetic tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: There are no stubbed tests for rc 3 fallback, rc 4 validator handoff, `PLAN_WRITE_OK` gating, publish failure, or cleanup eligibility. Static pins can miss publish and cleanup regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_18: Step 3 harness still tests duplicated logic instead of the wrapper
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Most Step 3 handoff cases exercise duplicated `apply_step3_handoff` logic rather than `design-step3-review.sh`. Wrapper behavior can diverge while CI stays green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_2: Zero-slot collection can continue without a fatal or degraded handoff
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Empty launched-path collection exits as skipped or before pause handling. HARD runs can continue without sketches, without degraded sentinels, or without honoring a pause request.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_22: HARD zero-sketch wrapper omits required degraded artifacts
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `design-step2a-zero-sketch.sh` writes completion sentinels without required degraded artifacts or warning logs. HARD both-tools-down runs can enter Step 2b without synthesis files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_3: Step 4b writes the step-4 sentinel after pause-sensitive preview work
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `design-step4b.sh` writes `.completed/step-4` after Gate C preview/read instead of before the first pause check. A pause during Gate C can resume at the wrong boundary and re-emit preview work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_32: Pause-save calls omit repo forwarding on several wrappers
- **Reviewer(s)**: dyn-risk-integration-output.txt
- **Severity**: important
- **Concern**: Several wrappers call `design-pause-save.sh` without forwarding `${REPO:+--repo "$REPO"}`. Fork or multi-repo pauses can write state against the wrong repo.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-risk-integration-output.txt: Address the concern above.


### FINDING_33: Family-B polling fence absence check was removed
- **Reviewer(s)**: dyn-risk-integration-output.txt
- **Severity**: important
- **Concern**: The harness no longer sources `lib-p3119-fence-absence.sh` or calls `assert_p3119_family_b_fence_absent`. Prohibited `run_in_background` plus polling monitor fences can reappear in design surfaces without failing structure tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-risk-integration-output.txt: Address the concern above.


### FINDING_4: Design structure harness lost broad wrapper ordering and behavioral coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-architecture-output.txt, dyn-risk-integration-output.txt
- **Severity**: important
- **Concern**: `scripts/test-design-structure.sh` removed or failed to retarget broad pause, sentinel, route, postplan, and wrapper-contract checks. Current checks cover only a small subset, so pause/resume and routing regressions can pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-architecture-output.txt: Address the concern above.
  - From dyn-risk-integration-output.txt: Address the concern above.


### FINDING_5: Degraded Step 0 lacks documented or autonomous both-down handling
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `design-step0-degraded.sh` emits `needs-degraded-decision` for both-tools-down paths without documented non-interactive handling, prompted sentinel writes, or required logging. Autonomous runs can block or re-prompt on resume.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_7: Step 0 route results are not re-emitted or persisted for prompt-side branching
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `design-step0-route.sh` reads route env internally but does not emit or persist the route allowlist. Later SKILL branches can see stale or empty `ISSUE_NUMBER`, `ROUTE`, or related handoff state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_8: Step 6 reports expected preserve-tmpdir states as failure
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `design-step6-cleanup.sh` exits non-zero for expected cleanup-ineligible preserve states. A successful plan write with publish failure can make the completed design look failed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_9: Consecutive-fence lint accepts generic prose as execution boundaries
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-risk-integration-output.txt
- **Severity**: important
- **Concern**: `assert_no_consecutive_executable_script_call_fences` allows broad headings, bold prose, and `Print:` breadcrumbs as boundaries. Consecutive wrapper calls can pass without a real prompt-side decision point.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.
  - From dyn-risk-integration-output.txt: Address the concern above.


