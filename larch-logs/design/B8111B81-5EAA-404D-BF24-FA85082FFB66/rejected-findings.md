### [Plan Review] FINDING_2

### FINDING_2: SKILL.md mid-loop prose still references deleted post-loop resume matrix
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The proposed SKILL rewrite deletes the post-loop branch matrix and adds a `NEXT_ACTION` table, but lines 615 and 660 still tell orchestrators to use the post-loop resume matrix for mid-loop returns. After deletion, mid-loop resume flags lose a stable anchor and can drift back to deleted matrix wording.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the SKILL.md rewrite, replace post-loop resume matrix at 615 and 660 with mid-loop resume sub-table keyed on STEP3_REVIEW_LOOP_STATUS. Cross-link the retained sub-table in section 3 of the rewrite.


### [Plan Review] FINDING_3

### FINDING_3: Mid-loop sub-table header conflicts with NEXT_ACTION-only post-notification routing
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Post-notification bullets (255-260) require exclusive routing via persisted `NEXT_ACTION`, but the mid-loop sub-table header (243) says it is keyed on `STEP3_REVIEW_LOOP_STATUS`, not `NEXT_ACTION`. Line 251 only says status selects resume flags, not that post-notification must never branch on the sub-table first. Dual-authority routing the plan retires can return for mid-loop bail-outs (`mav`, `gate-b`, `postplan-operator`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Scope the sub-table explicitly to launcher flag/round binding after the orchestrator has already branched on `NEXT_ACTION`; add one sentence that post-notification routing never uses this sub-table instead of `NEXT_ACTION`.


### [Plan Review] FINDING_4

### FINDING_4: Terminal normalize early returns omit NEXT_ACTION persist
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan says `normalize_step3_status_main` must merge recomputed `NEXT_ACTION` into `.step3-review-result.env`, but the post-loop flow still calls `_step3_emit_normalize_envelope` then returns 1 after printing `SUMMARY_OUTCOME` for `postplan-failed` and `panel-init-failed` without a named persist step. Hook-blocked `--read-result-env` recovery and file-first post-notification routing can see terminal statuses without `NEXT_ACTION=final-summary:*`, hitting the planned missing-`NEXT_ACTION` routing error.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Before the postplan-failed and panel-init-failed early returns in normalize_step3_status_main, persist recomputed NEXT_ACTION (and normalized status fields) to .step3-review-result.env via the same merge helper used elsewhere; add a pytest that normalize leaves NEXT_ACTION=final-summary:failed-judge-panel in the file when stdout prints SUMMARY_OUTCOME.


### [Plan Review] FINDING_5

### FINDING_5: Terminal degraded_exit zfdp path omits full persist and step-3 sentinel
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Plan lines 92-93 require terminal zfdp to call full `step3_loop_persist_envelope(..., write_terminal=True)` plus `step3_loop_write_completed_step3`, but the `python/plan_review.py` edit section does not name the `degraded_exit` branch at ~2099-2117. Today that branch only emits stdout KVs and returns, so even with in-loop fixes the terminal zero-findings path can lack persisted `NEXT_ACTION=step3b` and `.completed/step-3`, breaking the sentinel double-gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In `### UPDATED: python/plan_review.py`, add an explicit bullet for the `if degraded_exit:` block at ~2099-2117 mirroring the terminal zfdp contract (persist rows, `NEXT_ACTION=step3b`, `write_terminal=True`, `step3_loop_write_completed_step3`).


