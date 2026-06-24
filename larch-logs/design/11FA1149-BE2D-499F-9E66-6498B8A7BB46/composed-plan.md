## Plan

## Preconditions

- Land this only after **both** the severity-measurement dependency **and** the severity-rubric (Phase II rubric) dependency are complete.
- Do not add a runtime feature flag.
- Treat `approach-synthesis.txt` as `NO_SKETCHES`; draft from direct repo inspection.

## Approach

- Add weighted accepted counts to the prune data path.
- Derive accepted weight from the **same value-points contract** the scoreboard uses: `voting.accepted_points_from_classification_row(row, header)` over `v1_vote`–`v3_vote` and `v1_severity`–`v3_severity`.
- Use that helper for **both** plan mode and code-review mode; do **not** read `body_severity` for prune weighting (`body_severity` is forensic-only and uses a different token vocabulary).
- Count an accepted high-severity finding as `2` and all other accepted in-scope findings as `1`, matching `voting.accepted_finding_points_from_severities` / `voting.HIGH_SEVERITIES` semantics.
- Keep rejected and total counts unchanged.
- Use weighted accepted counts only for the net prune gate.
- Keep the 1/3 acceptance floor on unweighted `accepted_sum`.
- **Contract note:** `accepted_points_from_classification_row` returns flat `1` when `scope` is absent from the classification header, before reading `vN_severity` cells. Code-review weighting tests must therefore use the normal code-review classification header (including `scope`), not the legacy 3-column prune fixture shape.

## Files to modify/create

### UPDATED: `python/review_pipeline.py`

- Extend `PruneRoundCounts` with `weighted_accepted: int = 0`.
- Update `_read_classification_counts`:
  - Track `weighted_accepted` beside `accepted`, `rejected`, and `total`.
  - Capture `header = list(reader.fieldnames or [])` once per file.
  - When `voting_result == "accepted"`, increment `accepted` by `1` and, for each attributed label, increment `weighted_accepted` by `voting.accepted_points_from_classification_row(row, header)`.
  - Do **not** branch on `plan_mode` for weighting; `plan_mode` remains only for reviewer label tokenization.
  - Leave `rejected` and `total` behavior unchanged.
- Update `_prune_ledger_header()` to include `weighted_accepted_count`.
  - Use this order: `round`, `tool`, `slot`, `label`, `accepted_count`, `weighted_accepted_count`, `rejected_count`, `total_count`.
- Add a helper to normalize legacy prune ledger rows.
  - For 7-column rows, insert `accepted_count` as `weighted_accepted_count`.
  - For 8-column rows, preserve the supplied weighted value.
  - Reject any other column count.
  - Validate all numeric columns after normalization.
- Update `_well_formed_prune_ledger_row()` to accept legacy 7-column rows and new 8-column rows through that helper.
- Update `_rewrite_prune_ledger()`:
  - Normalize preserved old rows before writing them under the new header.
  - Write new round rows with 8 columns.
- Update `reviewer_prune_record()` to write `weighted_accepted_count`.
- Update `_ledger_history()`:
  - Accept both legacy and new headers.
  - Parse rows through the normalization helper, not `csv.DictReader` field alignment alone.
  - Default legacy `weighted_accepted` to `accepted`.
  - Merge duplicate round rows using max values for all four count fields.
- Update `reviewer_prune_filter()`:
  - Compute `weighted_accepted_sum` from the last two launched rounds.
  - Set `net_prunable = weighted_accepted_sum - rejected_sum <= 0`.
  - Keep `floor_prunable` based on unweighted `accepted_sum` only; do **not** substitute `weighted_accepted_sum` into the 1/3 floor formula.
- Update `ensure_reviewer_prune_ledger()`:
  - Write the new 8-column header.
  - Preserve valid legacy rows by upgrading them to 8 columns.
  - Continue dropping malformed rows.

### UPDATED: `python/test_review_pipeline.py`

- Update prune ledger header expectations to include `weighted_accepted_count`.
- Update existing row suffix assertions:
  - Accepted non-high rows should now end with `accepted_count`, `weighted_accepted_count`, `rejected_count`, `total_count`.
  - For existing tests without severity data, weighted accepted should equal accepted.
- Update `test_ensure_reviewer_prune_ledger_preserves_good_rows_and_drops_malformed`:
  - Start with a legacy 7-column header and row.
  - Assert the output header is the new 8-column header.
  - Assert the preserved row has `weighted_accepted_count == accepted_count`.
  - Keep malformed row drop coverage.
- Add a code-review weighting test:
  - Use the **normal code-review classification header** from `voting.code_review_classification_header()` (must include `scope`), not the minimal 3-column `_write_prune_classification` shape.
  - Set `scope=in_scope` on accepted rows.
  - Record round 1 with one accepted high-severity finding (`vN_vote=YES`, `vN_severity=major` or `blocker` on YES cells).
  - Record round 2 with one rejected finding.
  - Filter round 3.
  - Assert the combo is not pruned because `weighted_accepted_sum - rejected_sum` is positive.
  - Assert ledger rows write `weighted_accepted_count=2` when `scope` is present and YES voter severities are high.
  - Assert this does not alter the 1/3 floor behavior.
- Add a code-review low-severity control:
  - Same accepted plus rejected shape with `scope=in_scope`, but with non-high accepted voter severities.
  - Assert the combo is pruned and `weighted_accepted_count=1`.
- Add a code-review scope-absent control (optional but recommended):
  - Use a classification fixture **without** `scope` in the header.
  - Assert `weighted_accepted_count` stays `1` even when YES voter severities are high, matching the helper's flat-weight fallback.
- Add a plan-mode weighting test:
  - Record an accepted plan finding with high severity on YES `vN_severity` cells (not `body_severity` alone).
  - Assert the ledger row writes `accepted_count=1`, `weighted_accepted_count=2`, `rejected_count=0`, `total_count=1`.
- Add a plan-mode body-severity divergence regression:
  - Set `body_severity` to `important` or `blocking` but keep YES voter severities non-high.
  - Assert `weighted_accepted_count=1` (weight follows voter severities, not proposer body text).
- Add `test_reviewer_prune_filter_floor_uses_unweighted_accepted_with_high_severity`:
  - Use the full code-review classification header with `scope=in_scope`.
  - Record round 1 with one accepted high-severity finding (`vN_vote=YES`, `vN_severity=major` or `blocker`).
  - Record round 2 with three neutral findings.
  - Assert `PRUNED_COUNT=1` (combo is pruned by the unweighted 1/3 floor: `accepted_sum=1`, `total_sum=4`, `1*3 < 4*1`).
  - Assert `weighted_accepted_sum` is positive (`2` with zero rejected), so a buggy floor that substituted `weighted_accepted_sum` would **not** prune (`2*3 < 4*1` is false).
  - This pins floor math to unweighted `accepted_sum` on the high-severity weighted-net path; the legacy `test_reviewer_prune_filter_prunes_low_precision_positive_net` fixture cannot catch that regression because its 3-column shape keeps `weighted_accepted == accepted`.
- Add or update a legacy filter test:
  - Handwrite an old 7-column ledger.
  - Assert the filter still degrades gracefully and defaults weighted accepted to accepted.
- When adding new weighting fixtures, extend or supplement `_write_prune_classification` with a helper that emits the full code-review header plus `scope` and `vN_vote` / `vN_severity` columns; do not reuse the 3-column fixture for high-severity weighting assertions.

### UPDATED: `python/test_plan_review_round.py`

- Update prune ledger header assertions to include `weighted_accepted_count`.
- Update plan-review ledger row assertions:
  - Accepted rows without high YES voter severities should write `1\t1\t0\t1` for the four count columns.
  - Empty collector rows should write `0\t0\t0\t0`.

### UPDATED: `skills/design/scripts/test-findings-classification.sh`

- Refresh prune-ledger grep expectations for the 8-column suffix.
  - The harness builds FINDING_1 with three YES `SEVERITY=major` votes and `scope=in_scope`; `accepted_points_from_classification_row` returns `2` per label.
  - Change `Cursor-Pragmatic\t1\t0\t1` to `Cursor-Pragmatic\t1\t2\t0\t1`.
  - Change `Codex-Arch\t1\t0\t1` to `Codex-Arch\t1\t2\t0\t1`.
  - Keep `accepted_count=1` per label; only `weighted_accepted_count` changes.
- Update any header checks that assume the legacy 7-column prune ledger.

## Edge cases

- Legacy 7-column ledgers must keep working.
- Legacy rows preserved under the new header must be normalized before writing.
- Missing severity columns must default weight to `1` for accepted findings (via `accepted_points_from_classification_row`).
- Missing `scope` column in the classification header forces flat weight `1` even when YES voter severities are high.
- Invalid severity tokens must not inflate weights.
- Rejected findings must not add weighted accepted points.
- Neutral findings must still contribute to `total` but not accepted, weighted accepted, or rejected.
- `body_severity` tokens (`blocking`, `important`, etc.) must **not** affect prune weight when voter severities differ.
- Duplicate rows for the same combo and round should keep the max count per field.
- Plan-mode labels with spaces must still tokenize exactly as today.
- OOS scope rows stay weight `1` per the existing classification-row helper.
- One high-severity accepted plus three neutral findings across the last two rounds: weighted net is positive, but the unweighted 1/3 floor must still prune.

## Failure modes

- If a ledger has a malformed header or malformed numeric fields, pruning should keep the existing fail-open behavior.
- If severity columns are absent in old classification TSVs, weights should default to `1` for accepted findings.
- If `scope` is absent from classification headers, weights should default to `1` for accepted findings regardless of voter severities.
- If all reviewers prune out in rounds 3 or 4, existing `PANEL_PRUNED_EMPTY=true` behavior should remain unchanged.
- Landing before severity-rubric completes can double-weight inflated severities; the dual dependency precondition blocks that.
- Code-review tests that omit `scope` from fixtures will pass unweighted math and miss the weighted-prune regression.
- If `floor_prunable` accidentally uses `weighted_accepted_sum`, high-severity reviewers with low unweighted acceptance rates survive pruning; the dedicated floor-unweighted test above catches that.

## Testing strategy

- Run targeted tests:
  - `python3 -m pytest python/test_review_pipeline.py python/test_plan_review_round.py`
- Run the design forensic harness:
  - `make test-findings-classification`
- Run repository-required Python checks:
  - `make py-lint`
  - `make py-test`
- Run full lint before handoff:
  - `make lint`

## Non-goals

- Do not change the 1/3 acceptance floor formula.
- Do not change prune activation windows.
- Do not change panel size.
- Do not add scout precision allocation.
- Do not use `body_severity` as a prune-weight source.
- Do not update docs in this change unless tests expose a required contract mismatch.

## Acceptance

- `_prune_ledger_header()` returns 8 columns including `weighted_accepted_count`.
- Existing prune tests pass with updated header and suffix assertions.
- `weighted_accepted_sum - rejected_sum <= 0` drives `net_prunable`; `accepted_sum` still drives the 1/3 floor.
- New tests cover: high-severity weighting, low-severity control, legacy ledger backward compat, floor-unweighted regression, body-severity divergence.
- `skills/design/scripts/test-findings-classification.sh` updated and green.
- `make py-lint`, `make py-test`, `make lint` all pass.

review_status: complete
rounds_completed: 4
diff_lines: 255
