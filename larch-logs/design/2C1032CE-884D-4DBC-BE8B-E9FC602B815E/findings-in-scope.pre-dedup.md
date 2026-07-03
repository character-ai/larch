### FINDING_1:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review_loop.py:527-609
- **Concern**: The plan intentionally leaves the scoped round-rerun timing defect unresolved.. Scenario: On Step 3 re-entry for the same design round, an existing v1 round row makes _append_canonical_round_timing return early and an existing gate-b-apply-round-N.out row makes _gate_b_apply_start_s treat the rerun as duplicate, so the rerun still gets no fresh round window and no second gate-b/apply span.
- **Proposed resolution**: Add the narrow rerun remedy to the plan, such as attempt-specific design round timing plus attempt-specific Gate B output basenames, or split that Important issue item out before landing this narrower PR.



### FINDING_2:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review_loop.py:528-579
- **Concern**: Plan explicitly excludes the scoped rerun fix for Gate B apply timing. Scenario: On Step 3 re-entry or a rerun of the same design round, the existing v1 round row and gate-b-apply-round-N.out row still make the timing helpers return early, so the rerun gets no fresh round window or gate-b/apply span. This leaves the issue's Important finding unresolved.
- **Proposed resolution**: Add the narrow rerun handling requested by the issue: reset or version the design round and gate-b apply timing per attempt on Step 3 re-entry, or split that Important item into a separate tracked issue before landing this narrower PR.



### FINDING_3:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review_loop.py:527-592
- **Concern**: The plan intentionally excludes the binding round-rerun timing concern.. Scenario: Step 3 re-entry for the same design round still hits the existing round-row idempotence and the fixed gate-b-apply-round-N.out duplicate check, so the rerun gets no fresh round window and no second gate-b/apply span.
- **Proposed resolution**: Add one stated rerun remedy to the plan: per-attempt design round rows with attempt-specific Gate B output basenames, or a safe Step 3 re-entry cleanup of prior same-round Gate B timing rows.



