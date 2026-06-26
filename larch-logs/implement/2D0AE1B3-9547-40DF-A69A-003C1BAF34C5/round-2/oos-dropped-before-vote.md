### OOS_1: [OUT_OF_SCOPE] Missing `*.dropped-slots` dedupe test in progress report
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Plan-required duplicate `*.dropped-slots` dedupe test is absent. Duplicate ledger files could double-count Reviewer slot failures without CI catching it. `progress_report.py` implements `seen` dedupe, but the behavior is untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Fixture with two ledgers for one drop; assert failure total counts once.

