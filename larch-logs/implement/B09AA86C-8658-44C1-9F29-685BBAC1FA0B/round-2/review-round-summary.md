# Review Round 2

- Mode: `diff`
- 9 accepted, 2 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Shipped seeded guidelines do not match issue/plan register
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-generic-output.txt
- **Severity**: important
- **Concern**: `ARCHITECTURAL_GUIDELINES.md` ships a different guideline set (IDs, goals, count) than the issue/plan G-Py/G-Skill/G-Enf seeded register. Acceptance requires the agreed seed; operators get a different architectural advisory surface than designed and reviewed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Restore plan/issue seeded entries or update plan/issue explicitly
  - From cursor-specialist-edge-cases-output.txt: Replace file content with plan seed entries or update issue/plan if the generic set was intentional.
  - From codex-generic-output.txt: Replace the root file contents with the settled seeded guideline set from the feature description, preserving only the short aspirational opening note and the required schema.


### FINDING_2: Fingerprint validation skipped or incomplete at pin time
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-dyn-note-safety-output.txt
- **Severity**: important
- **Concern**: Fresh pin paths can publish a staged assessment without verifying it still matches the live implementation diff. `_pin_and_load_guidelines_note()` skips `note_fingerprint_stale()` when `pinned_now=True`, and `pin_note_from_staged()` does not verify `DIFF_FINGERPRINT` against the materialized diff snapshot. If merge-base or diff drifts while `HEAD_SHA` is unchanged, PR/final summaries may show false “no deviations” attestations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Verify staged DIFF_FINGERPRINT against live diff on every pin; invalidate on mismatch
  - From cursor-specialist-edge-cases-output.txt: Recompute fingerprint from MATERIALIZED_DIFF at pin time; fail closed on mismatch.
  - From dyn-dyn-note-safety-output.txt: Run fingerprint validation after every successful pin (or before returning note text), and reject or invalidate when `note_fingerprint_stale()` is true even when `pinned_now=True`.


### FINDING_3: Silent drop when guideline note redaction truncates
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: When redaction truncates a long architectural-guidelines note, the deviation text can appear in Phase A chat but disappear from the PR body and final summary with no operator-visible warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Log truncation warning; align with redact_pr_body fail-closed path


### FINDING_4: Missing plan-required ship integration tests for pin/compose/invalidate paths
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan acceptance calls for ship integration tests covering pin-before-compose (fresh and open-pr), CI-fix invalidation, and consumable notes reaching `compose_pr_body`. Only helper unit tests exist today; regressions in `ship.py` ordering or invalidation could omit guideline sections from PR bodies and final summaries without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add run_ship tests asserting compose_pr_body receives architectural_guidelines_note
  - From cursor-specialist-testing-output.txt: Add ship integration tests spying on _pin_and_load_guidelines_note, _invalidate_guidelines_note, and compose_pr_body for fresh pr-create, open-pr resume, and monitor.did_fixing paths.


### FINDING_8: Pin/invalidate/read failures swallowed in ship driver
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-dyn-note-safety-output.txt
- **Severity**: important
- **Concern**: `_invalidate_guidelines_note()` and `_pin_and_load_guidelines_note()` wrap invalidate, pin, and read operations in broad `suppress(Exception)`. Artifact deletion or note read failures after CI-fix or conflict commits can leave stale staged or durable notes that still pass `note_consumable()` when `HEAD_SHA` matches, while PR compose omits `## Architectural guidelines` with no ship-driver warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Log pin/read/redact failures to execution-issues or emit explicit PIN_STATUS=failed; narrow suppress scope.
  - From dyn-dyn-note-safety-output.txt: Log invalidate/read failures to `execution-issues.md` (or fail closed for note surfacing), and treat any failed invalidate as “no consumable note” rather than swallowing the error.


### FINDING_11: Git diff failure incorrectly treated as fingerprint stale
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `note_fingerprint_stale()` treats git diff failures as stale and invalidates the note. Open-pr resume with a missing remote ref can drop a valid guideline section from the PR body.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Treat diff-unavailable separately from fingerprint mismatch; warn without invalidating when git fails.


### FINDING_12: Parser leaks bullets from non-`G-*` headings into prior entry
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: The parser keeps collecting `Why:` / `Deviate when:` bullets after a non-`G-*` heading, so prose under a non-entry heading can be emitted inside the previous guideline block. That violates the parsed-entry-only trust boundary for normalized untrusted output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: End the current entry when any new markdown heading is encountered; only collect bullets while the active heading is a matched `### G-...` entry, and add a test that non-`G-*` heading bullets are omitted.


### FINDING_14: `final_report` omits fingerprint staleness check
- **Reviewer(s)**: dyn-dyn-note-safety-output.txt
- **Severity**: important
- **Concern**: `_architectural_guidelines_section()` gates only on `note_consumable(head_sha)` and never calls `note_fingerprint_stale()`. Committed `final-summary.md` can include guideline attestations that the ship path would drop on merge-base drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-note-safety-output.txt: Mirror the ship fingerprint check in `_architectural_guidelines_section()` (invalidate and return `""` when stale).


### FINDING_16: Step 16 pin-note invocation is prose-only in SKILL.md
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Step 16 `pin-note-from-staged` is prose-only with no bash fence unlike the Phase A trio. The orchestrator may skip pin before step-16-17, and the final summary omits guidelines despite a staged assessment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add one-line larch-run.sh fence and extend test-implement-fence-shape.


