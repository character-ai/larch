### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:245-248
- **Concern**: Mid-loop resume sub-table lists main-agent-vote-required twice with conflicting routes. Scenario: One bullet routes main-agent-vote-required through the MAV post wrapper; the next groups the same status with main-agent-apply-required and per-round-approval-required for Gate B apply. An implementer can send vote-required bail-outs into Gate B instead of the MAV block, breaking the existing vote/re-tally path.
- **Proposed resolution**: Keep a single main-agent-vote-required row for MAV post resume only. Limit the Gate B apply row to main-agent-apply-required and per-round-approval-required. Keep per-round-approval-required findings-file as a sub-bullet under Gate B only.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:615,660
- **Concern**: Proposed SKILL rewrite does not repoint mid-loop resume prose that still says post-loop resume matrix. Scenario: The plan deletes the post-loop branch matrix and adds a NEXT_ACTION table, but lines 615 and 660 still tell orchestrators to use the post-loop resume matrix for mid-loop returns. After deletion, mid-loop resume flags lose a stable anchor and can drift back to deleted matrix wording.
- **Proposed resolution**: In the SKILL.md rewrite, replace post-loop resume matrix at 615 and 660 with mid-loop resume sub-table keyed on STEP3_REVIEW_LOOP_STATUS. Cross-link the retained sub-table in section 3 of the rewrite.



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:245-246
- **Concern**: Mid-loop resume sub-table groups main-agent-vote-required with Gate B apply. Scenario: The proposed SKILL.md bullet lists main-agent-vote-required twice: first as MAV post resume, then again with main-agent-apply-required and per-round-approval-required as Gate B apply via awaiting-continuation. Post-loop vote-required maps to NEXT_ACTION=mav, not gate-b. An implementer can route MAV bail-outs through Gate B apply/resume flags.
- **Proposed resolution**: Split the bullets: keep main-agent-vote-required only on the MAV post resume line; limit the Gate B apply bullet to main-agent-apply-required and per-round-approval-required only.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/plan_review.py:613-623
- **Concern**: Terminal normalize paths still lack an explicit NEXT_ACTION file persist before early return. Scenario: The plan says normalize_step3_status_main must merge recomputed NEXT_ACTION into .step3-review-result.env, but the post-loop flow still calls _step3_emit_normalize_envelope then returns 1 after printing SUMMARY_OUTCOME for postplan-failed and panel-init-failed without a named persist step. Hook-blocked --read-result-env recovery and file-first post-notification routing can see terminal statuses without NEXT_ACTION=final-summary:*, hitting the planned missing-NEXT_ACTION routing error.
- **Proposed resolution**: Before the postplan-failed and panel-init-failed early returns in normalize_step3_status_main, persist recomputed NEXT_ACTION (and normalized status fields) to .step3-review-result.env via the same merge helper used elsewhere; add a pytest that normalize leaves NEXT_ACTION=final-summary:failed-judge-panel in the file when stdout prints SUMMARY_OUTCOME.



### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:245-246
- **Concern**: Mid-loop resume sub-table lists `main-agent-vote-required` under Gate B apply. Scenario: Step 2b SKILL rewrite bullet 246 groups `main-agent-vote-required` with `main-agent-apply-required` / `per-round-approval-required` and Gate B shared post-apply step 10, but bullet 245 already routes `main-agent-vote-required` to the MAV post wrapper. Implementers can launch Gate B apply/resume fences for a MAV bail-out instead of `design-step3-mav.sh`, skipping vote/re-tally and breaking mid-loop recovery.
- **Proposed resolution**: Split bullets: keep `main-agent-vote-required` only on the MAV post-wrapper row; limit the Gate B apply row to `main-agent-apply-required` and `per-round-approval-required` with the existing resume flags.



### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:243-251
- **Concern**: Mid-loop sub-table header conflicts with post-notification `NEXT_ACTION`-only routing. Scenario: Post-notification bullets (255-260) require exclusive routing via persisted `NEXT_ACTION`, but the mid-loop sub-table header (243) says it is keyed on `STEP3_REVIEW_LOOP_STATUS`, not `NEXT_ACTION`. Line 251 only says status selects resume flags, not that post-notification must never branch on the sub-table first. Dual-authority routing the plan retires can return for mid-loop bail-outs (`mav`, `gate-b`, `postplan-operator`).
- **Proposed resolution**: Scope the sub-table explicitly to launcher flag/round binding after the orchestrator has already branched on `NEXT_ACTION`; add one sentence that post-notification routing never uses this sub-table instead of `NEXT_ACTION`.



### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/plan_review.py:2099-2117
- **Concern**: Terminal `degraded_exit` zfdp path still omits full persist and `.completed/step-3`. Scenario: Plan lines 92-93 require terminal zfdp to call full `step3_loop_persist_envelope(..., write_terminal=True)` plus `step3_loop_write_completed_step3`, but the `python/plan_review.py` edit section does not name the `degraded_exit` branch at ~2099-2117. Today that branch only emits stdout KVs and returns, so even with in-loop fixes the terminal zero-findings path can lack persisted `NEXT_ACTION=step3b` and `.completed/step-3`, breaking the sentinel double-gate.
- **Proposed resolution**: In `### UPDATED: python/plan_review.py`, add an explicit bullet for the `if degraded_exit:` block at ~2099-2117 mirroring the terminal zfdp contract (persist rows, `NEXT_ACTION=step3b`, `write_terminal=True`, `step3_loop_write_completed_step3`).



### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:245-246
- **Concern**: Mid-loop resume sub-table groups main-agent-vote-required with Gate B apply. Scenario: The proposed SKILL.md mid-loop bullets list main-agent-vote-required twice: first as MAV post-phase resume, then again in a combined line with main-agent-apply-required and per-round-approval-required routed through Gate B apply and awaiting-continuation. MAV must resume via design-step3-mav.sh and awaiting-apply or awaiting-continuation, not Gate B apply. An implementer following the combined bullet can route MAV bail-outs through Gate B and break the existing MAV contract.
- **Proposed resolution**: Split the bullets: keep main-agent-vote-required on the MAV-only resume path (awaiting-apply or awaiting-continuation from the MAV post wrapper). Limit the Gate B apply bullet to main-agent-apply-required and per-round-approval-required only, matching current skills/design/SKILL.md:617-619 and approval-gates.md.



### FINDING_9:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/plan_review.py:1042-1090; skills/design/scripts/design-step3-mav.sh:253-350
- **Concern**: MAV retally-ok path can persist a post-loop NEXT_ACTION even though the plan says retally-ok resumes mid-loop.. Scenario: The planned persist_retally_step3_env change computes NEXT_ACTION from rows with TALLY_PLAN_REVIEW_STATUS=ok and LOOP_STATUS=complete. That can write NEXT_ACTION=step3b to .step3-review-result.env while MAV post is still supposed to resume awaiting-apply or awaiting-continuation. Recovery that reads the result env can see a terminal route before the resumed wrapper runs.
- **Proposed resolution**: Limit persist_retally_step3_env NEXT_ACTION persistence to retally-error, or otherwise suppress NEXT_ACTION for retally_status=ok mid-loop resumes. Extend the MAV test to assert ok retally does not emit or persist a post-loop NEXT_ACTION.



### FINDING_10:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:617-619
- **Concern**: Prior MAV Gate-B cleanup is incomplete: the proposed mid-loop sub-table still lists main-agent-vote-required under Gate B apply.. Scenario: NEXT_ACTION=main-agent-vote-required maps to mav, but the retained sub-table also says main-agent-vote-required uses Gate B apply. That keeps a second routing authority beside the NEXT_ACTION table and can send MAV-required rounds to the wrong prompt path.
- **Proposed resolution**: Remove main-agent-vote-required from the Gate B apply sub-table bullet. Keep it only in the MAV post wrapper route, then list Gate B apply for main-agent-apply-required and per-round-approval-required.



