### FINDING_1: Normal dispatch reships without provenance validation
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Cursor-Requirements, Codex-dyn-Salvage Provenance Auditor
- **Severity**: major
- **Concern**: The normal launcher-exit dispatch branch can reship a changed HEAD without validating ancestry and the exact lane-step trailer, allowing subject-only, malformed, duplicate, mismatched, unrelated, or multi-commit heads to bypass provenance checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Validate every normal reship-capable HEAD change, or route unvalidated commits to LaneClosedError/operator-bail; add corresponding tests
  - From Codex-Innovation: Validate every normal reship candidate with the shared provenance validator, and test this branch 1. [security] `python/larch/implement/ci_fixer_lane.py:509-510`: The detailed plan validates only the uncommitted-edit salvage path. The direct `final_head != starting_head` path still authorizes reship without the required trailer. Route it through the shared validator or bail closed.
  - From Cursor-Requirements: In the ci_fixer_lane.py plan bullet, state that the launcher_exit == 0 and committed_head is not None branch must call the shared validator on committed_head before emitting fixer-produced-uncommitted-change, and raise LaneClosedError when validation fails
  - From Codex-dyn-Salvage Provenance Auditor: Apply the shared validator before this reship return, and raise LaneClosedError on any provenance or ancestry failure


### FINDING_2: Step 8 shell harness is missing required salvage trailers
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The crashed-salvage shell fixture creates a subject-only commit and expects reship, so lane-bound trailer validation will make the existing integration harness fail unless the fixture is updated and the subject-only bail path is covered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add ### UPDATED: skills/implement/scripts/test-step-8-ci-fixer.sh: write Larch-Salvage-Step: $FINALIZE_STEP into the salvage commit body and add a subject-only negative fixture asserting crashed-lane-head-unverified
  - From Cursor-Pragmatic: Add ### UPDATED: skills/implement/scripts/test-step-8-ci-fixer.sh: write Larch-Salvage-Step: $FINALIZE_STEP into the salvage commit body in crashed-salvage and assert subject-only commits bail; keep python/tests/implement/test_ci.py updates as planned ### Finding 1 (risk-integration) **Location:** `skills/implement/scripts/test-step-8-ci-fixer.sh:199-207` **Concern:** The plan updates `python/tests/implement/test_ci.py` but omits the existing Bash finalize harness. The `crashed-salvage` case still creates a subject-only commit (`git commit -m 'Apply CI fixer working-tree edits (codex)'`) and asserts `RESULT=reship` / `REASON=crashed-lane-salvage-commit`. Once `_validated_salvage_head` requires an exact `Larch-Salvage-Step` trailer, that fixture will fail closed as `crashed-lane-head-unverified`. **Suggested revision:** Add `### UPDATED: skills/implement/scripts/test-step-8-ci-fixer.sh` to the firm file list. In `crashed-salvage`, include `Larch-Salvage-Step: $FINALIZE_STEP` in the commit message (the fixture already computes `FINALIZE_STEP`). Optionally add a sibling case that proves subject-only commits still bail. Mention running this harness in the testing strategy alongside `python/tests/implement/test_ci.py`.
  - From Cursor-Requirements: Add ### UPDATED: skills/implement/scripts/test-step-8-ci-fixer.sh: write the expected trailer into the crashed-salvage commit (use FINALIZE_STEP), add a subject-only negative fixture expecting crashed-lane-head-unverified, and list bash skills/implement/scripts/test-step-8-ci-fixer.sh in Testing strategy


### FINDING_4: Normal dispatch provenance failures lack regression coverage
- **Reviewer(s)**: Cursor-Innovation, Codex-Requirements, Cursor-dyn-Salvage Provenance Auditor
- **Severity**: minor
- **Concern**: Tests do not require the normal dispatch path to bail after a salvage commit fails provenance verification, so an implementation could still reship an unverified commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add a dispatch test where salvage commits then validator rejection yields operator-bail (not reship) and leaves the commit for inspection
  - From Codex-Requirements: Add one test that forces `_validated_salvage_head` to fail after the salvage commit and asserts `LaneClosedError`, no `reship`, and preservation of the commit for inspection
  - From Cursor-dyn-Salvage Provenance Auditor: Add a test that commits salvage delta then forces provenance verification failure and asserts `LaneClosedError` (or operator-bail) with no `reship` and no lineage/rounds advance


### FINDING_5: Wrong and duplicate trailer cases should be mandatory
- **Reviewer(s)**: Cursor-dyn-Salvage Provenance Auditor
- **Severity**: minor
- **Concern**: Wrong-step and duplicate `Larch-Salvage-Step` rejection tests are described as optional, allowing core provenance rejection paths to ship without regression coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Salvage Provenance Auditor: Mandate parametrized tests for wrong-step and duplicate `Larch-Salvage-Step` trailers on both crash finalize and normal salvage dispatch (not conditional)


### FINDING_2: Normal dispatch lacks subject-only provenance regression coverage
- **Reviewer(s)**: Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: Normal direct-HEAD dispatch, and its related salvage path, lack a mandatory regression test proving that a subject-only commit without the `Larch-Salvage-Step` trailer fails closed. The primary `fixer-produced-change` reship bypass could therefore regress while crash-finalize coverage still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add subject-only cases to the normal-dispatch matrix for both direct-HEAD and uncommitted-salvage paths; assert no reship and preserved offending commit
  - From Cursor-Pragmatic: Add a dispatch test (or extend the parametrized matrix with a `missing-trailer` case on the direct-HEAD-change path) where the launcher commits `Apply CI fixer working-tree edits ({tier})` with no `Larch-Salvage-Step` trailer; assert fail-closed with no `reship` and no rounds/lineage advance.
  - From Cursor-Requirements: Add an explicit `_dispatch` negative test where a committing launcher advances `HEAD` with the expected subject but no trailer; assert `LaneClosedError` (or `operator-bail` if exercised through `main()`), no `reship`, and no rounds/lineage advance.


