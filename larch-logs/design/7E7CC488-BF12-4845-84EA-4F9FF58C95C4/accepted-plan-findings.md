### FINDING_1: Re-author-required is not integrated into the Step 8 terminal state machine
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: major
- **Concern**: The plan adds or recognizes per-kind `re-author-required` results but does not consistently define the terminal status, coverage rules, adapter handoff, and parent-orchestrator branch. `run_child` may still stamp `ASSESSMENT_STATUS=complete`, while `terminal_is_success`, `validate_results_coverage`, `SKILL.md`, and the ship exit matrix still accept only complete success. A valid re-author result could therefore be treated as success, retried automatically, or fail-closed as tool failure instead of routing to bounded operator reassessment without ship relaunch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Teach run_child and terminal handlers to detect re-author-required tokens, emit a non-complete terminal status (for example ASSESSMENT_STATUS=re-author-required), and keep them out of success coverage; update skills/implement/SKILL.md, skills/implement/references/ship-pr-exit-matrix.md, and the architectural present references so that status routes to operator reassessment without ship relaunch or automatic retry
  - From Cursor-Innovation: Add `### UPDATED:` entries for `skills/implement/SKILL.md`, `skills/implement/references/ship-pr-exit-matrix.md`, and `skills/implement/scripts/step-8-assessment.md`. Define a non-complete terminal `ASSESSMENT_STATUS` (for example `re-author-required`), extend `validate_results_coverage` and `handle_terminal_outcome`/`terminal_is_success`, and branch the assessments path to operator-visible reassessment without treating it as ship-complete or generic tool-failure. Keep the existing no-auto-retry rule by requiring failed-attempt cleanup or non-consumable legacy notes before a fresh adapter run.
  - From Codex-Innovation: Add an explicit re-author terminal predicate and result-env contract. Route that predicate to the existing `NEXT_ACTION=assessments` handoff without retrying the malformed assessment
  - From Cursor-Pragmatic: Spell out in `step-8-assessment.sh` changes a new ASSESSMENT_STATUS value, a dedicated HANDLE_ACTION, child merge rules that forbid ASSESSMENT_STATUS=complete when any kind is re-author-required, and harness assertions that attempt 2 is not used for that terminal class
  - From Cursor-Requirements: Add `### UPDATED:` entries for `skills/implement/SKILL.md`, `skills/implement/references/ship-pr-exit-matrix.md`, and the architectural present-reference docs. Define a terminal adapter status such as `ASSESSMENT_STATUS=re-author-required`, require `BGJOB_RC=0`, preserve per-kind `ASSESSMENT_RESULTS`, forbid automatic bgjob retry of the same malformed assessment, and route the main agent to reassessment/user input rather than `step-8-ship.sh`.
  - From Codex-Requirements: Add `skills/implement/SKILL.md` as an updated file and define the caller branch for validated `re-author-required`: preserve its kind and reason, do not treat it as completed coverage, and route to the specified reassessment or user-input action without relaunching ship. Update `skills/implement/scripts/step-8-assessment.md` if its normative result grammar changes.


### FINDING_2: Legacy notes without valid assessment metadata can still crash instead of requesting re-authoring
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: Legacy prose-only or malformed durable notes can still be treated as current and enter `_repair_current_outcome`, where missing, invalid, or cross-vocabulary `ASSESSMENT_KIND` raises `ValueError`. The coordinator then reports `ARCHITECTURAL_ASSESSMENT_STATUS=failed`, causing retry or fail-closed handling instead of a bounded per-kind `re-author-required` result.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In repair and current-note paths, treat missing, invalid, or cross-vocabulary ASSESSMENT_KIND as per-kind re-author-required with bounded reason; do not let ValueError escape as coordinator failed status
  - From Cursor-Innovation: In `_compose_precheck_result` and `_invariant_compose_precheck_result`, require authored durable metadata to carry a kind-valid `ASSESSMENT_KIND` before returning `current`; otherwise continue to `assessment-required`. Update `_repair_current_outcome` to return bounded `re-author-required` (or force reassessment) rather than raising, and add coordinator/compose-precheck tests for legacy prose-only notes.
  - From Cursor-Pragmatic: Treat missing, empty, invalid, or cross-vocabulary `ASSESSMENT_KIND` in prepare/current/repair as per-kind `re-author-required`. Update `_compose_precheck_result` or `note_consumable`, stop raising from `_repair_current_outcome` for that case, and add coordinator tests for legacy metadata.
  - From Cursor-Requirements: In `architectural_assessment.py`, name `_repair_current_outcome` explicitly: return per-kind `re-author-required` (or route through the dedicated exception path) when repair metadata is missing, invalid, or cross-vocabulary; do not let `ValueError` bubble to coordinator failure. Add coordinator coverage in `test_architectural_assessment.py` for legacy metadata on the evidence-none repair path.


### FINDING_3: Retained staged/compose wrappers make the outcome mandatory before shared validation
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: The wrapper contract makes the second positional outcome required, so an omitted outcome exits in the shell before the shared Python writer can emit the distinct `re-author-required` result required by the core contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Make the outcome positional argument optional with an empty default, forward it as `--outcome`, and let the shared writer validation emit the distinct re-author-required exit. Apply the same contract to every retained wrapper.


### FINDING_6: Unavailable-note preservation still relies on prose classification
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: `write_unavailable_note` can still preserve or infer an authored invariant violation through `_invariant_assessment_kind(existing_note)`, allowing legacy prose or clean-shaped text to influence ship routing when assessment tooling is unavailable. This violates the requirement that durable explicit metadata, not prose, determine the outcome.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add an explicit `architectural_guidelines.py` change for `write_unavailable_note`: preserve an existing authored invariant violation only when current durable metadata has `ASSESSMENT_KIND=violation` (and the existing sidecar/pin contract matches). Remove the prose classifier fallback and extend `test_architectural_guidelines.py` unavailable-preservation coverage accordingly.

