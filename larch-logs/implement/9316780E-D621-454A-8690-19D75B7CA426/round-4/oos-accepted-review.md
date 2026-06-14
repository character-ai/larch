### OOS_70: [OUT_OF_SCOPE] C4c retired script paths not yet in migration manifest
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: C4c retired script paths not recorded in `python/migrated-scripts.tsv`. Future bash deletion will fail `lint-retired-scripts` until rows are added.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add C4c rows before deleting absorbed scripts.
  - From cursor-specialist-testing-output.txt: Add all plan-listed retired paths with issue number; finish deletion and run `lint-retired-scripts`.


