### OOS_1: [OUT_OF_SCOPE] `_has_header` name misleading for missing-plan warnings
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_has_header` is true for missing-plan warning text as well as the review header; misleading name only, no functional bug.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Rename when editing sentinel logic.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_2: [OUT_OF_SCOPE] `D6B`-style test covers `LOOP_STATUS` only, not `TALLY_PLAN_REVIEW_STATUS`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Safe-env `rc!=0` precedence test covers `LOOP_STATUS` only; tally status could be clobbered from stdout on `rc!=0` while file precedence for `LOOP_STATUS` remains tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Extend D6B-style case to assert TALLY_PLAN_REVIEW_STATUS file wins as well.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_3: [OUT_OF_SCOPE] `run-step3-review.md` exit-code table ambiguity for `--preview-only`
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Exit-code table describes exit `0` as “normal completion (any settled `LOOP_STATUS`)” but does not call out `--preview-only` always exiting `0` after preview render; doc clarity only, not a plan-required functional regression.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_4: [OUT_OF_SCOPE] Optional plan grep pins for display-pass / rc=2 banner not added
- **Reviewer(s)**: dyn-display-parse-sync-output.txt
- **Severity**: nit
- **Concern**: Branch adds thin-fence and `_step3_safe_env_loaded` pins but not the plan’s optional grep pins for display-pass suppression logic or `exit 1` immediately after the Step 3 rc=2 banner; doc/plan drift rather than display/parse list mismatch (SKILL.md and harness lists already match).
- **Suggested revisions (informational for voters; coder decides)**:

---

**Merge summary**: 31 raw inputs → **14 in-scope** `FINDING_*` blocks and **4** `OOS_*` blocks. Major consolidations: structure/REPO/grep pins (1, 10, 11, 13, 23, 25, partial 31); preview harness gaps (2, 9, 12, 19, 24); duplicate H1 (4, 15, 22, 26); `D_WARN` test vs WARN dedup split (28+30 vs 29). No `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` line (non-empty merge).

Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

