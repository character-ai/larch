### FINDING_1: [OUT_OF_SCOPE] correctness: python/larch/state/admission.py still suggests `--skip-branch-check` for `/design`
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-stash-gate
- **Severity**: minor
- **Concern**: Wrong-branch preflight still tells `/design` users to recover with `--skip-branch-check`, even though that path no longer applies there, so feature-branch operators get a misleading hint instead of being told to switch to `main`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Branch the error by caller or use design-only text: switch to main; do not mention --skip-branch-check for design.
  - From cursor-specialist-edge-cases: Remove or scope the --skip-branch-check hint to /implement-only recovery surfaces
  - From cursor-specialist-testing: Split branch-failure messaging by skill or remove skip-branch-check hint for /design
  - From dyn-dyn-stash-gate: Make the branch-failure message context-aware (e.g., omit the `--skip-branch-check` hint when the caller is `/design`, or split implement-only vs shared wording) so `/design` failures only advise `git checkout main`.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_3: [OUT_OF_SCOPE] correctness: python/larch/state/admission.py drops stderr on unknown stash probe
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-stash-gate
- **Severity**: minor
- **Concern**: When `_stash_check()` returns `unknown`, the `git stash list` stderr path is not surfaced, leaving operators with only the generic unknown-stash message during git or repo failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Pre-existing; relay stderr on unknown or include it in PREFLIGHT_ERROR diagnostics.
  - From dyn-dyn-stash-gate: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_4: [OUT_OF_SCOPE] docs: docs/workflow-lifecycle.md omits the new entry gates
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-stash-gate
- **Severity**: minor
- **Concern**: The workflow-lifecycle guide still omits the empty-stash requirement and `/design`-on-`main` gate, so readers of that guide may miss the new preconditions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Update workflow-lifecycle when docs are next touched or add a cross-link to clean-main-contract
  - From cursor-specialist-testing: Add entry-gate bullets pointing to docs/clean-main-contract.md
  - From dyn-dyn-stash-gate: Add entry-gate bullets pointing to docs/clean-main-contract.md


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_5: [OUT_OF_SCOPE] risk-integration: python/tests/test_session_env.py lacks stash-failure propagation coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: `setup_main` has no test that propagates a stash failure from admission preflight, so wiring bugs between setup and preflight could slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add setup_main test where mocked preflight returns stash failure and setup propagates rc/stdout


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_6: [OUT_OF_SCOPE] correctness: stash-failure tests miss `PREFLIGHT=fail`
- **Reviewer(s)**: dyn-dyn-stash-gate
- **Severity**: minor
- **Concern**: Existing stash-failure tests cover the error text and ordering, but they do not assert `PREFLIGHT=fail`, so a future edit could drop that KV while still passing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-stash-gate: Address the concern above.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

