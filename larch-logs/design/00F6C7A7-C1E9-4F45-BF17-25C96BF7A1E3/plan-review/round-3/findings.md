### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-stall-recovery-report.sh:157-158
- **Concern**: Classify bail split breaks existing case 7b. Scenario: The plan binds classify_from_evidence to state/session bail only (excluding --bail-reason), but case 7b classifies transient-infra from argv-only bail with no matching state/session evidence; after the split FAILURE_CLASS becomes unrecoverable and the harness fails despite Testing strategy requiring existing cases stay green
- **Proposed resolution**: Update Testing strategy: revise or remove case 7b (e.g. move network-timeout evidence into ship-pr-state.sh BAIL_REASON or a failure-detail log) and document that --bail-reason is report-only, not classification evidence

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/stall-recovery-report.sh:624-661
- **Concern**: Planned classify_bail/report_bail split drops the only classifier evidence for in-memory Step-2 hard-bail reasons. Scenario: When Step 2 returns STATUS=bailed REASON=wrapper-validation-failure before ship-pr-state.sh or session-env.sh carries that reason, Step 18a will pass the coalesced --bail-reason but the proposed classify_bail excludes it. classify_from_evidence then sees no wrapper-validation evidence, emits unrecoverable, and stall-recovery.md:19 skips first-detection issue filing. The existing harness case at skills/implement/scripts/test-stall-recovery-report.sh:156-159 also conflicts with making --bail-reason report-only.
- **Proposed resolution**: Keep the split narrow: let allowlisted Step-2 dispatch tokens from bail_arg participate in failure_class classification while still excluding the argv overlay from the signature hash if that is the stability goal, or persist the sanitized Step-2 reason into an existing durable classifier input before Step 18a. Update the existing bail-reason-only harness case accordingly.

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge, Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-stall-recovery-report.sh:155-158
- **Concern**: Plan omits harness update for case 7b after report-only --bail-reason split. Scenario: After cmd_classify stops feeding --bail-reason into classify_from_evidence, case 7b (empty state/session bail plus --bail-reason "network timeout while posting issue") classifies unrecoverable instead of transient-infra and test-stall-recovery-report.sh fails despite the plan calling the harness green
- **Proposed resolution**: Revise the Testing strategy / test-stall-recovery-report.sh section to rewrite or drop case 7b and, if transient-infra-from-bail coverage is still wanted, assert it via state/session BAIL_REASON or validated failure-detail evidence instead of argv-only bail

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/stall-recovery-report.sh:622-661; skills/implement/scripts/test-stall-recovery-report.sh:155-158
- **Concern**: Plan makes --bail-reason report-only but existing harness treats argv bail as classifier evidence. Scenario: Case 7b currently expects classify --bail-reason "network timeout while posting issue" to produce transient-infra; excluding bail_arg from classify_from_evidence makes it unrecoverable, so the plan violates its no classifier-behavior change claim and breaks an existing test it says to keep green
- **Proposed resolution**: Revise the split so existing --bail-reason classification behavior is preserved, or explicitly update the contract/tests and narrow the Step-18a handoff to a separate report-only path for FINAL_BAIL_REASON rather than changing --bail-reason globally

### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/stall-recovery-report.sh:655-661
- **Concern**: Proposed classify/report bail split drops argv bail from routing even when Step 2 only mirrors the dispatcher reason in memory. Scenario: A STATUS=bailed REASON=wrapper-validation-failure path with no ship-pr-state/session bail would pass the reason only via --bail-reason; after the split it can classify as unrecoverable instead of dispatch-failure, skipping first-detection filing/retry despite the plan promising behavior-stable routing
- **Proposed resolution**: Keep bail_arg in the classification input for the existing allowlisted dispatch bail tokens, or seed/read the Step-2 bail as state/session evidence before excluding argv from classify_from_evidence

### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-stall-recovery-report.sh:157-158
- **Concern**: Plan splits --bail-reason out of classify_from_evidence but omits case7b harness update. Scenario: Existing case7b asserts argv-only --bail-reason drives transient-infra classification; after the proposed split classify_bail excludes argv so the case fails while the plan still says keep existing classify cases green
- **Proposed resolution**: Add an explicit test-plan step to rewrite or drop case7b (e.g. move the transient-infra trigger into session/state evidence for classification and add a separate argv-only report-bail assertion)

### FINDING_7:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-stall-recovery-report.sh:155-158
- **Concern**: Plan says --bail-reason argv becomes report-only, but the existing harness asserts bail-reason-only transient evidence still classifies as transient-infra. That is a classifier behavior change despite the plan's report-only/no classifier-behavior-change goal.. Scenario: The proposed split would make the existing case classify from state/session only, so this test fails and real stalls whose only transient clue is --bail-reason can route as unrecoverable.
- **Proposed resolution**: Revise the plan to preserve --bail-reason as classification evidence while excluding the argv overlay only from BAIL_REASON reporting/signature where needed, or explicitly update the existing test/docs and state this intentional routing change.

### FINDING_8:
- **Reviewer(s)**: Cursor-dyn-skill-site-coverage
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-stall-recovery-report.sh:157-158
- **Concern**: Plan classify_bail/report_bail split drops --bail-reason from classify_from_evidence but omits harness update for case 7b. Scenario: Case 7b classifies argv-only --bail-reason network timeout while posting issue as transient-infra via bail string in lowered evidence; after split classify_bail is empty so FAILURE_CLASS becomes unrecoverable and test-stall-recovery-report.sh fails
- **Proposed resolution**: Add to test-stall-recovery-report.sh section: revise or remove case 7b (e.g. assert unrecoverable or move network markers into state/evidence) and note the intentional argv-routing regression in the harness doc

### FINDING_9:
- **Reviewer(s)**: Codex-dyn-skill-site-coverage
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-stall-recovery-report.sh:155-158; skills/implement/scripts/stall-recovery-report.sh:622-661
- **Concern**: The proposed classify_bail/report_bail split conflicts with an existing regression test because --bail-reason is currently folded into bail_reason, passed to classify_from_evidence, and hashed in the signature.. Scenario: After the split, case7b's --bail-reason "network timeout while posting issue" no longer classifies as transient-infra, so the plan's "keep existing classify cases green" claim is false unless this test is changed.
- **Proposed resolution**: Update case7b to the new report-only contract, or narrow the split if bail-reason-only routing must remain supported.

### FINDING_10:
- **Reviewer(s)**: Codex-dyn-skill-site-coverage
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:646
- **Concern**: The Step 2.4 recovery sub-branch also assigns FINAL_BAIL_REASON=recovery-out-of-scope, but the plan's concrete mirror pins cover only §2.1.5 and §2.2 sites.. Scenario: An implementer following the named touch sites can leave this Step-2 FINAL_BAIL_REASON path without an IMPLEMENT_BAIL_REASON mirror, so Step 18a may render Bail reason as none rather than redacted for that fail-closed path.
- **Proposed resolution**: Add the recovery-out-of-scope assignment to the SKILL.md mirror pass, or explicitly state that this path is excluded because it does not route through the Step 12d stall handoff.
