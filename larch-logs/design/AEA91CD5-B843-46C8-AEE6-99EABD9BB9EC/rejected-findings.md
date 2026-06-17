### [Plan Review] FINDING_1

### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/agents.py:896-912; scripts/lib-external-launcher-common.sh:182-226; plan.txt:31-33
- **Concern**: [SCOPE-REDUCTION] The plan infers health-gate mode from LARCH_EXTERNAL_AUTH_RETRIES=1, coupling the new transient retry budget back to the auth retry knob.. Scenario: A normal agent check-reviewers or Step 0 run with LARCH_EXTERNAL_AUTH_RETRIES=1 and no explicit LARCH_PROBE_RETRIES still treats the first rc==1 as final, so the bug remains for that configuration despite the approved separate default retry budget.
- **Proposed resolution**: Keep LARCH_PROBE_RETRIES independent in check_reviewers: default unset to 2, and disable transient retries only when LARCH_PROBE_RETRIES=0 is explicit. Remove the implicit max_auth_retries == 1 suppression and its companion docs/tests, or handle launch-health one-shot with an explicit caller opt-out in a separately scoped change.

