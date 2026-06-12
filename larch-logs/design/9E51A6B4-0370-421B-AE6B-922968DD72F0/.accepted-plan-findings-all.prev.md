### FINDING_1: Raw envelope emission can still abort before durable persistence
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements, Codex-dyn-test-mechanism-fit
- **Severity**: important
- **Concern**: Sanitizing only the durable `step3_loop_persist_envelope` write leaves `step3_loop_emit_envelope` exposed. `emit_kv` still receives raw `PLAN_REVIEW_CONTINUE_REASON` and `SCOPE_ANCHOR_FILE` first, so CR/LF values can abort under `set -e` before the result env is written.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Sanitize the same two values before the emit_kv calls in step3_loop_emit_envelope, or have those emits use the sanitized locals used for persistence
  - From Cursor-Innovation: Compute sanitized locals once at the top of step3_loop_emit_envelope and use them for both emit_kv (lines 38-39) and the step3_loop_persist_envelope call; or move sanitization into a shared helper invoked before any emit_kv/write
  - From Codex-Innovation: Sanitize once at the start of step3_loop_emit_envelope, use the sanitized values for emit_kv and persistence, and make the regression test exercise step3_loop_emit_envelope rather than only step3_loop_persist_envelope
  - From Cursor-Pragmatic: Strip CR/LF at the start of step3_loop_emit_envelope (in-place on the two globals or via shared locals) before any emit_kv call and before calling step3_loop_persist_envelope; persist should consume the same sanitized values
  - From Codex-Pragmatic: Sanitize the values before the emit_kv calls in step3_loop_emit_envelope too, then use the same sanitized values for the durable persist path or pass them into step3_loop_persist_envelope
  - From Codex-Requirements: Compute sanitized values before emit_kv and reuse them for both FD3 emission and result-env persistence, and change the regression test to exercise step3_loop_emit_envelope or the full loop path rather than calling only step3_loop_persist_envelope
  - From Codex-dyn-test-mechanism-fit: Sanitize these values before step3_loop_emit_envelope calls emit_kv, and use the same sanitized values for durable persistence; exercise the regression through step3_loop_emit_envelope or the loop subprocess, not only direct step3_loop_persist_envelope


### FINDING_2: Regression test misses the main-agent-vote-required path
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The proposed regression test calls `step3_loop_persist_envelope` with `status=complete` only. It does not exercise the `main-agent-vote-required` failure path after `run_step3_round_body`, the merge block, or the early-exit envelope shape that caused the orchestrator to lose status.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add a harness case that stubs LOOP_STATUS=main-agent-vote-required through run_loop (mirroring lines 117-124) with injected CR/LF in PLAN_REVIEW_CONTINUE_REASON and asserts .step3-review-result.env contains STEP3_REVIEW_LOOP_STATUS=main-agent-vote-required


### FINDING_3: Merge fallback sanitization is not covered
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The proposed test only sets shell variables before calling `step3_loop_persist_envelope` directly. It does not verify sanitization of merged `PLAN_REVIEW_CONTINUE_REASON` values read from an existing `.step3-review-result.env`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Seed a pre-existing .step3-review-result.env with a multiline PLAN_REVIEW_CONTINUE_REASON then invoke persist/envelope and assert the written file is single-line and the write succeeds


### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/review-design-step3-loop.sh:67-135
- **Concern**: [SCOPE-REDUCTION] Plan strips CR/LF from SCOPE_ANCHOR_FILE instead of omitting invalid paths. Scenario: On loop bail-outs validate_scope_anchor_handoff already cleared CR/LF paths in run_step3_round_body (run-step3-review.sh:192-201); stripping can persist a corrupted path such as bad\rpath becoming badpath, contradicting test-run-step3-review.sh:728-734 which expects omission
- **Proposed resolution**: Sanitize only PLAN_REVIEW_CONTINUE_REASON (direct and merge); for SCOPE_ANCHOR_FILE rely on existing validation or omit the KV when the path still contains CR/LF after assignment, do not strip




### FINDING_2: Merge-fallback test preseed is overwritten before persistence
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Cursor-dyn-test-oracle-fidelity, Codex-dyn-test-oracle-fidelity
- **Severity**: important
- **Concern**: The planned merge-fallback regression test seeds `.step3-review-result.env` before `run_loop`, but `run_step3_round_body` rewrites that same file before `step3_loop_persist_envelope` reads it. The seeded CR/LF-bearing `PLAN_REVIEW_CONTINUE_REASON` is lost, so the assertion may fail or pass without exercising the intended merge sanitization path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Change the merge-fallback coverage to call step3_loop_persist_envelope directly against a seeded .step3-review-result.env, or otherwise seed the file after run_step3_round_body writes RESULT_ENV and before the loop envelope persists
  - From Cursor-Innovation: Seed CR only after round-body write is bypassed (symlink write-failure path), call `step3_loop_persist_envelope` directly with a pre-seeded env, or stub round body to leave a merge-source file intact
  - From Cursor-dyn-test-oracle-fidelity: Replace that integration assertion with a direct subshell case: seed .step3-review-result.env with a CR/LF-containing PLAN_REVIEW_CONTINUE_REASON, leave the shell variable empty, call step3_loop_persist_envelope (or step3_loop_emit_envelope) without run_step3_round_body in between, then assert the written file has a sanitized single-line reason or omits the key when stripped empty
  - From Codex-dyn-test-oracle-fidelity: Change the merge sanitizer test to avoid the first-round overwrite, for example source the loop functions and call step3_loop_persist_envelope with a preseeded result env, or resume from a prewritten phase that reaches step3_loop_emit_envelope without running run_step3_round_body first


### FINDING_4: Sanitized-empty merged continue reason can still be persisted
- **Reviewer(s)**: Cursor-dyn-test-oracle-fidelity
- **Severity**: important
- **Concern**: The merge branch checks whether the raw merged value is non-empty before stripping CR/LF. A value containing only CR or LF can pass the pre-check, sanitize to empty, and still append `PLAN_REVIEW_CONTINUE_REASON=`, which contradicts the durable omission contract for sanitized-empty values.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-test-oracle-fidelity: In the merge branch, strip CR/LF into a local, then append only when [[ -n "$sanitized" ]] (mirror line 112 guard semantics)




### FINDING_3: Write-failure test does not reach the write-failure path
- **Reviewer(s)**: Cursor-dyn-test-harness-fidelity
- **Severity**: important
- **Concern**: The planned write-failure test calls `step3_loop_emit_envelope` without its required four arguments. Under `set -e`, that can fail before `phase_driver_write_result_env` runs, so the intended symlink write-failure behavior is not exercised.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-test-harness-fidelity: Use `step3_loop_emit_envelope complete 1 1 1` (or another valid terminal status) with `.step3-review-result.env` symlinked first



