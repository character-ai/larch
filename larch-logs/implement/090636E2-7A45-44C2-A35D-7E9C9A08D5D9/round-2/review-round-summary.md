# Review Round 2

- Mode: `diff`
- 5 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: compose-gate warning statuses should not trigger assessment loops
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-compose-gate
- **Severity**: important
- **Concern**: `load_or_prepare_guidelines_note` promotes warning-bearing compose-prep results to `needs_assessment` without checking `prepared.status`, so invalid/absent/failed prep can re-emit `architectural-guidelines-assessment` and leave stale or missing handoff artifacts in circulation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Branch on `prepared.status`; skip assessment for absent/invalid/materialization-failed; update the prepare-failure unit test
  - From cursor-specialist-correctness: Add parametrized prepare_compose_assessment tests for absent invalid and diff failure statuses
  - From cursor-specialist-testing: Retarget test to load_or_prepare_guidelines_note with warning_logged=True.
  - From codex-specialist-correctness: Only request assessment for assessment-required; log or omit for absent invalid failed materialization.
  - From codex-specialist-testing: Failed or invalid compose preparation routes to guidelines-assessment without valid handoff artifacts. Invalid guidelines or diff materialization failure can send the orchestrator to a branch that requires materialize env and diff files that were not produced Return needs_assessment only for successful assessment-required preparation; log and omit or fail closed for invalid and materialization-failure cases, and update the tests
  - From dyn-dyn-compose-gate: Branch on prepared.status before the generic warning handler. For absent and invalid, log the warning and return an empty GuidelinesGateResult (no needs_assessment). Reserve needs_assessment=True for assessment-required and for recoverable stale-note cases where rematerialization is expected to succeed.
  - From dyn-dyn-compose-gate: On non-`assessment-required` outcomes (`failed`, and ideally before returning `invalid`), clear compose handoff artifacts or mark them invalid. In `load_or_prepare_guidelines_note`, request reassessment only when `status=assessment-required`, or when a fresh materialization succeeded; for persistent `failed`, log the warning and proceed with an empty note (or stall once) instead of re-emitting `guidelines-assessment`.


### FINDING_2: moved-base run_ship regression is still missing
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-compose-gate
- **Severity**: important
- **Concern**: The current coverage still does not run `run_ship` end-to-end through the postbump rebase on a moved `origin/main`, compose-time materialization, durable note write, and PR-body compose. That leaves the original Step 8 drift failure unguarded in CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add run_ship test with real git repo postbump rebase onto moved origin/main and assert PR body gets a real assessment
  - From cursor-specialist-edge-cases: Add a git-fixture run_ship test covering postbump rebase, compose gate, durable write, and PR body note content.
  - From cursor-specialist-testing: Add run_ship integration test: moved origin/main, compose assessment write, PR body contains real note.
  - From codex-specialist-testing: Add a real run_ship regression that moves origin/main, materializes final diff, writes compose assessment, resumes pre-PR compose, and asserts the PR body contains the real note
  - From dyn-dyn-compose-gate: Add an integration test that advances origin/main, runs run_ship through postbump with real prepare_compose_assessment / write_compose_assessment, asserts Outcome.NEEDS_USER_INPUT with architectural-guidelines-assessment on first pass when needed, and asserts the composed PR body contains the authored note after relaunch.


### FINDING_3: merge-loop rebases should refresh the PR body
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: In-driver merge-loop rebases move HEAD but do not re-enter the compose gate or refresh the PR body, so the open PR can carry a stale guidelines section.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: After HEAD-changing merge-loop rebases route through _guidelines_gate_before_pr and PR body update or exit for reassessment
  - From cursor-specialist-edge-cases: Re-enter load_or_prepare_guidelines_note and ensure_pr body update after successful in-driver rebases that change HEAD.


### FINDING_4: open-PR resume stale-note reassessment is untested
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: important
- **Concern**: The open-PR resume path is still mocked in a way that does not prove stale durable-note rejection after HEAD/base movement, so reassessment routing can regress without test failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Replace fake_gate with real durable note plus HEAD or base movement and assert reassessment before compose
  - From cursor-specialist-edge-cases: Replace the mock with a fixture durable note plus base movement and assert NEEDS_USER_INPUT architectural-guidelines-assessment.
  - From cursor-specialist-testing: Run open-PR resume against real stale durable artifacts without mocking the gate.


### FINDING_5: durable note fingerprints can still be reused from an old snapshot
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-testing, codex-specialist-testing
- **Severity**: important
- **Concern**: `note_fingerprint_stale` can trust a saved snapshot instead of the live base, so a durable compose note may be reused after `origin/main` moves.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Recompute live diff fingerprint against current base before reusing a durable note.
  - From cursor-specialist-testing: Add ship_guidelines test for fingerprint-stale reassessment request.
  - From codex-specialist-testing: Recompute the live diff fingerprint or store and compare the base SHA before trusting the snapshot; add a moved-base regression with an existing compose snapshot


