### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:32-60
- **Concern**: [SCOPE-REDUCTION] Plan adds a third lazy-load reference `ship-pr-oos-checkpoint-router.md` beyond the binding issue’s two authorized splits (Step 18a.5 filing + autonomous CI-fix).. Scenario: Binding Mechanism authorizes only those two branch-only bodies (~28–39 every-run line savings). The third file plus lines 174–201 and 241–246 harness pins drive `diff_added: 198` / `diff_lines: 260`, expanding SKILL/matrix lazy-load surface without a completeness gate on the stated two-split scope.
- **Proposed resolution**: Drop the OOS-router split from this change. Keep `## OOS checkpoint router` inline in `ship-pr-exit-matrix.md` with only the mandatory-read pointer if needed; limit new files to `step18a5-filing.md` and `ship-pr-ci-fix.md`.

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:32-61
- **Concern**: [SCOPE-REDUCTION] Plan still adds a third lazy-load reference `ship-pr-oos-checkpoint-router.md` beyond the binding issue’s two authorized splits (Step 18a.5 filing + autonomous CI-fix).. Scenario: The issue Mechanism authorizes only those two branch-only bodies (~28–39 line savings). The plan’s own `diff_added: 198` / `diff_lines: 260` is dominated by this third file plus a large OOS-router harness block (lines 174–201), expanding every-run SKILL/matrix edits without a completeness gate. Prior scope-reduction rejections on the same expansion still apply; the plan doubled down with more pins rather than dropping the split.
- **Proposed resolution**: Drop `ship-pr-oos-checkpoint-router.md` from scope. Keep the `## OOS checkpoint router` body inline in `ship-pr-exit-matrix.md` (or only a pointer without a third header loop). Limit new files to `step18a5-filing.md` and `ship-pr-ci-fix.md` per the binding Mechanism.

### FINDING_12:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh
- **Concern**: [SCOPE-REDUCTION] OOS-router parent forbids still miss body text. Scenario: The planned `ship-pr-exit-matrix.md` split forbids the obvious router tokens, but it does not catch the remaining router prose such as `fallback counts only when ndjson is absent` or the stderr-preservation sentence. A partial edit can still leave the OOS checkpoint body inline in `ship-pr-exit-matrix.md:90-100`, so the every-run load and duplicate authority do not actually disappear.
- **Proposed resolution**: Extend the parent `forbid` set to cover the remaining router-only sentences, or move the whole section under a single child-reference guard so no router prose can survive inline.

### FINDING_13:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh
- **Concern**: [SCOPE-REDUCTION] CI-fix parent forbids still leave repair steps inline. Scenario: The CI-fix split forbids routing tokens, but it still leaves uncovered body prose such as the minimal-repair, git-add, commit, and run-log-refresh steps in `ship-pr-exit-matrix.md:102-117`. That lets a partial move keep autonomous repair instructions inline, so the lazy-load split can pass while the every-run path still carries most of the CI-fix body.
- **Proposed resolution**: Broaden the parent `forbid` list to cover the remaining CI-fix body sentences, or gate the whole section with a single child-reference move check so no repair steps remain inline.
