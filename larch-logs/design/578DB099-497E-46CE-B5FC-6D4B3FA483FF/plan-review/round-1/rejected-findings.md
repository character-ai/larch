### [Plan Review] FINDING_6

### FINDING_6: Static dispatch failure short-circuit bypasses intended-slot threshold
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: Threshold scaling may be ineffective because `review-core.sh` can still fail immediately on `STATIC_DISPATCH_OK=false`, even when the failure is represented in collector results and should be evaluated against the new intended-slot denominator.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Call check-reviewer-failure-threshold.sh with --intended-slots even when STATIC_DISPATCH_OK=false; reserve immediate failure only for a dispatch-level error that cannot be represented in collector-results.env.


