### [Plan Review] FINDING_1

### FINDING_1:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/implement/ci_fixer_lane.py:456-492,543-588
- **Concern**: 1. Diagnostic capture covers crashes only. Scenario: A clean fixer that makes no progress returns `retry-next-tool` with `BGJOB_RC=0`; the plan preserves no launch context or log tails before teardown, despite requiring diagnostics for every non-`reship` outcome.
- **Proposed resolution**: Persist the same bounded, redacted diagnostic for `BGJOB_RC=0` `retry-next-tool` and `operator-bail` results before lineage advancement.

