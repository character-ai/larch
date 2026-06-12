### FINDING_1: Continuation branch over-broad on degraded + zero accepted
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The proposed continuation branch keys only on `DEGRADED_PANEL != 0` and `ACCEPTED_COUNT == 0`. Voter-dispatch or dispatch-degraded rounds with zero accepted and `TALLY != ok` (e.g. `skipped-empty-findings`, `degraded-empty-collector`) can still have `DEGRADED_PANEL=1`; that branch would auto-continue with `ballot-items-lost` and burn review rounds until cap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Gate continuation on an explicit ballot-items-lost signal (read `REASON=ballot-items-lost` from `.step3-review-result.env`), not bare degraded+zero-accepted




### FINDING_1: Step 3 driver drops REASON before continuation
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: `plan-review-loop.sh` can emit `REASON=ballot-items-lost`, and `plan-review-continuation.sh` reads `REASON` from `.step3-review-result.env`, but `run-step3-review.sh` does not persist `REASON` into that env. The live Step 3 loop may still stop as `small-clean` instead of continuing on a lost-ballot round.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `REASON=${REASON:-}` to `emit_kv` and `result_env_kvs` in `run-step3-review.sh`; extend `run-step3-review.md` normalized-key list. Optionally mirror in `review-design-step3-loop.sh` `step3_loop_persist_envelope` so later envelope writes do not drop it.
  - From Codex-Arch: Add run-step3-review.sh to the plan. Persist REASON into .step3-review-result.env, or make continuation read the inner .step3-plan-review-result.env. Update the regression to cover this propagation path.
  - From Cursor-Innovation: Add REASON to result_env_kvs in run-step3-review.sh (and merge it in review-design-step3-loop.sh step3_loop_persist_envelope when absent) update run-step3-review.md and add an integration assertion in test-run-step3-review.sh
  - From Codex-Innovation: Add run-step3-review.sh to the plan: relay REASON from stdout and inner env, emit REASON, persist REASON in result_env_kvs, and cover the driver handoff in the continuation regression
  - From Cursor-Pragmatic: Add skills/design/scripts/run-step3-review.sh to the plan: include REASON=${REASON:-} in result_env_kvs and emit_kv stdout; update run-step3-review.md if present
  - From Codex-Pragmatic: Add run-step3-review.sh to the plan. Initialize REASON, relay it from loop stdout and .step3-plan-review-result.env, emit it, persist it in .step3-review-result.env, and cover the relay in the existing Step 3 continuation regression.
  - From Codex-Requirements: Add skills/design/scripts/run-step3-review.sh to the plan. Relay REASON into normalized stdout and result_env_kvs. Add a focused run-step3-review integration test that stubs plan-review-loop with REASON=ballot-items-lost and verifies .step3-review-result.env carries it before continuation.


### FINDING_2: Invalid mechanical_churn handoff is underspecified
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The invalid `mechanical_churn` contract between `lib-plan-optional-trailers.awk` and `check-plan-size.sh` is not pinned tightly enough. An invalid line such as `mechanical_churn: 35` can break the upward scan, leave `has_mech=0`, and still let `check-plan-size.sh` see only a false parse value unless an explicit invalid marker or validation path is required.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Specify awk contract: on any ^mechanical_churn: line that is not exactly true/false, emit invalid-mechanical-churn stderr, continue scanning, and emit a non-boolean token on parse line 4 (or add an explicit invalid flag); check-plan-size must reject any mechanical_churn value other than true/false before size gates




### FINDING_1: Use LOOP_REASON for ballot-items-lost loop state
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-dyn-signal-chain
- **Severity**: important
- **Concern**: The plan names `REASON=ballot-items-lost`, but `plan-review-loop.sh` uses `LOOP_REASON` internally and emits terminal KVs from `LOOP_REASON`. Setting only `REASON` may leave stdout, step3 env, and round summaries without the ballot-items-lost reason.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Cursor-Pragmatic: Set LOOP_REASON=ballot-items-lost in the detector and guard the ~1888-1905 terminal branch with [[ "${LOOP_REASON:-}" == "ballot-items-lost" ]] || LOOP_REASON=zero-findings-degraded-panel
  - From Cursor-dyn-signal-chain: State LOOP_REASON=ballot-items-lost in plan-review-loop.sh; keep KV name REASON via existing emit_loop_kvs/write_step3_result_env wiring


### FINDING_3: Specify invalid mechanical_churn parse handoff
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The invalid `mechanical_churn` behavior is underspecified for upward-scan block assembly. A non-boolean `mechanical_churn:` line may still be omitted from parsed metadata, causing parse mode to emit `false` instead of `invalid:<value>`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: check-plan-size.sh can still treat mechanical_churn: 35 as false even after stderr is added In the awk section, explicitly require recording any mechanical_churn: line in the final optional block (e.g., include it in block[] or a side variable) so parse mode line 4 is invalid:<value> and has_key treats the key as present; add a test-trailer-awk or test-check-plan-size assertion that line 4 is not false when only mechanical_churn: 35 precedes diff_lines:



