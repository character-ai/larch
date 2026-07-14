---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_1

### FINDING_1: Missing Step 8 ship contract retarget (G-Cfg-3)
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: The plan updates `step-5-review.md` and `step-18.md` but has no `### UPDATED: skills/implement/scripts/step-8-ship.md` row. After `test-step-8-ship.sh` is deleted, the Edit-in-sync block in `step-8-ship.md` will still name the retired harness as the coverage owner. That violates acceptance that removed paths leave no documentation references and breaks G-Cfg-3 writer/selector alignment for Step 8 ship edit-in-sync.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: skills/implement/scripts/step-8-ship.md: replace test-step-8-ship.sh in Edit-in-sync with python/tests/implement/test_implement_shell_scripts.py and the Step 8 node group (static pins, seeder argv, rejoin, handoff, guard, merge-result fail-closed cases).


### [Plan Review] FINDING_2

### FINDING_2: Step 18 finalize ordering assertions depend on restore-mismatch log
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: Step 18 finalize output-ordering assertions in `test-step-18.sh` read line order from `$TMP_ROOT/restore-mismatch.log` produced by the immediately preceding restore-mismatch finalize run, not from a standalone invocation. Porting ordering into an isolated pytest node without that shared log (or an equivalent re-run) drops five ordering assertions while other Step 18 ports can still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In the Step 18 port list, state that ordering nodes execute against the restore-mismatch finalize stub log (same coupling as `test-step-18.sh:294-326`) or fold ordering checks into that scenario.


### [Plan Review] FINDING_3

### FINDING_3: Token-propagation contract still documents wrong `review-and-fix` entrypoint
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: minor
- **Concern**: `test-implement-review-token-propagation.md` Coverage and Edit-in-sync sections still document `python/cli.py review-and-fix apply-findings`, while the legacy harness (`test-implement-review-token-propagation.sh`) and planned pytest port exercise `review-and-fix step5`. A title-and-module-only retarget can preserve the wrong subcommand and misdirect future edit-in-sync work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In the `### UPDATED: skills/implement/scripts/test-implement-review-token-propagation.md` step, explicitly require Coverage and Edit-in-sync to document `review-and-fix step5 --mode single` (and drop `apply-findings`).
  - From Cursor-Pragmatic: In the `### UPDATED: skills/implement/scripts/test-implement-review-token-propagation.md` step, require Coverage and Edit-in-sync to name `review-and-fix step5` (and the real `review core` stub path) and remove `apply-findings` references.
  - From Cursor-Requirements: In the `### UPDATED: skills/implement/scripts/test-implement-review-token-propagation.md` step, require rewriting Coverage and Edit-in-sync to `review-and-fix step5`, matching the harness and planned pytest nodes.


### [Plan Review] FINDING_4

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/tests/implement/test_implement_shell_scripts.py
- **Concern**: [SCOPE-REDUCTION] Do not port Step 18 SKILL.md prose-pin grep assertions into pytest. Scenario: `test-step-18.sh:271-273` only grep `skills/implement/SKILL.md` for missing-marker and no-Read prose already pinned by `python/tests/skills/_structure_implement_specialized.py:422-424` and `scripts/test-render-cost-line-callsites.sh:69-70`. Porting them adds duplicate maintenance with no new behavioral coverage.
- **Proposed resolution**: Record in the Step 18 harness contract that those two grep assertions stay owned by structure/callsite pins; exclude them from the pytest parity matrix before deleting `test-step-18.sh`.

---LARCH-REJECTED-END---
