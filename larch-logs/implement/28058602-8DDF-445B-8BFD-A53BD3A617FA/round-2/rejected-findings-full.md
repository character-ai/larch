### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: design-postplan-emit.sh rc 2 skips drift when baseline exists
- **Reviewer(s)**: dyn-drift-guard-output.txt
- **Severity**: important
- **Concern**: When `check-plan-size.sh` returns rc `2` (missing/malformed `diff_lines` trailer, missing plan, etc.), `_postplan_finish_merged_plan_size` (`design-postplan-emit.sh:401–407`) flushes and exits `0` without ever evaluating drift, even if `drift-baseline.env` was written earlier. A Gate B / discussion rewrite can grow `plan.txt` substantially while leaving the trailer broken; the merged fence proceeds as "ok" and skips both hard-size and drift prompts, defeating the sprawl guard on a realistic failure path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-drift-guard-output.txt: On rc `2`, if a readable `drift-baseline.env` exists, still parse `plan_lines` from the body (or run a drift-only helper) and surface drift via rc `14` or a dedicated warning before the degraded proceed; at minimum, do not treat rc `2` as unconditional success when a baseline snapshot is present.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: Gate B applies plan mutations before drift check with no rollback on Cancel
- **Reviewer(s)**: dyn-interactive-flow-output.txt
- **Severity**: important
- **Concern**: The shared post-apply pipeline in `approval-gates.md` (lines ~130–141) applies accepted findings to `plan.txt` **before** the merged `design-postplan-emit.sh --with-plan-size` drift check. If `_postplan_rc=14` fires and the operator picks **Cancel**, the run exits with `SUMMARY_OUTCOME=cancelled-sprawl` while `plan.txt` already contains the Gate B rewrites. The operator sees a "sprawl cancelled" terminal summary but a mutated plan in `$DESIGN_TMPDIR`, with no documented rollback to the pre-apply snapshot.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-interactive-flow-output.txt: Either run drift sizing on a dry-run copy before mutating `plan.txt`, snapshot `plan.txt` before Gate B apply and restore on drift Cancel, or at minimum use a distinct outcome (e.g. `cancelled-plan-drift`) and print an explicit warning that Gate B edits were retained in the tmpdir.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: Drift Continue completion sentinels inconsistent across SKILL.md callers
- **Reviewer(s)**: dyn-interactive-flow-output.txt
- **Severity**: important
- **Concern**: Drift **Continue** completion sentinels are inconsistent: the Step 2b thin fence touches both `.completed/step-2b` and `.completed/step-2b.5` (`SKILL.md:1066–1068`), while the standalone Step 2b.5 drift branch and Gate B/discussion merged fences touch only `step-2b.5`. After a Gate B or discussion re-emit drift Continue, pause/resume may believe Step 2b is incomplete relative to the Step 2b thin-fence contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-interactive-flow-output.txt: Align all drift-Continue paths to touch the same sentinel set the invoking caller uses on a clean rc `0` path (Step 2b initial: both; Gate B/discussion: at least document that `step-2b` remains from the initial emit).

Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Override recovery re-anchors drift baseline to bloated plan
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Override recovery in `check-plan-size.sh` (lines ~184–191) seeds the drift baseline from the current expanded plan when the snapshot is absent. Operator Override after a hard cap re-anchors drift to the bloated plan, allowing further growth within 2× of an inflated baseline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Seed baseline only from initial Step 2b snapshot; do not write baseline on Override-first check-plan-size path.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Orphaned revise-plan-with-waterfall.sh remains shipped
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Orphaned LLM patch-apply helper `revise-plan-with-waterfall.sh` remains in-tree though Step 3 no longer invokes it. Future mis-wiring or manual invocation reintroduces the highest-risk automated plan-mutation path. Plan marks removal as follow-up OOS.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Remove script per planned follow-up or guard behind explicit dev-only flag; trim publish allowlist when safe.
  - From cursor-specialist-plan-fidelity-output.txt: Track follow-up issue to delete helper/docs/tests as planned.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

