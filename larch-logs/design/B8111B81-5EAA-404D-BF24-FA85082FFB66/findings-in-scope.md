### FINDING_1: Mid-loop resume sub-table duplicates main-agent-vote-required under Gate B apply
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Generic
- **Severity**: blocking
- **Concern**: The proposed mid-loop resume sub-table lists `main-agent-vote-required` twice with conflicting routes: once on the MAV post-wrapper path and again grouped with `main-agent-apply-required` and `per-round-approval-required` under Gate B apply / `awaiting-continuation`. Post-loop vote-required maps to `NEXT_ACTION=mav`, not `gate-b`. An implementer can route MAV bail-outs through Gate B apply/resume instead of `design-step3-mav.sh`, skipping vote/re-tally and breaking mid-loop recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Keep a single main-agent-vote-required row for MAV post resume only. Limit the Gate B apply row to main-agent-apply-required and per-round-approval-required. Keep per-round-approval-required findings-file as a sub-bullet under Gate B only.
  - From Cursor-Innovation: Split the bullets: keep main-agent-vote-required only on the MAV post resume line; limit the Gate B apply bullet to main-agent-apply-required and per-round-approval-required only.
  - From Cursor-Pragmatic: Split bullets: keep `main-agent-vote-required` only on the MAV post-wrapper row; limit the Gate B apply row to `main-agent-apply-required` and `per-round-approval-required` with the existing resume flags.
  - From Cursor-Requirements: Split the bullets: keep main-agent-vote-required on the MAV-only resume path (awaiting-apply or awaiting-continuation from the MAV post wrapper). Limit the Gate B apply bullet to main-agent-apply-required and per-round-approval-required only, matching current skills/design/SKILL.md:617-619 and approval-gates.md.
  - From Codex-Generic: Remove main-agent-vote-required from the Gate B apply sub-table bullet. Keep it only in the MAV post wrapper route, then list Gate B apply for main-agent-apply-required and per-round-approval-required.

### FINDING_2: SKILL.md mid-loop prose still references deleted post-loop resume matrix
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The proposed SKILL rewrite deletes the post-loop branch matrix and adds a `NEXT_ACTION` table, but lines 615 and 660 still tell orchestrators to use the post-loop resume matrix for mid-loop returns. After deletion, mid-loop resume flags lose a stable anchor and can drift back to deleted matrix wording.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the SKILL.md rewrite, replace post-loop resume matrix at 615 and 660 with mid-loop resume sub-table keyed on STEP3_REVIEW_LOOP_STATUS. Cross-link the retained sub-table in section 3 of the rewrite.

### FINDING_3: Mid-loop sub-table header conflicts with NEXT_ACTION-only post-notification routing
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Post-notification bullets (255-260) require exclusive routing via persisted `NEXT_ACTION`, but the mid-loop sub-table header (243) says it is keyed on `STEP3_REVIEW_LOOP_STATUS`, not `NEXT_ACTION`. Line 251 only says status selects resume flags, not that post-notification must never branch on the sub-table first. Dual-authority routing the plan retires can return for mid-loop bail-outs (`mav`, `gate-b`, `postplan-operator`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Scope the sub-table explicitly to launcher flag/round binding after the orchestrator has already branched on `NEXT_ACTION`; add one sentence that post-notification routing never uses this sub-table instead of `NEXT_ACTION`.

### FINDING_4: Terminal normalize early returns omit NEXT_ACTION persist
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan says `normalize_step3_status_main` must merge recomputed `NEXT_ACTION` into `.step3-review-result.env`, but the post-loop flow still calls `_step3_emit_normalize_envelope` then returns 1 after printing `SUMMARY_OUTCOME` for `postplan-failed` and `panel-init-failed` without a named persist step. Hook-blocked `--read-result-env` recovery and file-first post-notification routing can see terminal statuses without `NEXT_ACTION=final-summary:*`, hitting the planned missing-`NEXT_ACTION` routing error.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Before the postplan-failed and panel-init-failed early returns in normalize_step3_status_main, persist recomputed NEXT_ACTION (and normalized status fields) to .step3-review-result.env via the same merge helper used elsewhere; add a pytest that normalize leaves NEXT_ACTION=final-summary:failed-judge-panel in the file when stdout prints SUMMARY_OUTCOME.

### FINDING_5: Terminal degraded_exit zfdp path omits full persist and step-3 sentinel
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Plan lines 92-93 require terminal zfdp to call full `step3_loop_persist_envelope(..., write_terminal=True)` plus `step3_loop_write_completed_step3`, but the `python/plan_review.py` edit section does not name the `degraded_exit` branch at ~2099-2117. Today that branch only emits stdout KVs and returns, so even with in-loop fixes the terminal zero-findings path can lack persisted `NEXT_ACTION=step3b` and `.completed/step-3`, breaking the sentinel double-gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In `### UPDATED: python/plan_review.py`, add an explicit bullet for the `if degraded_exit:` block at ~2099-2117 mirroring the terminal zfdp contract (persist rows, `NEXT_ACTION=step3b`, `write_terminal=True`, `step3_loop_write_completed_step3`).

### FINDING_6: MAV retally-ok path can persist post-loop NEXT_ACTION during mid-loop resume
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The planned `persist_retally_step3_env` change computes `NEXT_ACTION` from rows with `TALLY_PLAN_REVIEW_STATUS=ok` and `LOOP_STATUS=complete`. That can write `NEXT_ACTION=step3b` to `.step3-review-result.env` while MAV post is still supposed to resume `awaiting-apply` or `awaiting-continuation`. Recovery that reads the result env can see a terminal route before the resumed wrapper runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Limit persist_retally_step3_env NEXT_ACTION persistence to retally-error, or otherwise suppress NEXT_ACTION for retally_status=ok mid-loop resumes. Extend the MAV test to assert ok retally does not emit or persist a post-loop NEXT_ACTION.
