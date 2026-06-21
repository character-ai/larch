## Decision 1: Extraction boundary
- **Question**: How much of design-step3-review.sh's post-loop back half should move into the new cli.py plan-review verb?
- **Resolution**: Full back half. Move result-env read, LOOP_STATUS<->STEP3_REVIEW_LOOP_STATUS normalization, terminal-status synthesis, KV envelope emission, and escalation-evidence recording into the new verb. The wrapper keeps only argv parse, monitor/job-control setup, background launch, EXIT-trap sentinels, and verb calls.
- **Source**: user

## Decision 2: --read-result-env recovery path
- **Question**: Where should the existing --read-result-env recovery branch live after the refactor?
- **Resolution**: Fold into the verb. Route --read-result-env through the new Python verb (a read mode) so all envelope parsing lives in one place. The wrapper's --read-result-env branch becomes a thin delegation to the verb, preserving the exact stdout KV grammar.
- **Source**: user

## Decision 3: Behavior parity (hard constraint)
- **Question**: What contracts must stay byte-identical across the refactor?
- **Resolution**: Preserve exactly: the `.completed/step-3`, `.completed/step-3-terminal`, and `.step3-terminal-persisted-this-run` sentinel contracts; the post-loop stdout KV envelope grammar (STEP3_REVIEW_LOOP_STATUS, LOOP_STATUS, POSTPLAN_RC, ROUNDS_COMPLETED, etc.); the `--read-result-env` stdout grammar (READ_RESULT_ENV_STATUS + 7 KV lines); and terminal exit codes (postplan-failed / panel-init-failed -> exit 1 with SUMMARY_OUTCOME lines). This is a behavior-preserving refactor, not a behavior change.
- **Source**: codebase (acceptance criteria + design-step3-review.sh)

## Decision 4: Keep the process-group launcher in Bash
- **Question**: Should any job-control logic move to Python?
- **Resolution**: No. The Bash wrapper retains `set -m` monitor-mode setup, the background `plan-review run --mode loop` launch, `kill -- -$pid` process-group teardown, and the EXIT-trap sentinel guarantees. These need shell job control and stay in Bash. This is a partial thinning, not a full migration; do not remove the launcher.
- **Source**: codebase (issue Note + design-step3-review.sh)

## Decision 5: No scope creep
- **Question**: Any related changes the user does NOT want?
- **Resolution**: Out of scope: changing plan-review loop behavior, altering the escalation-evidence semantics, touching argv/resume-state validation, or reworking the EXIT-trap sentinel guarantee logic. Only the pure post-loop logic and the --read-result-env read move to Python; everything else stays put.
- **Source**: codebase
