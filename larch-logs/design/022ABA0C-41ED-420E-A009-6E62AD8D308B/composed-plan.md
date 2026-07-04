## Plan

Approach

- Keep this as a narrow parity-test hardening change.
- Do not edit `scripts/hook-bg-poll-guard.sh` or `scripts/hook-no-progress-guard.sh`.
- Extend the existing byte-identity harness so it also compares:
  - `canonical_dir`
  - `marker_value`
  - `marker_candidates`
- Update the sibling contract doc to name all five guarded helpers.
- Leave the intentionally renamed pairs out of scope.

Files to modify/create

### UPDATED: scripts/test-hook-clone-ownership-parity.sh

Add these calls near the existing `compare_function` calls:

- `compare_function canonical_dir`
- `compare_function marker_value`
- `compare_function marker_candidates`

Keep the existing `extract_function` and `compare_function` mechanism unchanged.

### UPDATED: scripts/test-hook-clone-ownership-parity.md

Update the invariant list so it says the harness extracts and compares all five functions:

- `canonical_dir()`
- `marker_value()`
- `marker_candidates()`
- `clone_paths_same()`
- `marker_foreign_clone()`

Keep the edit-in-sync guidance. Adjust wording to say the harness fails when any guarded helper is missing or drifts.

Edge cases

- Function order differs between the two hook scripts. The existing extractor is name-based, so no change is needed.
- `marker_candidates()` includes comments. Byte comparison should keep comments in scope because they are part of the deliberately duplicated helper.
- Missing helpers should continue to fail through the existing empty extraction check.

Failure modes

- A one-sided edit to any of the three newly covered helpers should fail `make test-hook-clone-ownership-parity`.
- If a future helper is intentionally similar but renamed, this plan does not cover it. That is out of scope per the approved outline.

Testing strategy

- Run `make test-hook-clone-ownership-parity`.
- Optional manual negative check: temporarily change one of the newly guarded functions in one hook only, verify the harness fails, then revert the temporary edit before committing.
- If Markdown lint is part of the local workflow, run the scoped relevant checks for the changed `.md` and `.sh` files.

## Acceptance

See Testing strategy in plan.

review_status: ok
rounds_completed: 1
difficulty: MODERATE
diff_lines: 12
