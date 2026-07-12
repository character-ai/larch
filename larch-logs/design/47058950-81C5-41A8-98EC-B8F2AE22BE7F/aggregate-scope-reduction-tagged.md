### FINDING_2:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: architecture
- **Location**: skills/implement/scripts/step-8-assessment.sh:663-728
- **Concern**: [SCOPE-REDUCTION] `ASSESSMENT_CHILD_DETAIL` stderr pipeline is disconnected from operator-bail. Scenario: The reported failure is coordinator `status=ok` with `kind:unavailable`; `_persist_unavailable` already receives launcher/parse errors such as empty stdout. Operator-bail is built from `ship route-exit` (`ASSESSMENT_UNAVAILABLE_DETAIL` from outcome sidecars), not assessment merge/terminal KVs. Child stderr capture, sanitization, merge forwarding, and harness cases for `ASSESSMENT_CHILD_DETAIL` add secret/cleanup risk without fixing the missing diagnostic unless separately wired.
- **Proposed resolution**: Limit Step 8 adapter changes to fail-closed behavior already required; propagate diagnostics only through `_persist_unavailable` outcome `detail` plus `dispatch_ship.py` `ASSESSMENT_UNAVAILABLE_DETAIL`. Drop `ASSESSMENT_CHILD_DETAIL` merge/terminal forwarding and its dedicated harness surface unless a concrete operator-bail consumer is added.
