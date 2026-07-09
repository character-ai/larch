## Plan

## Approach

Confidence: high.

Implement the marker as a parser-only normalization feature. Do not change downstream consumers. They already read the normalized `parse_guideline_entries` output.

Keep the source guideline prose intact for human readers. For marked entries, emit only:

1. the normalized `### G-...` heading
2. the normalized `- Mechanized: ...` line

Drop `Why` and `Deviate when` only from marked entries.

## Files to modify/create

### UPDATED: python/larch/core/architectural_guidelines.py

- Add `_MECHANIZED_RE` near `_WHY_RE` and `_DEVIATE_RE`.
- Update `parse_guideline_entries` so it tracks each current entry's heading, optional mechanized line, and normal detail bullets.
- On entry flush:
  - if a mechanized line exists, emit `[heading, mechanized]`
  - otherwise emit the existing heading plus `Why` and `Deviate when` bullets
- Preserve current behavior for:
  - preamble omission
  - closing an entry on non-guideline Markdown headings
  - stripping bullet payload whitespace
  - unmarked entries byte-for-byte

### UPDATED: ARCHITECTURAL_GUIDELINES.md

- Add a Mechanized marker to `G-Cfg-1`:
  - Name `python3 python/cli.py lint env-via-config-constant`
  - State the partial scope clearly: env-var literals only, not exit codes, tunables, or all wire literals.
- Add a Mechanized marker to `G-Bash-3`:
  - Name `make lint-bash32`
  - Include the existing residue in one line, likely the renderer replacement hazard covered by `make lint-renderer-substitution-safety`.
- Leave `G-Py-11` unchanged because the companion suppression-reason lint has not landed.

### UPDATED: python/tests/core/test_architectural_guidelines.py

Add focused parser tests:

- A marked guideline emits exactly heading plus Mechanized line.
- A marked guideline drops `Why` and `Deviate when`.
- An unmarked guideline keeps today's normalized output byte-for-byte.
- Mixed marked and unmarked entries preserve ordering and only slim the marked entry.

Use `parse_guideline_entries` directly for byte-stable tests. Avoid fixture files unless needed.

## Edge cases

- A `- Mechanized:` line outside a `G-*` entry must be ignored.
- A non-guideline Markdown heading must still end the current entry.
- An unmarked entry with extra bullets such as `Guidance:` must still omit those bullets.
- G-Cfg-1 must not overstate coverage. Its marker should make partial coverage visible in the slim payload.
- G-Bash-3 should not claim one lint covers the renderer substitution residue unless the marker names both relevant checks or states the split.

## Failure modes

- If parser state is mutated in place after seeing `Mechanized`, prior `Why` lines may leak. Flush based on stored fields, not append-only lines.
- If the Mechanized regex is too broad, unrelated bullets may slim entries by accident. Match exact `- Mechanized:` bullets only.
- If the marker prose is too long, payload reduction shrinks less. Keep marker text one concise line.
- If tests assert only substrings, byte drift in unmarked entries may slip through. Add an exact expected string.

## Testing strategy

Run only changed-file relevant tests and lint:

- `PYTHONPATH=python python3 -m pytest python/tests/core/test_architectural_guidelines.py`
- `make py-lint-main` or the narrower project-supported Python lint path if available.
- Recompute and record normalized payload bytes and entry count before and after for the PR description. Use `parse_guideline_entries` and `GUIDELINE_HEADING_RE` so counts match runtime behavior.

## PR notes

In the PR description, report:

- normalized payload bytes before and after
- normalized entry count before and after
- that G-Cfg-1 is partially mechanized for env-var literals only
- that G-Py-11 remains unmarked

## Acceptance

Run only changed-file relevant tests and lint:

- `PYTHONPATH=python python3 -m pytest python/tests/core/test_architectural_guidelines.py`
- `make py-lint-main` or the narrower project-supported Python lint path if available.
- Recompute and record normalized payload bytes and entry count before and after for the PR description. Use `parse_guideline_entries` and `GUIDELINE_HEADING_RE` so counts match runtime behavior.

review_status: complete
rounds_completed: 1
difficulty: MODERATE
diff_lines: 100
