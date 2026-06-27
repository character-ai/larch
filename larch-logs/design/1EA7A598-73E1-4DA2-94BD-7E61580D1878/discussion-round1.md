## Decision 1: CI-mergeable definition
- **Question**: Should skipped/neutral/cancelled checks count as acceptable for merging?
- **Resolution**: Lenient — skipped, cancelled, neutral, unknown all count as acceptable. Only "fail" and "pending" block merging.
- **Source**: user

## Decision 2: Stuck-bucket guard in merge loop
- **Question**: Should we add a guard that bails with a diagnostic when CI_NOT_READY persists unchanged N times?
- **Resolution**: Yes — add a guard. After N consecutive CI_NOT_READY results from merge_pr, bail with a clear message naming the stuck bucket instead of silently hitting the 50-iteration cap.
- **Source**: user

## Decision 3: Acceptable buckets in text fallback
- **Question**: In the text-based fallback classifier (_CHECKS_TEXT_BAD_RE), should "cancelled" and "skipping" remain blocking?
- **Resolution**: No — align with the lenient definition. Remove "cancelled" and "skipping" from the bad-pattern regex. Keep "fail", "pending", "in_progress", "queued" as blocking (they represent truly not-yet-done states).
- **Source**: codebase (derived from Decision 1)

## Decision 4: Required-path classifier unchanged
- **Question**: Should the required=True path in ci_monitor._classify_checks_json also be loosened?
- **Resolution**: No — the required classifier correctly fails-closed (cancelled/skipping/unknown → fail). It is used for a different purpose (verifying required checks after a fix attempt). Leave it unchanged.
- **Source**: codebase (issue analysis + test_ci_monitor.py:3020-3025)

2 user decisions + 2 codebase decisions resolved.
