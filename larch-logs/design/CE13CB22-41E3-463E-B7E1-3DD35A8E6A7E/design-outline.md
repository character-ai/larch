## Proposed Design Outline

### Goals
- Stop `/design` filing spurious `escalation-success` GitHub issues when a successful run's only escalation evidence is a normal main-agent handoff (`main-agent-apply-required`, `main-agent-vote-required`, `postplan-operator-required`).
- Preserve `escalation-success` reporting for genuine Step-3 failures (`panel-failed`, `panel-init-failed`, `tally-error`, `degraded-empty-collector`).
- Add regression coverage proving the split (normal handoff → no report; genuine failure → report).

### Non-goals
- Do NOT disable the escalation-success reporting feature.
- Do NOT change the terminal-failure report path or genuine-failure semantics.
- Retroactive cleanup of already-filed noise issues (operational, separate task).

### Approach sketch
- Split the Step-3 escalation-evidence statuses into two named sets: normal handoffs vs genuine failures.
- Prevent the three normal handoffs from contributing escalation evidence that reaches the `escalation-success` report gate; keep genuine failures behaving as today.
- Center the change on `plan_review_normalize.py` (`step3_record_report_evidence`) and/or `design_terminal.py` (`escalation_evidence_present`); prefer the smallest surgical fix that keeps genuine failures loud (G-Py-4).
- If a shared token set is introduced, define it once as a Final (G-Cfg-1) rather than re-listing statuses.

### Surfaces in scope
- `python/larch/review/plan_review_normalize.py` — Step-3 escalation-evidence recording.
- `python/larch/design/design_terminal.py` — escalation-evidence report gate.
- `python/larch/config.py` — named status token sets, if centralized.
- `python/tests/review/test_plan_review.py` / `python/tests/design/test_design_lifecycle.py` — regression tests.

### Open questions
- Exact filter location (stop recording handoff ledger rows vs exclude them at the report gate) and whether the ledger has an independent run-log role to preserve — resolve during plan drafting/review.
