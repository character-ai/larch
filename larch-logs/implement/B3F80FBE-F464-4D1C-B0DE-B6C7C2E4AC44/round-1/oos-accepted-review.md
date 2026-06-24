### OOS_1: [OUT_OF_SCOPE] No mechanical enforcement or structure-test pin for NEVER #21
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: NEVER #21 has no structural `require()` pin in `scripts/test-implement-structure.sh` (unlike NEVER #8 and #14). No dirty-tree probe at item 6 exit or hook gating on Edit/Write. Prompt-only guard can still be ignored; future work per issue open questions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: add a `require(skill, 'NEVER make Edit, Write, or repo-mutating Bash calls between Preflight item 6', ...)` pin alongside the existing NEVER pins.


### OOS_2: [OUT_OF_SCOPE] Bootstrap ordering: tracking rename before dirty-tree check
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: In `python/bootstrap.py`, tracking rename runs before dirty-tree check and branch creation. Pre-Step-0 edits plus Step 0 can yield an `[IMPLEMENTING]` title with dirty `main` and no feature branch. Pre-existing; consider bootstrap ordering in follow-up.
- **Suggested revisions (informational for voters; coder decides)**:


