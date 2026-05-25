### FINDING_3: Resume sentinel written on partial `/larch:issue` batch (`ISSUES_FAILED>0`)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `annotate` writes the filing/resume sentinel even when `ISSUES_FAILED>0`, so §0 / resume-close can skip re-filing while children are still missing; operator may need manual sentinel removal and this conflicts with documented partial filing / resume semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Guard sentinel on ISSUES_FAILED==0 and fix resume-close prose for partial states
  - From cursor-specialist-correctness-output.txt: Only write the resume sentinel when ISSUES_FAILED=0 (and URLs are complete); keep partial diagnostics in partition-filed.md without arming skip-re-file
  - From cursor-specialist-plan-fidelity-output.txt: Only write filing sentinel when ISSUES_FAILED==0; define partial-state handling per decompose-panel.md



