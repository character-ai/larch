### FINDING_1: Absolute cli.py argv capture
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The shim interception in `python/tests/review/test_review_and_fix.py` can miss the real `review-and-fix step5` invocation because the wrapper passes an absolute `python/cli.py` path in `argv[1]`. If the test keys off a literal `python/cli.py` token instead of the actual argv layout, it may delegate to the real loop, hang, flake, or miss `DIFFICULTY_OVERRIDE` forwarding.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Match review-and-fix step5 when argv has review-and-fix at index 1 and step5 at index 2 after the cli.py path (or when argv[1].endswith("python/cli.py")), then assert flags on that captured slice only.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

