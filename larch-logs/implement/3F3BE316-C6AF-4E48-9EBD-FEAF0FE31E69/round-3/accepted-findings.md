### FINDING_1: Empty bail reason emits multiline/incorrect KV
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `safe_bail_reason_value()` falls through for empty bail reasons, producing spurious multiline output or `redacted` values that break the single-line KV contract and obscure empty bail intent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_10: Harness does not cover in-memory versus disk clear ordering
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Case 19 checks disk temp/mv behavior but not the planned ordering that keeps in-memory `STALL_TRACKING=true` until disk false has been persisted and read back.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_11: Dry-run coverage misses some reporting and issue surfaces
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Dry-run automation only partially covers output paths, leaving `bug-comment`, `issue-input-file`, and orchestrator `/larch:issue` behavior insufficiently verified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_18: Terminal-failure comment target is underspecified
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: When `stall-recovery-issue.env` is missing, exhaustion comments may be posted to the consumer tracking issue instead of the filed larch bug issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_19: Success path may lack ship-pr-state seeding
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Successful recovery can skip `restore-finalize-state` and fail to create `ship-pr-state.sh`, leaving stale finalize state to drive the wrong DONE versus STALLED branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_2: Same-cause-repeat can skip alternate retry
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Stall recovery prose routes `RESUME_HINT=none` directly terminal before the same-cause-repeat alternate-strategy branch, so repeated failures may skip the intended one alternate retry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_21: Classifier evidence can include stale full-state data
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Feeding full state or session files into classifier evidence allows stale fields such as `NOTE=` lines to misclassify an otherwise clean failure-detail log.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_22: Plan and harness disagree on absent ship-pr-state classification
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan case 8 expects unrecoverable behavior when `ship-pr-state.sh` is absent, but the harness expects transient-infra through session-env, leaving the acceptance text and implemented path misaligned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_23: Deny-list coverage omits chat-print surface
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Deny-list case 13 scans only three composed outputs while the plan lists four surfaces, leaving the consumer chat-print path unverified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_24: Plan files section contradicts bail bullet edits
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The plan says bail-path bullets were not modified, but rebase bail bullets were reworded for Step 18a/18b.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: Successful recovery dispatch may not clear stall tracking
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Recovery dispatch success lacks an explicit transition to the step that clears `STALL_TRACKING`, so teardown can still treat a merged recovery as stalled.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_5: Broad auth matching misclassifies permanent auth failures as transient
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The transient-infra classifier matches broad auth-failure wording, causing permanent auth misconfiguration to consume retry budget instead of terminaling or using a non-retryable class.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_6: Retry caps are prose-only
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Per-class retry caps are documented but not enforced by helper logic or covered by automation, so orchestrator regressions could exceed retry limits unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_8: 64 KiB failure-detail validation coverage is missing or overstated
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The 64 KiB failure-detail-log limit is implemented and claimed in security documentation, but no harness case verifies the behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_9: RESUME_HINT=none assertions missing for terminal plan cases
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Contract-failure and unrecoverable bail test cases assert failure class but not `RESUME_HINT=none`, leaving redispatch regressions undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


