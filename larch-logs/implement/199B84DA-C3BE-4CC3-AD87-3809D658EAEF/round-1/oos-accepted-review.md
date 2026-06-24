### OOS_1: [OUT_OF_SCOPE] Stale parse_failed warning after successful degraded retry
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `parse_failed` still calls `surface_warning` inside `python/review_tally.py` (~872–878) before the degraded-retry decision settles. A successful degraded-panel retry can leave a stale parse-failure warning in the final run summary (same append-only bug class as #5334). Defer `parse_failed` warning surfacing to the caller after retry settles, or retract it on successful retry (separate follow-up fix).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


