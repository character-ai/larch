### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: design_summary degraded path lacks an em-dash regression test
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: The enrich-degraded/OSError branch in design_summary is still untested, so a later edit could reintroduce em-dash punctuation in the user-visible footer without failing CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add a test forcing the enrich-degraded branch and assert the footer text has no U+2014.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** dismissed (0 YES)

### FINDING_5: cost-line formatter needs an exact-string test
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: important
- **Concern**: The cost-line formatter switched from an em dash to a colon, but the tests still only check a prefix and token suffix, so the exact line shape is not locked down.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Add an exact-string assertion for the full cost line in python/tests/report/test_report_tokens_cost.py and lock the same formatter shape wherever it is reused


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

