### FINDING_10: issue-input-file accepts body files outside the implement tmpdir
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `--body-file` accepts any readable path, so a mistaken file outside `IMPLEMENT_TMPDIR` can be concatenated into public `/larch:issue` input.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_13: Terminal-failure path leaves stall state memory-only
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Terminal failures can keep `STALL_TRACKING=true` only in memory, while Step 18b Branch A requires on-disk state, so a Step 0/pre-ship recovery may never rename the tracking issue to `[STALLED]`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_14: same-cause-repeat still produces step-specific resume hints
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `same-cause-repeat` can still return a step-specific `RESUME_HINT`, causing dispatch to rerun the same path instead of taking the documented alternate strategy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_16: Success-path read-back omits required --file argument
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `stall-recovery.md` success-path read-back calls `read-session-env-key.sh` without required `--file`, so literal orchestration can fail and leave `STALL_TRACKING` true.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_17: Plan acceptance case 8 conflicts with intended session-env behavior
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan acceptance still expects unrecoverable when `ship-pr-state` is absent, while the harness expects transient-infra with session-env stall, creating a stale checklist conflict.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_18: Harness contract documentation omits expanded case mapping
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `test-stall-recovery-report.md` does not document per-case fixtures and outputs for expanded cases, making it harder to trace harness coverage to requirements.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_19: Case 9 does not assert distinct validation errors
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Harness case 9 can allow distinct invalid `--failure-detail-log` rejections to collapse without test signal because stderr patterns are not asserted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Transient-infra classification can preempt test and lint failures
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Broad transient-infra matching over merged state/session evidence can classify review-step test, lint, auth, timeout, or stale session content as transient infrastructure and redispatch the wrong recovery path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_3: Memory-only stall state is ignored when persistence files are absent
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: When both state files are missing, classification forces unrecoverable even if in-memory `STALL_TRACKING=true` and the detail log or bail reason contains recoverable evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_4: Transient-infra regex misses documented network errors
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The transient-infra regex requires literal `network/auth issue`, so broader documented network-error evidence can miss transient-infra classification and fall through to unrecoverable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_7: Title-prefix lifecycle references are inconsistent
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: SKILL/rebase guidance still points to a missing or ambiguous Title-prefix lifecycle/Step 18 section, leaving operators with conflicting guidance about when `[STALLED]` rename is decided.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_8: Dispatch classifier tests omit RESUME_HINT assertions
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Cases 2-4 assert `FAILURE_CLASS` but not `RESUME_HINT`, so `resume_hint_for()` could regress to `none` for dispatch paths while classifier tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_9: Classification KV output can expose raw stall metadata
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `classify` emits raw `STALL_STEP`, `PHASE`, and `BAIL_REASON` in KV output while only bug-body/comment surfaces are sanitized, so copied classification output can leak paths or tool output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


