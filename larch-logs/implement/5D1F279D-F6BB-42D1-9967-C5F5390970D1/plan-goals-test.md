## Goal
Implement issue #6376: [IMPLEMENTING] architectural-guidelines-III Implement guideline notes: fix Tool Failures miscategorization and duplicate execution-issues writes.

## Implementation Plan
## Plan

## Approach

Add a narrow Python helper for architectural-guidelines deviation logging.

- Keep the fix on the append path, not the flush path.
- Put the helper in `python/larch/core/architectural_guidelines.py`.
- Register `architectural-guidelines append-deviation-note` in `python/larch/cli.py`.
- Update the Step 8 prompt reference to call the new helper instead of leaving category choice to the model.
- Keep non-guideline execution-issue behavior unchanged.

Implementation details:

- Add `append_deviation_note(implement_tmpdir: Path, note: str) -> str`.
- Format the Warnings entry from the note text (e.g., prefix each note line as bullet lines under `### Warnings`, matching the shape that the flush path commits).
- Redact the formatted entry using the same `_redact_batch_payload` logic from `run_log_batch` before hashing.
- Split the redacted entry with the same `_execution_issue_chunks` chunking rules as `run_log_flush`.
- Compute `structured_body_dedupe_keys` for category `Warnings` per chunk; compare against:
  1. `_existing_execution_issue_keys` parsed from the `### Warnings` body already in `execution-issues.md`.
  2. `_existing_execution_issue_keys` parsed from `larch-logs/implement/$RUN_ID/execution-issues.ndjson` when the batch file exists.
- Return `duplicate` immediately (without writing) when any chunk key already exists in either source.
- When not duplicate, append under `### Warnings` only (create section if absent); do not write `Tool Failures`.
- Reject empty or whitespace-only notes before any file I/O.
- Resolve `run_id` from `$IMPLEMENT_TMPDIR/parent-issue.md` (key `RUN_ID`) with fallback to `$IMPLEMENT_TMPDIR/session-id` file; when neither yields a valid run ID, skip the ndjson check silently and rely on the md-only dedup.
- Add `append_deviation_note_main(argv)` with:
  - `--implement-tmpdir`, defaulting to env `IMPLEMENT_TMPDIR`
  - `--note-file` for the deviation note text (file-only; no `--note-text`)
  - machine stdout `ARCHITECTURAL_GUIDELINES_APPEND_STATUS=ok|duplicate|failed`
  - exit `2` for missing tmpdir; exit `1` for invalid or empty note or write failure; `duplicate` exits `0`

Do not copy `normalize_body_for_hash` locally; import or call it through the same module that the flush path uses (`run_log_batch._normalize_body_for_hash` or the re-exported `append_execution_issue` family). If a direct private import from `run_log_batch` trips layering lint, add an internal accessor in `run_log_batch` and call it through that.

## Files to modify/create

### UPDATED: python/larch/core/architectural_guidelines.py

Add the helper and CLI main.

Helper shape:

- Resolve `implement_tmpdir` from the CLI argument or `config.ENV_IMPLEMENT_TMPDIR`; exit 2 when absent.
- Read the note from `--note-file` via `_read_regular_text_no_follow`; reject symlinks and empty files.
- Format the Warnings entry (one or more bullet lines); redact with `_redact_batch_payload`.
- Split with `_execution_issue_chunks`; compute `structured_body_dedupe_keys` per chunk.
- Parse md dedup keys from the existing `### Warnings` body in `execution-issues.md`.
- Resolve RUN_ID from `parent-issue.md RUN_ID` → `session-id` file; when found, parse ndjson dedup keys from `larch-logs/implement/$RUN_ID/execution-issues.ndjson`.
- If any chunk key already exists in either key set, return `duplicate`.
- Otherwise append under `### Warnings`; create section if absent.
- Do not write or classify anything under `Tool Failures`.
- Return status string `ok`, `duplicate`, or `failed`; emit to stdout as `ARCHITECTURAL_GUIDELINES_APPEND_STATUS=`.

### UPDATED: python/larch/cli.py

Register the new verb:

- Add `("architectural-guidelines", "append-deviation-note"): ("larch.core.architectural_guidelines", "append_deviation_note_main")` to `_REGISTRY`.
- Add the same tuple to `_MACHINE_STDOUT_KEYS` near the other architectural-guidelines verbs.

### UPDATED: skills/implement/references/architectural-guidelines-present.md

Replace the vague append instruction with an explicit helper call.

Contract:

- In the deviation path, after writing `$IMPLEMENT_TMPDIR/architectural-guideline-assessment-draft.md`, call:
  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" architectural-guidelines append-deviation-note \
    --implement-tmpdir "$IMPLEMENT_TMPDIR" \
    --note-file "$IMPLEMENT_TMPDIR/architectural-guideline-assessment-draft.md"
  ```
- This helper always uses `category=Warnings`, deduplicates via the flush-path chunk+hash contract against both the md file and the committed ndjson batch.
- Treat `ARCHITECTURAL_GUIDELINES_APPEND_STATUS=ok` or `duplicate` as success; continue to the durable compose wrapper.
- On non-zero exit or `ARCHITECTURAL_GUIDELINES_APPEND_STATUS=failed`, do not continue to PR compose; relaunch Step 8.
- Explicitly prohibit using `execution-issues append` for guideline deviations.
- Keep the existing "if deviations are genuine" guard; do not append on the clean path.

### UPDATED: python/tests/core/test_architectural_guidelines.py

Add focused tests covering:

- A deviation note appends under `### Warnings`, not `Tool Failures`.
- The same note appended twice appears once (md-level dedup via chunk keys).
- A note whose chunk keys already appear in a seeded ndjson batch returns `duplicate` without modifying the md. Seed the batch using the same hash path as `_render_execution_issues_batch` (not raw note sha).
- Empty or whitespace-only note input fails with exit 1.
- Symlink `--note-file` is rejected.
- The CLI returns exit 2 for missing `--implement-tmpdir` with unset `IMPLEMENT_TMPDIR`.

### UPDATED: python/tests/design/test_design_cli_ports.py

Add the new verb to the registry coverage:

- Add `("architectural-guidelines", "append-deviation-note"): ("larch.core.architectural_guidelines", "append_deviation_note_main")` to `ARCHITECTURAL_GUIDELINES_EXPECTED` so CLI registration and machine-stdout assertions cover the new entry.

### UPDATED: skills/implement/scripts/test-architectural-guidelines-step.sh

Extend the harness to pin the new contract:

- Add a `contains` check for `architectural-guidelines append-deviation-note` in the deviation path of `architectural-guidelines-present.md`.
- Add a `not_contains` check for bare `execution-issues append` on the deviation path.

## Edge cases

- Existing `execution-issues.md` has `### Tool Failures` before `### Warnings`: insert into `Warnings` without moving other sections.
- Existing `execution-issues.md` has no `Warnings`: append a new `Warnings` section.
- Hash dedup matches flush-path keys: identical notes are idempotent even when the md or ndjson grows between calls.
- Empty or whitespace-only notes fail closed before any file I/O.
- Symlink note files are rejected.
- When RUN_ID is absent or the ndjson does not exist, skip the secondary ndjson check silently and rely on md dedup only.
- When ndjson check hits, return `duplicate` and emit `ARCHITECTURAL_GUIDELINES_APPEND_STATUS=duplicate` with exit 0 without appending to md.

## Failure modes

- If the entry format differs from what the flush path records, the ndjson dedup hash mismatches and duplicates can still appear. Pinning the exact entry format and the flush-path normalization prevents this.
- If `_normalize_body_for_hash` or `_execution_issue_chunks` drift between modules, dedup correctness degrades. Calling through the single `run_log_batch` module (or an exported accessor) avoids local copy drift.
- If the prompt still allows `execution-issues append` without `--category Warnings`, the fix is bypassed. The explicit prohibition in the updated contract closes this.

## Testing strategy

Run changed-surface checks:

- `python3 -m pytest python/tests/core/test_architectural_guidelines.py`
- `python3 -m pytest python/tests/design/test_design_cli_ports.py`
- `bash skills/implement/scripts/test-architectural-guidelines-step.sh`
- `python3 python/cli.py checks run-relevant`

## Acceptance

Run changed-surface checks:

- `python3 -m pytest python/tests/core/test_architectural_guidelines.py`
- `python3 -m pytest python/tests/design/test_design_cli_ports.py`
- `bash skills/implement/scripts/test-architectural-guidelines-step.sh`
- `python3 python/cli.py checks run-relevant`

diff_lines: 260

## Test plan
(no test plan section in plan-file)
