### [Plan Review] FINDING_1

### FINDING_1: stall-recovery.md Step 18a.5 forward pin stale after split
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: After moving eligible filing prose to `step18a5-filing.md`, `stall-recovery.md` still directs readers to `step18-cleanup.md` § Step 18a.5 for the full escalation-success procedure. Once the parent becomes gate-only, eligible-path implementers can skip Tier A/B filing steps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: skills/implement/references/stall-recovery.md` to forward gate/skip predicates to `step18-cleanup.md` and eligible filing to `step18a5-filing.md`; update `scripts/test-implement-structure.sh` line 512 forward pin accordingly.


### [Plan Review] FINDING_2

### FINDING_2: step18-cleanup.md Contract header still claims reporting ownership
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The parent `**Contract**` header still claims `step18-cleanup.md` owns escalation-success reporting while the plan makes it gate-only. Load-contract drift misroutes maintainers and reviewers to the wrong authority surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Revise the parent Contract to gate/skip/eligibility only; move reporting ownership to `step18a5-filing.md` Contract. Add a structure `forbid(step18-cleanup.md, 'escalation-success reporting', ...)` or equivalent if the phrase must not remain in the parent header.


### [Plan Review] FINDING_14

### FINDING_14:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:32-60
- **Concern**: [SCOPE-REDUCTION] Plan adds a third lazy-load reference `ship-pr-oos-checkpoint-router.md` beyond the binding issue’s two authorized splits (Step 18a.5 filing + autonomous CI-fix).. Scenario: Binding Mechanism authorizes only those two branch-only bodies (~28–39 every-run line savings). The third file plus lines 174–201 and 241–246 harness pins drive `diff_added: 198` / `diff_lines: 260`, expanding SKILL/matrix lazy-load surface without a completeness gate on the stated two-split scope.
- **Proposed resolution**: Drop the OOS-router split from this change. Keep `## OOS checkpoint router` inline in `ship-pr-exit-matrix.md` with only the mandatory-read pointer if needed; limit new files to `step18a5-filing.md` and `ship-pr-ci-fix.md`.


### [Plan Review] FINDING_15

### FINDING_15:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:32-61
- **Concern**: [SCOPE-REDUCTION] Plan still adds a third lazy-load reference `ship-pr-oos-checkpoint-router.md` beyond the binding issue’s two authorized splits (Step 18a.5 filing + autonomous CI-fix).. Scenario: The issue Mechanism authorizes only those two branch-only bodies (~28–39 line savings). The plan’s own `diff_added: 198` / `diff_lines: 260` is dominated by this third file plus a large OOS-router harness block (lines 174–201), expanding every-run SKILL/matrix edits without a completeness gate. Prior scope-reduction rejections on the same expansion still apply; the plan doubled down with more pins rather than dropping the split.
- **Proposed resolution**: Drop `ship-pr-oos-checkpoint-router.md` from scope. Keep the `## OOS checkpoint router` body inline in `ship-pr-exit-matrix.md` (or only a pointer without a third header loop). Limit new files to `step18a5-filing.md` and `ship-pr-ci-fix.md` per the binding Mechanism.


