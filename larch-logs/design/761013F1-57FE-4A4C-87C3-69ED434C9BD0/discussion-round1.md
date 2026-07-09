## Decision 1: Name predicate for Lint 1
- **Question**: Should the `_render_*` OR `*_rows` predicate be narrowed given medium false-positive risk?
- **Resolution**: Keep as-is. Measurement shows 21 top-level matches, 12 untested (baseline candidates). Five are non-renderer helpers (`_state_file_has_rows`, `_parse_rows`, `_parse_ndjson_structured_rows`, `_read_transcript_rows`, `_tsv_has_data_rows`) — these go into the baseline as grandfathered. The baseline-only-shrinks ratchet prevents growth.
- **Source**: codebase

## Decision 2: Lint 2 suppression pragma string
- **Question**: What is the suppression pragma format for lint_guidelines_note_wrapper_bypass?
- **Resolution**: `# lint-guidelines-note-wrapper-bypass: ok <reason>`, matching the Lint 1 convention and existing lint naming patterns.
- **Source**: codebase

## Decision 3: Baseline format for Lint 1
- **Question**: What JSON schema does the renderer-golden-tests baseline use?
- **Resolution**: `{"file": "larch/report/foo.py", "function_name": "_render_bar", "reason": "..."}` — three fields, matching the `lint_lifecycle_prefix_literal` style for reason-per-entry baselines. Baseline file: `python/renderer-golden-tests-baseline.json`.
- **Source**: codebase (mirroring lint_lifecycle_prefix_literal)
