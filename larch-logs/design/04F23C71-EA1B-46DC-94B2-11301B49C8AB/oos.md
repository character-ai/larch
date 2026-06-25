### FINDING_3: Missing ship test for persist-false with readable drop marker
- **Reviewer(s)**: Cursor-Arch
- **Severity**: latent
- **Concern**: No test covers ship returning PR drop text when `maybe_persist` is write-onced out but `DROPPED_NOTE_ARTIFACT` remains readable. Planned tests cover pin-failure persist, compose-then-invalidate integration, and `clear_dropped_note_notice` unlink failure on `write_implement_note`, but not `_pin_and_load_guidelines_note` after successful pin plus failed marker clear plus `note_fingerprint_stale` where `maybe_persist` returns False yet the artifact is readable. Green tests can miss the PR-body regression in FINDING_1.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a ship test: pre-seed DROPPED_NOTE_ARTIFACT, pin consumable note, force note_fingerprint_stale, mock maybe_persist to return False (or rely on write-once), assert _pin_and_load_guidelines_note returns the drop notice text for compose_pr_body.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected (latent-rerouted)

### OOS_1: Persist-failure path still leaves the final report silent despite acceptance wording asking for a visible explanation when a current-HEAD note cannot be delivered
- **Description**: Persist-failure path still leaves the final report silent despite acceptance wording asking for a visible explanation when a current-HEAD note cannot be delivered. Scenario: The plan documents fail-open behavior (edge case line 204): when `persist_dropped_note_notice` fails, callers return `""` and only log warnings. That matches round-4 accepted fail-open intent but not the literal acceptance criterion for infra failures (read-only/full tmpdir).
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: summary-final.md
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

