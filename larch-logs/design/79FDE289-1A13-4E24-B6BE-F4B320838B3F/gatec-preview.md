## Final Design Plan

## Approach

Centralize canonical review-wire fixtures without changing production grammar. Keep malformed, legacy, and one-off literals inline when tests must control exact deviations.

### NEW: python/tests/support/review_wire.py

- Add typed, side-effect-free builders:
  - `make_finding_block` for canonical finding and OOS Markdown blocks.
  - `make_rejected_block` for rejected findings, with optional `[Plan Review]` framing.
  - `vote_lines` for canonical judge vote rows and axis tokens.
  - `ballot_snippet` for composing finding blocks and ballots with stable spacing.
  - `plan_review_slot_line` for one plan-review slot record.
  - `slot_manifest_ndjson` for deterministic compact NDJSON with a terminal newline.
  - Shared panel-manifest row and NDJSON builders for code-review and report fixtures.
- Accept `Path` values and serialize them as strings through `json.dumps`.
- Preserve caller-supplied row order and optional manifest fields such as `prompt_file`, `vendor`, and `resolved_model`.
- Do not hide invalid-input scenarios behind validation. Tests for malformed JSON, missing fields, scalar rows, duplicate headings, or noncanonical votes must retain explicit literals.

### UPDATED: python/tests/review/test_plan_review.py

- Import the shared builders.
- Replace `_make_rejected_block` and `_make_finding_only_rejected_block` with `make_rejected_block` calls.
- Replace repeated canonical plan-review slot NDJSON and ballot fixtures where their byte shape matches the shared contract.
- Keep tests for marker drift, malformed blocks, symlinks, and stale artifacts explicit.

### UPDATED: python/tests/review/test_review_tally.py

- Replace `_mk_ballot`, `_write_classification_ballot`, repeated canonical finding blocks, vote rows, and panel-manifest rows with shared builders.
- Retain local literals when a test targets missing axes, invalid votes, stale proposer maps, malformed manifests, or exact partial ballots.
- Preserve classification headers and production-facing assertions unchanged.

### UPDATED: python/tests/review/test_voting.py

- Import and use `make_finding_block`, `ballot_snippet`, and `vote_lines` for normal parser and tally fixtures.
- Keep hand-authored inputs for whitespace variants, duplicate headings, aliases, Markdown tables, invalid tokens, and other parser edge cases.
- Remove imports made obsolete by the migration.

### UPDATED: python/test_support.py

- Re-export or import the review-wire helpers needed by shared top-level fixtures.
- Update `make_zero_findings_plan_review_fake_cli` to build `plan-review-slots.ndjson` with `plan_review_slot_line` or `slot_manifest_ndjson`.
- Preserve its fake CLI command routing and emitted `KEY=value` envelopes.

### MAY_UPDATE: python/tests/review/test_review_aggregate.py

- Convert canonical aggregation inputs and outputs that differ only by finding content.
- Keep malformed headings, omitted fields, attribution failures, preamble slips, and empty-merge attestations inline so each regression remains visible.

### MAY_UPDATE: python/tests/review/test_plan_review_panel.py

- Use shared slot and panel-manifest builders for ordinary manifest setup.
- Preserve fixtures that intentionally exercise invalid slot definitions, dropped-slot sidecars, fallback fields, or serialization details.

### MAY_UPDATE: python/tests/review/test_plan_review_round.py

- Replace repeated valid `plan-review-slots.ndjson` construction with shared builders.
- Preserve non-dict rows, missing keys, mixed valid and invalid records, and ordering-sensitive fixtures as explicit test data.

### MAY_UPDATE: python/tests/report/test_review_phase_detail.py

- Replace `_write_slot_manifest` and repeated valid panel-manifest NDJSON with the shared builders.
- Pass optional model and vendor fields through the common row factory.
- Keep relative-path, dropped-slot, legacy-shape, and malformed fixtures explicit.

## Edge cases

- Emit exactly one newline between Markdown fields and blocks where existing tests require it.
- Support singular and plural reviewer labels without normalizing intentional test input.
- Preserve manifest row order, compact JSON, Unicode, quotes, backslashes, and paths with spaces.
- Represent zero rows as an empty string, not a blank NDJSON record.
- Do not merge distinct slot records. This preserves per-slot accounting.

## Failure modes

- A builder default could silently change fixture bytes. Pin representative full-string outputs through migrated assertions.
- Over-migration could weaken negative parser tests. Leave every deliberate grammar violation inline.
- Optional manifest fields could be dropped. Cover plan-review and shared panel rows with extra fields.
- Import layering could create a cycle. Keep `review_wire.py` independent of `test_support.py` and production test runners.

## Testing strategy

- Run focused support and migrated suites:
  - `python3 -m pytest -q python/tests/support/test_foundation.py`
  - `python3 -m pytest -q python/tests/review/test_plan_review.py`
  - `python3 -m pytest -q python/tests/review/test_review_tally.py`
  - `python3 -m pytest -q python/tests/review/test_voting.py`
  - Include each changed MAY_UPDATE test file in the same focused run.
- Run the full review shard: `python3 -m pytest -q python/tests/review`.
- Run the report fixture suite when changed: `python3 -m pytest -q python/tests/report/test_review_phase_detail.py`.
- Run lint and type checks only for changed Python files through the repository’s relevant-checks flow.

difficulty: MODERATE
mechanical_churn: true
diff_lines: 1100
