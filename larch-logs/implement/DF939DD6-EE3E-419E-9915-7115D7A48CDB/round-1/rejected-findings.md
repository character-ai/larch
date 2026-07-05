### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: Rescue re-approval must precede stale closure
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-oos-merit
- **Severity**: important
- **Concern**: The rescue path can advance to `close-stale` or `oos-5` before the regrouped proposal is re-approved after merit resolution, which can close or apply against the pre-rescue scheme.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add explicit ordered steps: finalize merit batch apply rescues rerun oos-3 regroup re-approve if changed then close-stale then oos-5
  - From cursor-specialist-correctness: Add rule forbidding close-stale for merit-affected or rescued sources until merit batch final and regroup re-approved
  - From dyn-dyn-oos-merit: Add an explicit ordering rule: parse merit outcome (confirm + rescue) first; rerun `oos-3`/grouping; if the kept set or grouping changed, re-present and require fresh approval; only then run `close-stale`; only then enter `oos-5`.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: `oos-2` should only close stale-only sources
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: important
- **Concern**: The `oos-2` terminal path can treat a mixed stale-plus-merit-pending source as fully confirmed and close it too early.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Limit oos-2 close-stale to stale-only sources with no pending merit; carry mixed sources to oos-4


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** dismissed (0 YES)

### FINDING_5: Blanket approval must not survive rescue regrouping
- **Reviewer(s)**: dyn-dyn-oos-merit
- **Severity**: important
- **Concern**: A blanket approval can be reused after rescue even though the kept set or grouping changed, which can skip the required second approval.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-oos-merit: State explicitly that rescue always changes merit state and therefore requires re-presenting the combination/closure scheme; a prior blanket “apply all” does not authorize `oos-5` after rescue unless the operator re-confirms the updated proposal (or cancel and restart).


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

