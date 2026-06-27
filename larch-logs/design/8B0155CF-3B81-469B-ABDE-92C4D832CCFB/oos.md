### OOS_1: Closeout step-16 pin path lacks the same refresh retry
- **Description**: Closeout step-16 pin path lacks the same refresh retry. Scenario: _pin_architectural_guidelines_note_best_effort calls pin_note_from_staged directly before final report. Runs that still have staged artifacts at Step 16 but never got a successful ship-time refresh would remain on the drop path even if the library helper exists only in ship.py
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/state/closeout.py:213-228
- **Phase**: design

Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected

