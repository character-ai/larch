## Goal
Implement issue #6176: [IMPLEMENTING] [OOS] Specialist payload accounting omits inlined competition notice.

## Implementation Plan
## Plan

## Approach

Make the payload counter match the renderer.

`_render_specialist_text()` inlines `competition_notice_file` only under:

- `args.competition_notice`
- `args.competition_notice_file`

Add the same gate to `_specialist_payload_bytes()`. Count raw file bytes through `_file_payload_bytes()`, matching `feature_file` and `plan_file`.

Do not count the static competition notice paragraph. It remains scaffold.

## Files to modify/create

### UPDATED: python/larch/rendering/rendering.py

In `_specialist_payload_bytes()`:

- Add `competition_notice_file` to `total` when both `args.competition_notice` and `args.competition_notice_file` are set.
- Use `_file_payload_bytes(Path(args.competition_notice_file))`.
- Keep the existing `feature_file`, `plan_file`, description text, and ledger counting unchanged.

### UPDATED: python/tests/rendering/test_rendering.py

Add a focused regression near the existing specialist payload and competition-notice tests.

Test cases:

- Render a diff specialist prompt with:
  - `--competition-notice`
  - `--competition-notice-file <notice>`
  - `--payload-bytes-output <sidecar>`
- Assert the sidecar equals `len(notice.read_bytes())`.
- Re-run with `--competition-notice-file` but without `--competition-notice`.
- Assert the sidecar returns to `0`, proving the counter matches the render gate.

Use raw byte length, not encoded rendered text length.

## Edge cases

- If the notice file is present but `--competition-notice` is false, do not count it.
- If the notice file cannot be read after parse-time validation, `_file_payload_bytes()` already fails soft to `0`.
- Non-ASCII notice text should be covered by byte-based assertions if convenient.

## Failure modes

- Counting the file whenever `--competition-notice-file` is set would inflate payload for prompts that do not inline it.
- Counting rendered wrapper bytes would diverge from the existing raw-file convention for `feature_file` and `plan_file`.
- Updating `measure-panel-cost` would be scope creep. It already consumes `payload_bytes`.

## Testing strategy

Run the changed test file only:

```bash
cd python
python -m pytest tests/rendering/test_rendering.py
```

If local lint is requested, run changed-file Python checks only:

```bash
make py-lint
```

## Acceptance

Run the changed test file only:

```bash
cd python
python -m pytest tests/rendering/test_rendering.py
```

If local lint is requested, run changed-file Python checks only:

```bash
make py-lint
```

diff_lines: 25

## Test plan
(no test plan section in plan-file)
