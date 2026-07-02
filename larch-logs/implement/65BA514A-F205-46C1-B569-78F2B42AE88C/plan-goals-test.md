## Goal
Implement issue #5969: [IMPLEMENTING] [BUG] #5675 recurrence: staged-assessment refresh returns False on fingerprint drift, so the ship-time retry never recovers and the guideline note is still dropped on ~90% of runs.

## Implementation Plan
## Plan

## Approach

Implement the approved core fix only.

- Keep `ship_guidelines.py` retry flow unchanged.
- Do not add the optional #5754 durable-note fallback.
- Do not re-run prompt-side guideline assessment.
- Carry the staged assessment text forward unchanged.
- Refresh only HEAD, base, diff snapshot, and fingerprint metadata against the current live diff.

## Files to modify/create

### UPDATED: python/larch/core/architectural_guidelines.py

In `refresh_staged_assessment_for_current_head`:

- Keep the existing fail-closed checks for:
  - missing `repo_root`
  - blank `head_sha`
  - missing staged assessment or sidecar
  - non-present sidecar status
  - missing resolved base ref
  - unresolvable repo root
  - live diff materialization failure
  - staged assessment read or rewrite failure
- Replace the current fingerprint-drift bail:
  - keep returning `False` when `DIFF_FINGERPRINT` is missing
  - stop returning `False` when the live fingerprint differs from the staged fingerprint
- After live diff materialization, read the existing staged assessment text.
- Call `write_staged_assessment` with:
  - the unchanged assessment text
  - `assessed_head_sha=head_sha`
  - `diff_fingerprint_value` set to the live diff fingerprint
  - `base_ref` set to the resolved base ref
  - `diff_text` set to the live diff text
- Return `True` after the staged snapshot is rewritten.

This makes fingerprint drift the recovery trigger instead of a permanent drop condition.

### UPDATED: python/tests/core/test_architectural_guidelines.py

Update the drift test that currently pins the wrong behavior:

- Rename `test_refresh_staged_assessment_for_current_head_returns_false_when_diff_changes`.
- Make it assert successful recovery when:
  - the staged sidecar fingerprint matches the stale staged diff
  - the live diff has a different fingerprint
  - `repo_root` and base ref are available
- Assert:
  - `refresh_staged_assessment_for_current_head(...)` returns `True`
  - the materialized diff artifact now contains the live diff
  - the staged sidecar contains the live diff fingerprint
  - the staged sidecar contains the new `ASSESSED_HEAD_SHA`
  - `pin_note_from_staged(...)` succeeds afterward
  - the durable note is consumable for the new head
- Keep the existing tests for missing artifacts, live diff failures, and missing base ref unchanged.

### UPDATED: python/tests/implement/test_ship.py

Update the ship-level drift test that currently expects a drop notice:

- Rename `test_pin_and_load_guidelines_note_returns_drop_notice_when_diff_changes_with_repo`.
- Keep its setup where the staged snapshot is stale and `materialize_implementation_diff` returns a different live diff.
- Assert `_pin_and_load_guidelines_note(...)` returns the staged note text after refresh and retry.
- Assert:
  - the durable note is consumable for the requested head
  - no dropped-note notice was persisted
  - the materialized diff artifact was refreshed to the live diff

Keep `test_pin_and_load_guidelines_note_returns_drop_notice_on_fingerprint_mismatch` unchanged. It still covers a corrupt or unrecoverable staged fingerprint path without a usable repo refresh.

## Edge cases

- Missing `DIFF_FINGERPRINT` remains unrecoverable, because the staged sidecar is corrupt or incomplete.
- Live diff materialization errors remain unrecoverable and still return `False`.
- Staged assessment text read failures remain unrecoverable.
- The assessment content is not regenerated, so the change does not introduce prompt-side reassessment or new LLM behavior.
- `pin_note_from_staged` still rejects stale staged fingerprints on the first attempt. The existing ship retry then calls the fixed refresh helper and retries pinning.

## Failure modes

- If `write_staged_assessment` fails, refresh still returns `False`, so the existing drop-notice path remains active.
- If the refreshed live diff changes again between refresh and retry pinning, `pin_note_from_staged` may still fail and ship will preserve the existing drop-notice behavior.
- If `repo_root` is absent at ship time, refresh cannot run and the current fail-closed behavior remains.

## Testing strategy

Run targeted tests for the changed surfaces:

- `python3 -m pytest python/tests/core/test_architectural_guidelines.py -k "refresh_staged_assessment_for_current_head or pin_note_from_staged"`
- `python3 -m pytest python/tests/implement/test_ship.py -k "pin_and_load_guidelines_note"`

Then run changed-file lint if local Python lint dependencies are installed:

- `python3 -m ruff check python/larch/core/architectural_guidelines.py python/tests/core/test_architectural_guidelines.py python/tests/implement/test_ship.py`

Optionally run the repo relevant-checks dispatcher after implementation:

- `python3 python/cli.py checks run-relevant`

## Acceptance

Run targeted tests for the changed surfaces:

- `python3 -m pytest python/tests/core/test_architectural_guidelines.py -k "refresh_staged_assessment_for_current_head or pin_note_from_staged"`
- `python3 -m pytest python/tests/implement/test_ship.py -k "pin_and_load_guidelines_note"`

Then run changed-file lint if local Python lint dependencies are installed:

- `python3 -m ruff check python/larch/core/architectural_guidelines.py python/tests/core/test_architectural_guidelines.py python/tests/implement/test_ship.py`

Optionally run the repo relevant-checks dispatcher after implementation:

- `python3 python/cli.py checks run-relevant`

diff_added: 22
diff_deleted: 14
mechanical_churn: false
diff_lines: 36

## Test plan
(no test plan section in plan-file)
