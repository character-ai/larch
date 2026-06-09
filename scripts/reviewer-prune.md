# reviewer-prune.sh Contract

`scripts/reviewer-prune.sh` is the shared per-run reviewer conditional-spawning helper for `/review`, `/implement` Step 5, and `/design` plan review.

## Commands

- `record --ledger FILE --round N --manifest FILE --classification FILE [--label-map FILE]` rewrites the ledger rows for round `N` from the launched manifest and final findings-classification TSV.
- `filter --ledger FILE --round N --manifest FILE --out FILE` writes an eligible-only manifest to `--out` and emits pruning KVs.

Ledger columns are `round`, `tool`, `slot`, `label`, `accepted_count`. `record` is idempotent per round: it rewrites the ledger as all rows whose `round != N`, followed by the new rows for `N`. If the manifest has zero rows, this clears that round's ledger rows.

## Matching and eligibility

Combo identity is the manifest pair `tool:slot`. Launched rows are strike rows: each launched slot records its accepted count, including zero when it returned no substantive accepted findings.

`accepted_count` counts `voting_result=accepted` TSV rows. Code-review TSV attribution comes from `reviewer_slots`, split on `|`, with phase2/phase3/retry suffixes and one trailing parenthetical normalized away before exact token equality against the manifest output basename. Plan-review TSV attribution comes from `finding_reviewers`, split on commas or whitespace runs, with exact token equality against labels supplied by `--label-map` (`slot<TAB>label`). Accepted OOS rows count the same as accepted in-scope rows.

Filtering is fail-open. `LARCH_REVIEWER_PRUNE=off` disables pruning exactly; other values keep pruning enabled, with a warning for non-empty values other than `off`. Rounds 1, 2, 5, and later are full-panel. In rounds 3 and 4, a combo is pruned only when its two most recent prior launched rows both have `accepted_count=0`; fewer than two prior launched rows keeps the combo eligible.

`filter` emits `PRUNE_ACTIVE`, `ELIGIBLE_COUNT`, `PRUNED_COUNT`, `PRUNED_COMBOS`, `PANEL_PRUNED_EMPTY`, and a `WARN` line when ledger parsing fails open. When it prunes, it also writes an operator-visible breadcrumb to stderr.

Harness: `scripts/test-reviewer-prune.sh`, wired through `make test-reviewer-prune`.
## Concise prune/log audit update

Filter stdout stays limited to prune KVs plus operator-visible `WARN` lines. Callers derive `PRUNE_STATUS` through `scripts/lib-prune-decision.sh`; advisory warnings do not imply failure, while nonzero filter rc or `PRUNE_FAIL_OPEN=true` do. Ledger rows remain launched-slot history only.
