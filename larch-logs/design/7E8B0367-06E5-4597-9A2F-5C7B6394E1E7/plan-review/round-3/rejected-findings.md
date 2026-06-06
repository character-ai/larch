### [Plan Review] FINDING_10

### FINDING_10: Collapsed plan-review loop omits ordered post-round guards
- **Reviewer(s)**: Cursor-dyn-loop-collapse-status-mapping
- **Severity**: important
- **Concern**: The post-round collapse spec cites hoist range ~1780-1818 but omits ordered guards outside that range and per-status predicates. An implementer who hoists only tally/zero-findings checks skips `_round_rc != 0` (panel-failed at 1760-1777) and `main-agent-vote-required` (1751-1757); failures keep default `LOOP_STATUS=complete` from `_run_plan_review_round` (legacy branch at 1704-1725 already does this for tally-error).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-loop-collapse-status-mapping: Specify single-pass guard order explicitly: `_round_rc != 0` → `panel-failed` exit 1; then `main-agent-vote-required`; then `TALLY_PLAN_REVIEW_STATUS == tally-error` → `tally-error`; then zero-findings branches; then findings-present → `complete`

