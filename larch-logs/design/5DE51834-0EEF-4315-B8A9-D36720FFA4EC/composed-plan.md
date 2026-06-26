## Plan

## Approach

Make the minimum code change approved in discussion and accepted review findings:

- Keep the existing prune formulas (`net_prunable`, `floor_prunable`).
- Keep one shared path for `/design` and `/implement`.
- Move the active window from rounds 3–4 to rounds 2–4.
- Let round 2 prune from its only available prior ledger row.
- Keep rounds 3–4 on the existing two-row evidence bar so a single stale ledger row cannot prune after an intermediate round that launched reviewers but never recorded (e.g. MAV / `main-agent-vote-required`).
- Fix docs that still describe pruning as unweighted.

## Files to modify/create

### UPDATED: `python/review_pipeline.py`

Change `reviewer_prune_filter`:

- Replace the early skip guard:
  - From `round_num <= 2`
  - To `round_num <= 1`
- Keep `round_num >= 5` unchanged so round 5 still re-probes the full panel.
- Change the evidence threshold to be round-aware:
  - Compute `min_recent = 1 if round_num == 2 else 2`
  - Replace `if len(recent) >= 2:` with `if len(recent) >= min_recent:`
  - Round 2 may prune from one prior launched round.
  - Rounds 3–4 still require two recent ledger rows, preserving today's guard against single-row stale history.
- Do not change:
  - `recent = sorted(hist.get(key, {}).items())[-2:]` (still the last two launched rounds when present)
  - `net_prunable = weighted_accepted_sum - rejected_sum <= 0`
  - `floor_prunable`
  - fail-open ledger handling
  - `LARCH_REVIEWER_PRUNE=off`
  - manifest rewrite behavior

Change `prune_window_evaluated`:

- Return `"true"` for `{"2", "3", "4"}`.
- Keep all other rounds `"false"`.

### UPDATED: `python/test_review_pipeline.py`

Add focused coverage near the reviewer-prune tests:

- Add a round-2 activation test:
  - Record only round 1.
  - Use a zero-yield or rejected round-1 ledger row.
  - Filter for round 2.
  - Assert `PRUNE_ACTIVE=true`, `PRUNED_COUNT=1`, and `PANEL_PRUNED_EMPTY=true`.
- Add a round-3 guard test for the round-aware threshold:
  - Seed ledger history with only one prior launched round for a combo (e.g. round 1 present, round 2 absent because recording never ran).
  - Filter for round 3.
  - Assert the combo is **not** pruned (`PRUNED_COUNT=0` or combo remains eligible).
  - This locks the accepted finding: global `len(recent) >= 1` must not apply to rounds 3–4.
- Add or update window assertions for `review_pipeline.prune_window_evaluated`:
  - Round 1 is false.
  - Rounds 2, 3, and 4 are true.
  - Round 5 is false.
- Update any stale test name or assertion that implies pruning starts only at round 3.
- Keep existing round-3 weighted-net tests. They protect the #5126 formula.
- Keep the round-5 and `LARCH_REVIEWER_PRUNE=off` test. Extend it to assert round 1 stays inactive if that is the smallest clean edit.

### UPDATED: `docs/point-competition.md`

Fix stale wording in two places:

- In the `LARCH_UNIQUE_FINDER_BONUS` paragraph:
  - Stop saying reviewer pruning is unweighted accepted-minus-rejected math.
  - Say the net prune gate uses value-weighted accepted points minus rejected counts.
  - Say the unique-finder bonus does not affect pruning.
  - Mention that the acceptance-rate floor still uses unweighted accepted/total counts.
- In `## Conditional spawning`:
  - Change rounds 3–4 to rounds 2–4.
  - Explain that round 2 uses one prior launched round, while rounds 3–4 still require two recent launched rounds.
  - Replace "Net score is unweighted accepted-minus-rejected counts" with value-weighted net gate wording.
  - Preserve the note that neutral findings affect the acceptance-rate denominator but not the net gate.

## Edge cases

- **Round 1** stays skipped because no prior ledger evidence exists.
- **Round 2** can prune from one prior launched round.
- **Rounds 3–4** still slice the last two launched rounds and still require `len(recent) >= 2`, so a lone stale row cannot prune after a skipped recording round.
- **Round 5** stays full-panel re-probe.
- **Env override** still disables pruning with `LARCH_REVIEWER_PRUNE=off`.
- **Malformed ledger** still fails open.

## Failure modes

- If `prune_window_evaluated` is not updated, dispatch may report pruning as skipped even when `reviewer_prune_filter` can prune.
- If only the window is updated and the evidence check becomes globally `len(recent) >= 1`, rounds 3–4 may prune from one stale ledger row and overwrite productive recent history.
- If round 2 keeps `len(recent) >= 2`, `/implement` still cannot activate pruning when only round 1 exists.
- If docs keep "unweighted", operators will see a false contract for #5126.

## Testing strategy

Run targeted tests first:

- `python3 -m pytest python/test_review_pipeline.py -k 'reviewer_prune'`

Then run required repo checks:

- `make lint`
- `make py-lint`
- `make py-test`

## Acceptance

Run targeted tests first:

- `python3 -m pytest python/test_review_pipeline.py -k 'reviewer_prune'`

Then run required repo checks:

- `make lint`
- `make py-lint`
- `make py-test`

review_status: complete
rounds_completed: 2
diff_added: 42
diff_deleted: 10
mechanical_churn: false
diff_lines: 52
