### [Plan Review] FINDING_2

### FINDING_2: Timing tests should use implement-skill vendor fixtures
- **Reviewer(s)**: Cursor-Innovation, Cursor-dyn-Timing Ledger Integrity
- **Severity**: important
- **Concern**: The new timing test fixtures seed design-skill vendor rows, which does not match the production ledger shape. That can make the test pass even while the real plan-review flow still skips Gate B because the production timing rows are written with `skill=implement`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In the _write_design_round_meta timing tests, seed vendor rows with skill=implement and plan-review task kinds (e.g. codex-phase1-voter-2) like _write_vendor_timing defaults and the F37028B8 ledger
  - From Cursor-dyn-Timing Ledger Integrity: Seed reviewer/voter rows with skill=implement (same columns as timing-ledger.tsv in the cited run log). Assert gate_b_start_s equals the latest implement-skill vendor end inside the round window.


### [Plan Review] FINDING_3

### FINDING_3: Gate-b-apply can still disappear under the Gantt row cap
- **Reviewer(s)**: Codex-dyn-Timing Ledger Integrity
- **Severity**: important
- **Concern**: Even if Gate B is labeled, the existing Gantt row cap can still drop late apply lanes. If `gate-b-apply` is not preserved by the cap logic, the same unlabeled tail can reappear because the apply span never makes it into the rendered chart.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Timing Ledger Integrity: Keep the existing cap value and logic, but include gate-b-apply in the existing apply-lane preservation path, for example _CODER_APPLY_TASK_KINDS, and adapt the planned progress_report test to assert gate-b/apply survives an over-cap round.


