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


### FINDING_6: MAV retally-ok path can persist post-loop NEXT_ACTION during mid-loop resume
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The planned `persist_retally_step3_env` change computes `NEXT_ACTION` from rows with `TALLY_PLAN_REVIEW_STATUS=ok` and `LOOP_STATUS=complete`. That can write `NEXT_ACTION=step3b` to `.step3-review-result.env` while MAV post is still supposed to resume `awaiting-apply` or `awaiting-continuation`. Recovery that reads the result env can see a terminal route before the resumed wrapper runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Limit persist_retally_step3_env NEXT_ACTION persistence to retally-error, or otherwise suppress NEXT_ACTION for retally_status=ok mid-loop resumes. Extend the MAV test to assert ok retally does not emit or persist a post-loop NEXT_ACTION.


