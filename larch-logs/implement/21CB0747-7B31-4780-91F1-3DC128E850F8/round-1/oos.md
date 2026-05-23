### FINDING_2: [OUT_OF_SCOPE] Run-log and plan artifacts vs branch reality (`larch-logs/implement/21CB0747-7B31-4780-91F1-3DC128E850F8`, `plan-goals-test.md`)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-residue-completeness-output.txt
- **Concern**: Together: the run-log flush commit is not reflected in the issue plan’s nine-file / no-new-files framing; the archived `plan-goals-test.md` snapshot can mislead anyone treating it as a live checklist; and the embedded plan text still contains literals for removed script names so repo-wide grep for those tokens continues to hit `larch-logs/` after Class C edits elsewhere—i.e. partial drift relative to grep expectations unless policy exempts archived logs. Sources flag this as out of scope given intentional `larch-logs` practice.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-residue-completeness-output.txt: **Suggested fix:** If the log must stay verbatim for audit traceability, document that `larch-logs/` is intentionally exempt from the Class C grep contract; otherwise regenerate or hand-edit `plan-goals-test.md` so the flushed snapshot matches post-migration wording (or drop the verbose plan paste and keep only the goal line).


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_5: [OUT_OF_SCOPE] Stale header comments in `skills/issue/scripts/add-blocked-by.sh:13-15`
- **Reviewer(s)**: dyn-residue-completeness-output.txt
- **Concern**: Header comments still describe parity with deleted `skills/fix-issue/scripts/find-lock-issue.sh` and name `find-lock-issue.sh`; file not in this branch’s diff; stale framing predates this change set—follow-up PR territory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-residue-completeness-output.txt: **Suggested fix:** In a follow-up PR, rewrite those lines to reference the live Issue Dependencies API usage (this script’s GET/POST pairing) without naming the removed script.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_6: [OUT_OF_SCOPE] `/fix-issue` mention in `scripts/token-cost.md:5,55`
- **Reviewer(s)**: dyn-residue-completeness-output.txt
- **Concern**: Prose still lists `/fix-issue` as a consumer of `token-cost.sh` alongside `/implement`; not touched by this diff; matches known drift from older review logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-residue-completeness-output.txt: **Suggested fix:** Update the intro and table row to `/implement` only (or “final-report path via `scripts/render-run-summary.sh`”) in a separate doc sweep.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_7: [OUT_OF_SCOPE] Historical launcher / `find-lock-issue.sh` mentions in `CHANGELOG.md`
- **Reviewer(s)**: dyn-residue-completeness-output.txt
- **Concern**: Historical entries still mention removed launchers and `find-lock-issue.sh`; expected changelog archaeology; unchanged by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No non-placeholder revision text was supplied in the `Suggested revision` field for this slot.)

**Subsumed (no separate heading):** `dyn-residue-completeness-output.txt` “Makefile / harness wiring” note (input FINDING_13)—positive attestation that no `Makefile` references to the ten removed `test-*` tokens remain; no distinct fix path vs other findings. Not emitted as a `### FINDING_N:` block.

Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

