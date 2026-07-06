# Review Round 1

- Mode: `diff`
- 5 accepted, 3 rejected (2 neutral)

## Accepted Findings

### FINDING_6: merge-conflict markers remain in the skill-closure baseline
- **Reviewer(s)**: cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: Unresolved conflict markers in `python/skill-closure-baseline.json` make the baseline invalid JSON, so linting and diff checks can fail before feature tests run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_10: route-exit classification misses invariant cases
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: The `test_ship_route_exit_classifies_driver_sidecars` matrix does not exercise invariant assessment or violation reasons, so sidecar classification can drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_11: CLI port tests do not pin the invariant verb surface
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: The CLI port tests only pin the architectural-invariants read, leaving the rest of the invariant verb surface free to drift from `_REGISTRY`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_12: audit-runs tests do not cover invariant handlers
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: The new invariant scan handlers in `python/tests/issue/test_audit_runs.py` lack pytest coverage, so malformed or missing invariant artifacts can slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_13: harness scripts lack invariant pins
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: The plan-required invariant harness extensions are still missing from `skills/implement/scripts/test-architectural-guidelines-step.sh` and `scripts/test-design-structure.sh`, leaving invariant pins unverified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


