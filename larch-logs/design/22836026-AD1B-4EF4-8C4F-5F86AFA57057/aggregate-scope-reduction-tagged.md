### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review_loop.py
- **Concern**: [SCOPE-REDUCTION] Gate B start scan filters vendor rows to skill=design but live plan-review vendor rows use skill=implement. Scenario: On committed design ledgers (e.g. larch-logs/design/F37028B8-64BD-4BB2-96DB-44ADEB6B87B0/timing-ledger.tsv) every Step 3 reviewer/aggregator/voter row is v1 vendor with skill=implement while v1 round rows use skill=design. Filtering gate_b_start candidates to skill=design finds zero overlapping rows, triggers the no-candidate skip, and leaves the Round N Gantt tail unlabeled on the exact reproduction path.
- **Proposed resolution**: Drop the skill=design vendor filter. Derive gate_b_start_s as max(end_s) over v1 vendor rows that overlap round-start-s..frozen end_s, exclude task_kind gate-b-apply, and include signal rows. Match _progress_vendor_rows window overlap (no skill column filter). Update test_plan_review.py and test_progress_report.py fixtures to seed implement-skill vendor rows like production, not design-skill rows.
