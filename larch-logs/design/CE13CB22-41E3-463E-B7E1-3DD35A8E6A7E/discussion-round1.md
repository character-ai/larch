## Decision 1: Root problem
- **Question**: Why was issue #6231 (`escalation-success`) auto-filed, and is it a defect?
- **Resolution**: A successful `/design` run files an `escalation-success` GitHub issue whenever the escalation ledger has any content. Normal Step-3 main-agent handoffs write ledger rows, so nearly every successful run with accepted findings files a spurious `[Bug]` issue. This is a larch defect (noise), not intended telemetry for those statuses.
- **Source**: user + codebase (`design_terminal.py` lines 766-776; `plan_review_normalize.py` `step3_record_report_evidence`)

## Decision 2: Which statuses stop counting as escalation evidence
- **Question**: Which Step-3 handoff statuses should no longer count as escalation evidence for the `escalation-success` report?
- **Resolution**: All three normal handoffs — `main-agent-apply-required`, `main-agent-vote-required`, `postplan-operator-required` — must stop counting as escalation evidence that triggers an `escalation-success` report.
- **Source**: user

## Decision 3: Genuine failures must still be reported (hard constraint)
- **Question**: Should genuine panel/tally failures still count as escalation evidence?
- **Resolution**: Yes. `panel-failed`, `panel-init-failed`, `tally-error`, and `degraded-empty-collector` MUST remain escalation evidence and continue to produce `escalation-success` reports on otherwise-successful runs. Do not disable the escalation-success reporting feature; only stop the three normal handoffs from triggering it.
- **Source**: user

## Decision 4: Retroactive cleanup is out of scope (non-goal)
- **Question**: Should this change also close/clean up the escalation-success issues already filed by the buggy behavior?
- **Resolution**: Out of scope. This design covers only the code fix that prevents future spurious reports (plus regression coverage). Cleaning up already-filed noise issues is a separate operational task.
- **Source**: codebase/scope judgment (surgical-change principle)
