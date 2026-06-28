## Goal
Implement issue #5675: [IMPLEMENTING] [BUG] Architectural-guideline note dropped on HEAD drift on ~87% of runs.

## Implementation Plan
## Plan

## Approach

- Treat `approach-synthesis.txt` as `NO_SKETCHES`.
- Make the minimum Python change:
  - Keep `pin_note_from_staged()` strict by default.
  - Add a separate refresh helper for the Phase-B drift case.
  - Have `ship.py` retry the pin once after refreshing staged metadata from the live diff.
- Do not add prompt-side LLM assessment to Python.
- Do not relax fingerprint validation when the live diff cannot be materialized.

## Files to modify/create

### UPDATED: python/larch/core/architectural_guidelines.py

- Add a small internal helper that materializes the live implementation diff and returns both:
  - diff text
  - fingerprint
- Reuse `materialize_implementation_diff()` and `diff_fingerprint()`.
- Add a public library helper, for example `refresh_staged_assessment_for_current_head(...) -> bool`.
- Helper contract:
  - Require regular non-symlink staged assessment and sidecar files.
  - Require `STATUS=present`.
  - Resolve `base_ref` from the caller or staged metadata.
  - Require `repo_root`, `head_sha`, and a materializable live diff.
  - Read the existing staged assessment body.
  - Rewrite staged artifacts with `write_staged_assessment(...)`.
  - Store the current live diff snapshot and fingerprint.
  - Store `ASSESSED_HEAD_SHA=head_sha`.
  - Return `False` on missing artifacts, invalid metadata, live diff failure, or I/O failure.
- Keep `pin_note_from_staged()` behavior unchanged.
- Keep `_staged_fingerprint_valid()` fail-closed when the live diff and snapshot cannot validate.

### UPDATED: python/larch/implement/ship.py

- Update `_pin_and_load_guidelines_note()` only.
- Current flow:
  - Try `pin_note_from_staged(...)`.
  - On failure, log and fall through to drop notice handling.
- New flow:
  - Try `pin_note_from_staged(...)`.
  - If it fails and staged artifacts exist, call the new refresh helper with:
    - `tmpdir`
    - `head_sha`
    - `base_ref`
    - `repo_root`
  - If refresh succeeds, retry `pin_note_from_staged(...)` once.
  - Only log the existing skip warning when both the first pin and retry fail.
  - Do not persist a drop notice after a successful retry.
- Keep existing behavior when:
  - `repo_root` is missing.
  - live diff materialization fails.
  - staged artifacts are absent.
  - refresh writes fail.
  - durable note redaction fails.

### UPDATED: python/test_architectural_guidelines.py

- Add unit coverage for the new refresh helper:
  - Refresh succeeds when staged metadata has the old fingerprint and the live diff has a new fingerprint.
  - The staged diff snapshot is rewritten to the live diff.
  - The staged sidecar has the new `DIFF_FINGERPRINT`.
  - The staged sidecar has the current `ASSESSED_HEAD_SHA`.
  - A subsequent `pin_note_from_staged(..., repo_root=repo)` succeeds.
- Add failure coverage:
  - missing staged artifacts returns `False`.
  - live diff materialization failure returns `False`.
  - missing or empty resolved base returns `False`.
- Keep existing strict mismatch tests unchanged.

### UPDATED: python/test_ship.py

- Keep the existing mismatch test that lacks `repo_root`; it should still return the drop notice.
- Add a drift recovery test:
  - Write staged assessment with old diff fingerprint and old diff snapshot.
  - Monkeypatch or fixture the live diff to a different current diff.
  - Call `_pin_and_load_guidelines_note(..., repo_root=repo)`.
  - Assert the returned note is the staged note, not the drop notice.
  - Assert the durable note is consumable for `head_sha`.
  - Assert no dropped-note artifact remains.
  - Assert durable metadata carries the refreshed fingerprint.
- Add a retry-failure test only if the implementation needs a distinct branch:
  - refresh returns `False`.
  - existing drop notice path and warning still happen.

## Edge cases

- **Log-only HEAD bumps:** the live diff should still match or refresh safely because `larch-logs/**` stays excluded.
- **Fast-moving base branch:** refresh uses the current merge-base diff, so context-only diff fingerprint changes no longer drop the note.
- **No repo root:** keep the old fail-closed behavior.
- **Bad remote/base ref:** do not pin stale content.
- **Symlinked artifacts:** keep regular-file checks and fail closed.
- **Existing dropped notice:** successful refresh and pin should clear it through `write_implement_note()`.

## Failure modes

- Live diff materialization may fail because the base ref is unavailable.
  - Return `False`.
  - Let existing warning and drop-notice behavior run.
- Refresh may fail because artifacts are missing or unreadable.
  - Return `False`.
  - Do not mask the failure.
- A true semantic change after staging may still need prompt-side reassessment.
  - Do not try to solve semantic reassessment in Python.
  - Preserve the existing prompt-side Phase A ownership.

## Testing strategy

- Run targeted tests:
  - `python3 -m pytest python/test_architectural_guidelines.py python/test_ship.py`
- Run targeted lint on changed Python files:
  - `python3 -m ruff check python/larch/core/architectural_guidelines.py python/larch/implement/ship.py python/test_architectural_guidelines.py python/test_ship.py`
- If available in the local workflow, run the repository Python lint target for changed files only.

## Acceptance

- Run targeted tests:
  - `python3 -m pytest python/test_architectural_guidelines.py python/test_ship.py`
- Run targeted lint on changed Python files:
  - `python3 -m ruff check python/larch/core/architectural_guidelines.py python/larch/implement/ship.py python/test_architectural_guidelines.py python/test_ship.py`
- If available in the local workflow, run the repository Python lint target for changed files only.

diff_added: 120
diff_deleted: 25
mechanical_churn: false
diff_lines: 145

## Test plan
(no test plan section in plan-file)
