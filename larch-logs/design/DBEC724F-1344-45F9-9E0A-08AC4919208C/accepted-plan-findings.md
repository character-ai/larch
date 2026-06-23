### FINDING_1: MainAgent sole-voter adjudication lacks named harness contract
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: When `tally_voter_file` is set for sole `--voter MainAgent:<file>`, `plan_review_tally.py` sets `eligible=1`, but the plan only vaguely says to add or extend MainAgent-adjudication coverage in `python/test_plan_review.py`. There is no existing `--voter MainAgent` tally test. An implementer can satisfy zero-judge tests while still passing a three-slot `voter_severities` list and break degraded adjudication with `ValueError`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a named test (new or explicit) that runs `plan-review tally` with sole `--voter MainAgent:<vote-file>`, asserts `TALLY_PLAN_REVIEW_STATUS=ok`, and asserts `voting-tally.md` includes `## Voter Severity Scoreboard` after agreement without raising from the length guard.


### FINDING_4: Voter-calibration harness severity assertion can pass with incomplete scoreboards
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The accepted harness fix in `skills/voter-calibration/scripts/test-voter-calibration.sh` can still pass when only one severity section exists. `grep -c ... | awk '$1>=2'` exits 0 even when the count is 0 or 1, and an unbounded slice after `## Agreement Table` can match the later global severity block. `make test-voter-calibration` can pass while either the panel or global severity scoreboard is missing, violating the explicit acceptance gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Use a failing shell count check and bounded section checks. For example assign the grep count and run `[[ "$count" -ge 2 ]]`, then use bounded awk ranges from `## Agreement Table` to `## Global Voter Agreement` and from `## Global Voter Agreement` to the next heading to require one severity heading in each range.
```

**Merge notes**

- **FINDING_5 + FINDING_6** → **FINDING_2** (same `eligible == 0` path and fix).
- **FINDING_4 + FINDING_7** → **FINDING_3** (same zero-findings round integration path and fix).
- **Input FINDING_2** (conflation) attributed to both **FINDING_2** and **FINDING_3** because it spans both code paths; kept separate from each other per different-fix / different-path rule.
- **Input FINDING_1** and **FINDING_9** stand alone.
- No `[OUT_OF_SCOPE]` tags in any source; all severities **important** → max **important**.


