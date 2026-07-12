### FINDING_1:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/ship.py:467-497,544-564
- **Concern**: Ship gate clears outcome sidecars before unavailable detail can be read. Scenario: The plan adds a ship_guidelines reader for validated unavailable detail from outcome sidecars and says ship.py should preserve detail during refresh, but `_invariants_gate_before_pr` and `_guidelines_gate_before_pr` still call `clear_*_ship_outcome_sidecar` before `load_or_prepare_*`. Any diagnostic written by `_persist_unavailable` is deleted before the reader runs, so refreshed outcomes and `ASSESSMENT_UNAVAILABLE_DETAIL` can stay empty on the BD267D84 path.
- **Proposed resolution**: In `_invariants_gate_before_pr` and `_guidelines_gate_before_pr`, snapshot validated unavailable detail from the existing outcome sidecar (matching live `head_sha`/`base_ref`, `reason=unavailable`) before `clear_*_ship_outcome_sidecar`, then inject that detail into the gate result passed to `write_*_ship_outcome`.
