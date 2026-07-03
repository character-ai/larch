### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:40-42; larch-logs/design/F37028B8-64BD-4BB2-96DB-44ADEB6B87B0/timing-ledger.tsv:4-17
- **Concern**: Gate B start scan filters out the real plan-review vendor rows. Scenario: The live reproduction ledger records plan-review reviewer and voter vendor rows with skill column implement, while the design Gantt uses those rows. With the proposed skill == design predicate, no candidates are found, the helper skips gate-b-apply, and accepted-finding rounds keep the unlabeled tail.
- **Proposed resolution**: Drop the vendor skill == design predicate for this derivation, or match the renderer contract by deriving from rows that overlap the round window and excluding only gate-b-apply. Add the test fixture with reproduction-shaped vendor rows whose skill column is implement.

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review_loop.py:549-558
- **Concern**: The Gate B start scan filters ledger rows to skill=design, but live /design plan-review vendor rows are written with skill=implement. Scenario: Committed run F37028B8-64BD-4BB2-96DB-44ADEB6B87B0 and other design run logs show every plan-review v1 vendor row uses the implement skill column (e.g. codex-phase1-codex-plan-arch, codex-phase1-voter-2) while only v1 round rows use design. _progress_vendor_rows renders those implement rows inside the design round window and never filters by skill. With skill=design the helper finds zero candidates, skips the gate-b-apply bar, and the reproduction gap (~239s after codex vote in round 1) stays unlabeled
- **Proposed resolution**: Drop the skill=design predicate. Derive gate_b_start_s as max(row_end_s) over all v1 vendor rows overlapping round-start-s..frozen end_s, excluding task_kind gate-b-apply only, matching the rows the Gantt already displays

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/review/test_plan_review.py:2316-2334
- **Concern**: Plan-review timing tests are specified to seed a design-skill vendor row, which does not match production ledger shape. Scenario: Tests would pass with skill=design fixtures while production still skips the bar because real subprocess timing uses LARCH_TIMING_SKILL=implement (default in timing record-vendor-task). This masks the blocking skill-filter bug
- **Proposed resolution**: In the _write_design_round_meta timing tests, seed vendor rows with skill=implement and plan-review task kinds (e.g. codex-phase1-voter-2) like _write_vendor_timing defaults and the F37028B8 ledger

### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/report/timing.py:703-716
- **Concern**: Planned Gate B helper filters candidate vendor rows to skill=design, but current plan-review vendor timing rows default to skill=implement unless LARCH_TIMING_SKILL is exported.. Scenario: The helper will find no prior vendor row in current design ledgers, skip the gate-b-apply row, and leave the original unlabeled tail unfixed.
- **Proposed resolution**: Derive Gate B start from overlapping vendor rows the same way the Gantt renderer does, or explicitly accept both design and legacy/default implement skill rows for plan-review timing. Add the plan-review test with an implement-skill vendor row.

### FINDING_6:
- **Reviewer(s)**: Cursor-dyn-Timing Ledger Integrity
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review_loop.py:549-558, python/larch/report/timing.py:714, larch-logs/design/F37028B8-64BD-4BB2-96DB-44ADEB6B87B0/timing-ledger.tsv:4-17
- **Concern**: Gate B start scan filters skill=design but plan-review vendor rows are skill=implement. Scenario: The helper is specified to scan only v1 vendor rows with skill=design. Production plan-review subprocess timing uses LARCH_TIMING_SKILL default implement (timing.py:714). The reproduction ledger has zero design-skill vendor rows; all reviewer/aggregator/voter rows are implement (lines 4-17). gate_b_start_s stays empty, the bar is skipped, and the unlabeled tail remains.
- **Proposed resolution**: Drop the skill=design filter. Scan overlapping v1 vendor rows excluding task_kind=gate-b-apply only, matching _progress_vendor_rows which does not filter by skill (progress_report.py:920-961). In test_plan_review.py use skill=implement vendor fixtures aligned with the reproduction ledger, not design-skill rows.

### FINDING_7:
- **Reviewer(s)**: Cursor-dyn-Timing Ledger Integrity
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/review/test_plan_review.py:2316-2334
- **Concern**: Planned timing test fixtures misrepresent production ledger skill column. Scenario: The new test is specified to add a design vendor row before _write_design_round_meta. That passes the broken skill=design filter while production rows are implement, so the test can go green without fixing the reproduction bug.
- **Proposed resolution**: Seed reviewer/voter rows with skill=implement (same columns as timing-ledger.tsv in the cited run log). Assert gate_b_start_s equals the latest implement-skill vendor end inside the round window.

### FINDING_8:
- **Reviewer(s)**: Codex-dyn-Timing Ledger Integrity
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:24-30; python/larch/report/progress_report.py:886-960; python/tests/report/test_progress_report.py:919-949
- **Concern**: Gate B can still be dropped by the existing Gantt cap. The plan only adds label handling and says not to change row caps, but progress_report preserves only _CODER_APPLY_TASK_KINDS under the cap. The existing cap test documents that late apply lanes disappear without this reservation.. Scenario: A design round with PROGRESS_GANTT_ROW_CAP normal reviewer or voter rows plus the late gate-b-apply row renders the earliest rows and drops gate-b/apply, leaving the same unlabeled tail despite the planned v1 vendor row.
- **Proposed resolution**: Keep the existing cap value and logic, but include gate-b-apply in the existing apply-lane preservation path, for example _CODER_APPLY_TASK_KINDS, and adapt the planned progress_report test to assert gate-b/apply survives an over-cap round.
