# Review Round 4

- Mode: `diff`
- 14 accepted, 7 rejected (5 neutral)

## Accepted Findings

### FINDING_1: Step 2a.3 collector cannot discover launched sketch outputs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The Step 2a.3 collector has no reliable launched-path source. SKILL fences pass only `--mode`, `--mode` is ignored, and no launch path writes `sketch-launched-paths.txt`. HARD runs can abort with `zero-launched-slots-hard` after successful sketch launches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_10: Step 2b validation failure metadata is not emitted
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The Step 2b postplan rc 10 path reads validator metadata but does not emit allowlisted `VALIDATE_*` KVs. Failure handling can lose defect counts, status, and log path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_11: Step 5b can skip issue filing without annotation recovery
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `skip-already-filed-sentinel` can mark Step 5b complete after issue filing but before annotation, leaving accepted OOS blocks unannotated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_14: Step 3 handoff tests duplicate live wrapper logic
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Most Step 3 handoff tests still exercise duplicated `apply_step3_handoff` logic instead of `design-step3-review.sh`. CI can pass on stale parser behavior while live Step 3 breaks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_15: Plan-listed behavioral checks have no executing tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Several planned behavioral paths lack executable harness coverage, including parse-before-setup, missing initial env, rc=3 publish fallback, `PUBLISH_OK=false` cleanup skip, and Gate B skip when Step 3.5 exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_16: Pause and folded-sentinel ordering coverage is too narrow
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-architecture-output.txt, dyn-risk-integration-output.txt
- **Severity**: important
- **Concern**: Wrapper ordering checks cover only a small subset of the planned pause-before-work and folded-sentinel contracts. Many direct and internal wrappers can reorder pause checks or sentinels without failing `test-design-structure.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-architecture-output.txt, dyn-risk-integration-output.txt: Address the concern above.


### FINDING_19: Step 0 decomposition defeats the planned wrapper shape
- **Reviewer(s)**: codex-specialist-testing-output.txt, dyn-architecture-output.txt
- **Severity**: important
- **Concern**: Step 0 remains split across consecutive SKILL fences instead of one phase-aware wrapper. The harness whitelists ordinary headings as boundaries, which weakens D3 turn-reduction verification and omits planned resume phases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt, dyn-architecture-output.txt: Address the concern above.


### FINDING_2: Step 3 entry mutates direct-review state before pause-check
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `design-step3-entry-state.sh` rewrites direct-review-entry state before honoring pause. A pause requested during Step 3 entry LLM work can resume at the wrong phase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_20: Step 0 route and init wrappers lack pause-checks
- **Reviewer(s)**: dyn-architecture-output.txt
- **Severity**: important
- **Concern**: `design-step0-route.sh` and `design-step0-init.sh` do not call `design-pause-save.sh` before route/init side effects. Pause requests during routing or init are delayed until later steps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-architecture-output.txt: Address the concern above.


### FINDING_22: SKILL.md does not consume STEP0_STATUS
- **Reviewer(s)**: dyn-architecture-output.txt
- **Severity**: important
- **Concern**: The degraded wrapper emits `STEP0_STATUS`, but SKILL prose does not bind or branch on it. Wrapper stdout and prompt-side orchestration can drift for degraded decisions, verbal issue flow, and resume continuations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-architecture-output.txt: Address the concern above.


### FINDING_3: Removed route pause and cancel-route integration coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-risk-integration-output.txt
- **Severity**: important
- **Concern**: The rewritten structure harness dropped integration fixtures for pause-load routing, cancel-route KV-only stdout, resume routing, backward re-entry, and related acceptance behavior without equivalent wrapper-level replacements.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-risk-integration-output.txt: Address the concern above.


### FINDING_6: Step 0 route state is lost across split wrappers
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Step 0 route/init wrappers do not reliably persist or refresh resolved issue, title, repo, route flags, or brainstorm prefix. Normal issue runs and verbal issue creation can proceed with empty or stale route state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_7: Combined wrappers do not stop after child pause-save exits
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Combined parent wrappers call child wrappers sequentially. If a child handles a pause and exits, the parent can continue into later work, such as Step 3 preview after Step 3 state pause-save.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_8: Degraded-tools gate misclassifies interaction mode
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-architecture-output.txt
- **Severity**: important
- **Concern**: `design-step0-degraded.sh` uses TTY checks instead of an explicit interactive/autonomous signal. Interactive Claude Bash runs can auto-proceed without the Continue/Abort prompt, while autonomous runs with malformed `BOTH_DOWN` can block. The wrapper also lacks a clear Continue resume path and can write the prompted sentinel at the wrong time.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-architecture-output.txt: Address the concern above.


