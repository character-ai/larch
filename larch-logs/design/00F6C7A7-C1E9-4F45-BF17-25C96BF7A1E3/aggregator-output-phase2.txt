Verifying referenced locations so normalized findings match the codebase.
Both inputs come from the same reviewer slot but target different artifacts (plan minimum-touch list vs. structure-test coverage) and need different fixes, so they stay as two separate findings.

### FINDING_1: Plan omits main-branch-post-dispatch IMPLEMENT_BAIL_REASON mirror
- **Reviewer(s)**: Cursor-dyn-step2-bail-completeness
- **Severity**: important
- **Concern**: The minimum-touch list does not call out `skills/implement/SKILL.md` line 630 (`main-branch-post-dispatch`), even though that is a live Step-2 site that already sets `FINAL_BAIL_REASON=main-branch-post-dispatch`, `STALL_TRACKING=true`, and bails to Step 12d on post-dispatch branch mismatch. Plan line 27 requires mirroring `IMPLEMENT_BAIL_REASON` at every such site, but lines 28–30 only name §2.1.5 and a new §2.2 `STATUS=bailed` bullet; the catch-all is scoped to the “§2.2 hard-bail branch,” so an implementer may skip `:630`. Step 18a classify would then see an empty `IMPLEMENT_BAIL_REASON` and the Bail reason row would show none.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-step2-bail-completeness: Explicitly add skills/implement/SKILL.md:630 (main-branch-post-dispatch) to minimum-touch sites: set IMPLEMENT_BAIL_REASON=main-branch-post-dispatch alongside existing FINAL_BAIL_REASON/STALL_TRACKING before Step 12d

### FINDING_2: Structure tests omit main-branch-post-dispatch IMPLEMENT_BAIL_REASON pin
- **Reviewer(s)**: Cursor-dyn-step2-bail-completeness
- **Severity**: important
- **Concern**: `scripts/test-implement-structure.sh` already greps `FINAL_BAIL_REASON=main-branch-post-dispatch` at lines 124–125, but planned assertions only cover §2.1.5 and §2.2 `STATUS=bailed`. A partial SKILL edit can leave line 630 without `IMPLEMENT_BAIL_REASON=main-branch-post-dispatch` and still pass structure tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-step2-bail-completeness: Add grep/assert that IMPLEMENT_BAIL_REASON=main-branch-post-dispatch appears adjacent to the existing FINAL_BAIL_REASON=main-branch-post-dispatch pin at skills/implement/SKILL.md:630
