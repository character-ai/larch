# Review Round 1

- Mode: `diff`
- 11 accepted, 5 rejected (4 neutral)

## Accepted Findings

### FINDING_1: `run_plan_review_round` is an incomplete single-round stub
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-step3-parity-output.txt
- **Severity**: blocking
- **Concern**: `run_plan_review_round` (`python/plan_review.py:713-767`) runs `panel-dispatch` then immediately emits `LOOP_STATUS=complete` with `ACCEPTED_COUNT=0` and `TALLY_PLAN_REVIEW_STATUS=ok`. It never runs collector STATUS gating, `agent collect-results`, aggregation, `plan-review voter-dispatch`, tally, or MAV. When `RUN_STEP3_PLAN_REVIEW_LOOP_SH` is unset (production default in `run_step3_review`), `/design` Step 3 completes every round without reviewing the plan, applying findings, or routing continuation/Gate B correctly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.
  - From dyn-step3-parity-output.txt: Port the full single-round body from embedded `plan-review-loop.sh` into `run_plan_review_round()`: collector STATUS gating, `COLLECT_FAILURE_COUNT`, voter dispatch, tally, degraded-panel handling, and `main-agent-vote-required` / `tally-error` / `degraded-empty-collector` envelopes before marking a round complete.


### FINDING_10: Retired bash loop bodies and dual authority remain on disk
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: blocking
- **Concern**: Retired loop bodies (`review-design-step3-loop.sh`, `plan-review-continuation.sh`, `lib-step3-prelaunch-failure.sh`) remain on disk; `migrated-scripts.tsv` lacks `#4632` rows; `design-step3-review.sh` still sources `lib-step3-prelaunch-failure.sh` instead of `plan-review prelaunch-failure` CLI. `make lint-retired-scripts` and acceptance criteria cannot pass; dual bash/Python authority persists while the native port is incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_11: `test-review-design-step3-loop` Makefile target uses obsolete pytest selectors
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-step3-parity-output.txt
- **Severity**: important
- **Concern**: `Makefile:519-520` still filters `embedded_review or embedded_run_step3_review or embedded_waterfall or run_legacy`, but embedded-asset tests were removed from `python/test_plan_review.py`. `pytest --collect-only` with that `-k` likely exits 5 and breaks `test-harnesses-16`; CI can pass without exercising the native Python Step 3 implementation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-step3-parity-output.txt: Retarget the `-k` selector to the native tests that remain (`cap_reached`, `tally_error_rollback`, `plan_review_continuation`, prune-empty continuation, etc.), per the implementation plan.


### FINDING_2: `dispatch_voters` only launches voters when both externals are down
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-step3-parity-output.txt
- **Severity**: blocking
- **Concern**: `dispatch_voters` (`python/plan_review_panel.py:238-273`) launches a Claude voter only when both Codex and Cursor are unavailable. When either external is present, all three voter slots remain `failed`, `DISPATCH_OK=false`, and the function exits non-zero. Normal environments with Codex or Cursor available cannot complete voting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.
  - From dyn-step3-parity-output.txt: Port the legacy voter dispatch path: launch Codex/Cursor/Claude per availability, parse-rate retry, degraded-panel accounting, and `VOTER_PATHS_FILE` emission; keep Claude-only fallback only for the both-down case.


### FINDING_3: `STATIC_SLOTS` use wrong canonical slot identifiers and prompts
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-step3-parity-output.txt
- **Severity**: important
- **Concern**: `STATIC_SLOTS` (`python/plan_review_panel.py:22-31`) use `cursor-plan-correctness`, `cursor-plan-integration`, `cursor-plan-architecture`, `cursor-plan-tests`, etc., instead of the canonical Arch / Innovation / Pragmatic / Requirements diagonal from `plan-review.md`. Slots also get generic inline prompts instead of `python/cli.py render plan-review --archetype ...`, and there is no round-1 vs round-2+ Codex replacement gating. Reviewer prune ledger, tally scoreboard, and status tables desync from production slot labels and historical contracts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-step3-parity-output.txt: Restore the canonical static slot table and round-gated Codex replacement rows from the legacy dispatcher; generate prompts through `render plan-review` with the correct archetype/vendor pairs.


### FINDING_4: Registered `plan-review` CLI verbs are no-op stubs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-step3-parity-output.txt
- **Severity**: blocking
- **Concern**: Registered verbs including `step35-settle`, `step3-mav`, `step3b-entry`, `step3b-sanitize`, and `step3b-tail` (`python/plan_review.py:1069-1255`) are stubs that return success without Gate B settle rc mapping, MAV vote/apply, diagram classification/sanitization, Gate C preview, `SKIP_APPROVE_REQUESTED_GATEC` output, or `.completed/step-4` ordering. Wrappers or direct CLI callers get exit 0 while required side effects are skipped. `step3-entry` delegates to `step3_state` rather than scope-anchor assembly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.
  - From dyn-step3-parity-output.txt: Port the bodies from `design-step35-settle.sh`, `design-step3-mav.sh`, `design-step3b-entry.sh`, `design-step3b-sanitize.sh`, and `design-step3b-tail.sh` into these functions before shrinking wrappers further.


### FINDING_5: `step35_settle` always returns 0 instead of preserving required rc mapping
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `step35_settle` (`python/plan_review.py:1069-1071`) always returns 0. A postplan rc 10 that should route operator-required settlement is reported as success instead of the legacy `design-step35-settle.sh` rc matrix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_6: `run_step3_review` missing multi-phase loop and postplan operator routing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-step3-parity-output.txt
- **Severity**: important
- **Concern**: `run_step3_review` (`python/plan_review.py:947-1034`) does not implement the multi-phase state machine from `review-design-step3-loop.sh`. It runs one round body, optional apply, then continuation recursion. Missing: reading `.step3-round-N.phase`, `awaiting-revise` / `awaiting-post-apply` / `awaiting-postplan-operator`, `RUN_STEP3_POSTPLAN_EMIT_SH` / `design postplan-emit`, `postplan-operator-required`, `postplan-failed`, and per-round approval resume via `.gate-b-per-round-approval-round-N.env`. Wrapper resume artifacts from `design-step3-review.sh` are ignored, breaking Gate B / MAV / postplan resume after pause.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-step3-parity-output.txt: Port the bash phase machine into `run_step3_review()` (or call into retained loop logic until fully native): honor phase files on entry, run post-apply postplan emit with rc `10/11/12/13` routing, and handle `postplan-operator-continue` sentinels before continuation.


### FINDING_7: `zero-findings-degraded-panel` emit/persist contract broken
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-step3-parity-output.txt
- **Severity**: important
- **Concern**: When `LOOP_STATUS=zero-findings-degraded-panel`, the native path still calls `step3_loop_emit_envelope(..., "complete", ...)`, which always sets `STEP3_REVIEW_LOOP_STATUS` (`python/plan_review.py:403-426`, `1008-1030`). Legacy bash leaves `STEP3_REVIEW_LOOP_STATUS` unset for this path so wrapper continuation and ballot-items-lost handling key off `LOOP_STATUS` alone. Additionally, pruned-empty state is not persisted to `.step3-review-result.env` before continuation reads it; rounds 3–4 with all slots pruned can complete immediately instead of continuing toward round 5.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.
  - From dyn-step3-parity-output.txt: Add a dedicated emit/persist path for `zero-findings-degraded-panel` that writes `LOOP_STATUS=zero-findings-degraded-panel` to `.step3-review-result.env` but omits `STEP3_REVIEW_LOOP_STATUS`, matching bash and `plan_review_continuation()` (`887-889`).


### FINDING_8: `review-round-count.txt` not rolled back on tally-error or degraded-empty-collector
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `run_plan_review_round` persists `review-round-count.txt` at round start (`python/plan_review.py:725`) without native-path rollback on `tally-error` or `degraded-empty-collector`. After a failed tally in production mode the cap counter advances ahead of durable launched rounds, skewing resume and cap guards versus the bash contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_9: Failure paths write both `step-3` and `step-3.5` completion sentinels
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Failure paths in `run_step3_review` (`python/plan_review.py:1000-1003`, `1032-1033`) call `step3_loop_write_completed_step3`, which can create `.completed/step-3.5` alongside `.completed/step-3`. A `panel-failed` round writing `step-3.5` can skip Gate B or break repair routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


