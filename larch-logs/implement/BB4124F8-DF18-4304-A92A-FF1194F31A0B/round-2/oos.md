### OOS_1: [OUT_OF_SCOPE] assess-plan-round redundant HARD / round checks
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `assess-plan-round.sh` re-validates HARD and `round<2` when only called from the HARD driver path; redundant work on every Step 3.6 HARD run (pre-existing). Add caller-gated fast path in a separate change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add caller-gated fast path in a separate change.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_2: [OUT_OF_SCOPE] write-after rollback cursor/value semantics (pre-existing)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: write-after rollback sets `review-round-count` to `ROUND_NUM-1` but `write-cursor --value ROUND_NUM`; possible cursor/count drift on rollback. Audit snapshot round-state contract separately.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Audit snapshot round-state contract separately.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_3: [OUT_OF_SCOPE] design-postplan-emit shares stale-env WARN pattern
- **Reviewer(s)**: dyn-warn-routing-output.txt
- **Severity**: nit
- **Concern**: `design-postplan-emit.sh` uses the same post-write-failure WARN-on-stdout-only pattern and the same `_parse_ok` + stdout WARN gating in SKILL.md Step 2b; the stale-env hole is sibling-shared, not unique to Step 3.6, but this branch amplifies it with a new stdout-only operational WARN on write failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-warn-routing-output.txt: Address the concern above.

---

**Merge notes (for voters, not part of machine output):**

| Subsumed inputs | Merged into |
|-----------------|-------------|
| 1, 10, 15, 24, 30, 35 | FINDING_1 |
| 3, 34, 36 (+ OOS 40, 41 as harness/context) | FINDING_3 |
| 4, 18 | FINDING_4 |
| 9, 19, 23, 26, 29, 42 | FINDING_8 |
| 28, 43 | FINDING_19 |
| 31–33, 37–39 | Dropped (noise / affirmative) |
| 8, 12, 44 | OOS_1–OOS_3 |

Highest-priority voter themes: **FINDING_8** (stale env + handoff), **FINDING_3** (classification vs `workflow_path`), **FINDING_1** (ignored `_assess_rc`), plus test gaps **FINDING_10**, **FINDING_11**, **FINDING_19**.

Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

