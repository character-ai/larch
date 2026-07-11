### FINDING_1: Explicit-outcome mismatches are incorrectly persisted as unavailable
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Requirements, Cursor-dyn-Ship Gate Auditor, Codex-dyn-Ship Gate Auditor
- **Severity**: major
- **Concern**: The coordinator’s broad persistence-error handler can convert missing, invalid, mismatched, or post-write-inconsistent explicit outcomes into `_persist_unavailable`. That produces an unavailable/dropped artifact which downstream logic may treat as terminal coverage, allowing a clean-claim mismatch or other re-author condition to bypass the required fail-closed path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Introduce a dedicated ReAuthorRequired (or config exit) in _persist_result: on mismatch call neither write_compose_assessment nor _persist_unavailable; emit a distinct per-kind status (e.g. re-author-required) or fail the run without durable artifacts; add test_architectural_assessment.py coverage that mismatch never produces unavailable sidecars
  - From Cursor-Innovation: Define a coordinator per-kind status such as re-author that must not be treated as complete success; keep it out of the success allowlist (or fail child rc) so attempt-1 retries; forbid mapping mismatch to unavailable; add coverage in python/tests/implement/test_architectural_assessment.py and skills/implement/scripts/test-step-8-assessment.sh
  - From Codex-Innovation: Define a dedicated re-author exception or status for outcome validation failures, handle it before the generic unavailable path, clear any authored artifacts, and return the documented re-author result through the Step 8 adapter and caller.
  - From Cursor-Requirements: Introduce a dedicated re-author exception/result (distinct config exit + status grammar), skip _persist_unavailable, leave no consumable durable note/outcome sidecar, and return non-ok coordinator output that fail-closes Step 8 rather than `kind:unavailable`
  - From Cursor-dyn-Ship Gate Auditor: Add a dedicated re-author exception/status, validate outcome/note consistency before any durable note or sidecar write, and catch re-author failures before the generic except that calls _persist_unavailable
  - From Codex-dyn-Ship Gate Auditor: Handle the explicit-outcome or consistency failure separately in `run`: clear authored and outcome artifacts, preserve the distinct re-author status, and return a status that the ship coordinator maps to `needs_assessment`; reserve `_persist_unavailable` for genuine unavailable results


### FINDING_2: Step 8 does not define or preserve the re-author result
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Ship Gate Auditor, Codex-dyn-Ship Gate Auditor
- **Severity**: major
- **Concern**: The Step 8 adapter’s result allow-list and nonzero-exit handling do not specify how a coordinator-level re-author result is represented or routed. A new status may be rejected as malformed coverage or collapsed into generic retry/fail-closed behavior, while mapping it to unavailable incorrectly treats reassessment as completed coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add re-author-required (or chosen token) to validate_results_coverage and document ship routing: treat it like needs_assessment (NEEDS_USER_INPUT reassessment), not unavailable/dropped; update test-step-8-assessment.sh if stub results change
  - From Cursor-Innovation: Define a coordinator per-kind status such as re-author that must not be treated as complete success; keep it out of the success allowlist (or fail child rc) so attempt-1 retries; forbid mapping mismatch to unavailable; add coverage in python/tests/implement/test_architectural_assessment.py and skills/implement/scripts/test-step-8-assessment.sh
  - From Cursor-Pragmatic: Spell out Piece 2 terminal semantics: either bounded in-coordinator retry before emitting final `ARCHITECTURAL_ASSESSMENT_RESULTS`, or add an allowed result token plus `test-step-8-assessment.sh` retry/fail-closed coverage in `### UPDATED: skills/implement/scripts/step-8-assessment.sh` and its harness.
  - From Codex-Pragmatic: Add `step-8-assessment.sh` and its existing harness to the plan. Recognize and propagate the coordinator's re-author result without converting it to generic failure, while retaining fail-closed behavior.
  - From Cursor-Requirements: Introduce a dedicated re-author exception/result (distinct config exit + status grammar), skip _persist_unavailable, leave no consumable durable note/outcome sidecar, and return non-ok coordinator output that fail-closes Step 8 rather than `kind:unavailable`
  - From Codex-Requirements: Add firm updates to step-8-assessment.sh, its contract, and focused harness. Preserve the distinct coordinator exit or status through child parsing and terminal KVs, then route it as re-author-required instead of generic failure or unavailable.
  - From Cursor-dyn-Ship Gate Auditor: Either document that mismatch must fail architectural-assessment run without a consumable kind status, or add an explicit allowed status plus adapter/ship routing to NEXT_ACTION=assessments for re-author
  - From Codex-dyn-Ship Gate Auditor: Handle the explicit-outcome or consistency failure separately in `run`: clear authored and outcome artifacts, preserve the distinct re-author status, and return a status that the ship coordinator maps to `needs_assessment`; reserve `_persist_unavailable` for genuine unavailable results


### FINDING_3: Authored notes without valid ASSESSMENT_KIND can bypass reassessment or misroute ship
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Ship Gate Auditor
- **Severity**: major
- **Concern**: Present authored notes with missing, invalid, or empty persisted `ASSESSMENT_KIND` are not consistently rejected before handled-coverage checks, present-note short-circuits, or outcome classification. Once prose fallback is removed, legacy or malformed notes can be treated as clean, pinned, violation, or otherwise consumable instead of requesting re-authoring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In _read_current_* (or immediately after), when NOTE_STATE is authored and ASSESSMENT_KIND is missing or not in the kind vocabulary, invalidate the durable note or return needs_assessment=True with a re-author detail; add regression tests in python/tests/implement/test_ship.py
  - From Codex-Innovation: Validate the persisted outcome while reading each present authored note. Return a re-author-required result for missing, invalid, or cross-vocabulary values, while preserving the existing system-derived exceptions for deterministic-clean, unavailable, absent, invalid, and invariant-empty states.
  - From Cursor-Pragmatic: Extend the plan’s `architectural_assessment.py` work (and matching tests) so authored notes require a valid persisted outcome before `_already_handled` returns true; otherwise leave the kind pending for reassessment.
  - From Cursor-Requirements: In `_read_current_guidelines_note` / `_read_current_invariant_note` (and before `_classify_*`), when `NOTE_STATE` is authored and persisted `ASSESSMENT_KIND` is missing or not in the vocabulary, return `needs_assessment=True` with a bounded re-author detail; do not call `_classify_*` on that path
  - From Cursor-dyn-Ship Gate Auditor: On NOTE_STATE authored, require ASSESSMENT_KIND in the vocabulary; if missing/invalid set needs_assessment=True on the gate result and add tests that missing metadata cannot reach PR compose with a clean gate


### FINDING_6: Unavailable handling still derives violation preservation from prose
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: `write_unavailable_note` uses prose classification to decide whether an existing invariant violation should be preserved. That retains prose as routing authority and can either overwrite an authored violation with unavailable or preserve a legacy prose-only violation without valid metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Switch preservation to metadata ASSESSMENT_KIND==violation (shared classifier only as optional cross-check); add a small test that unavailable does not clobber an authored violation note with explicit metadata
  - From Cursor-Requirements: Replace the prose check with persisted `ASSESSMENT_KIND=="violation"` and/or a matching violation outcome sidecar; if neither is present on an authored note, fail closed to re-author instead of inferring from note text


### FINDING_7: The explicit-outcome CLI, wrapper, staged-writer, and test-call contracts are incomplete
- **Reviewer(s)**: Codex-Arch, Cursor-Arch, Cursor-Requirements, Cursor-Pragmatic
- **Severity**: major
- **Concern**: The plan does not fully define how explicit outcomes reach all writer entry points and callers. Making `--outcome` argparse-required conflicts with the required distinct re-author response for omitted values; wrapper argv contracts are unspecified; staged refresh/pin paths and final-report tests are omitted from the affected surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Do not make `--outcome` an argparse-required argument. Parse it with an empty default, then validate missing, invalid, and mismatched values in the shared writer path and return the distinct re-author exit code for all four write verbs.
  - From Cursor-Arch: Add python/tests/report/test_final_report.py to Files to modify/create and pass an explicit outcome (likely clean) on each write_staged_assessment call; include pytest python/tests/report/test_final_report.py in Testing strategy
  - From Cursor-Requirements: Extend staged writers to require explicit outcome, thread sidecar `ASSESSMENT_KIND` through refresh, and fail closed in pin paths when authored staged metadata lacks a valid explicit outcome (no prose inference)
  - From Cursor-Pragmatic: Define wrapper input explicitly (for example required second positional `clean|deviation|violation` forwarded as `--outcome`, or a documented env var) in both compose shell scripts and `test-architectural-guidelines-step.sh`.


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

