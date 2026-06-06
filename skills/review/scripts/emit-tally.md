# emit-tally.sh Contract

`skills/review/scripts/emit-tally.sh` writes review summary artifacts for a round.

It writes `review-round-summary.md`, `review-summary.json` with `schema_version=3`, and `rejected-findings.md`. Accepted and rejected totals come from the summary counters in `review-tally.env` (falling back to grep heuristics when needed). The round summary uses operator-facing wording of the form “`K` accepted, `N` rejected (`P` exonerated)” with `P ≤ N` (enforced before the JSON write — violation exits non-zero and leaves no `review-summary.json`). The compact `rejected-findings.md` lists `FINDING_*_OUTCOME=rejected` lines (all non-accepted findings share `OUTCOME=rejected`; sub-classification lives in optional `FINDING_*_REJECTED_SUBTYPE=` keys in `review-tally.env`). The JSON summary includes `panel.scout_status`, `panel.static_slot_count`, `panel.dynamic_slot_count`, and `panel.total_slot_count`, populated by `--scout-status`, `--static-slot-count`, and `--dynamic-slots` (defaulting to `na`/`0`/`0`). For accepted OOS it first reads `OOS_ACCEPTED_COUNT` from the tally file (absent or non-numeric coerces to `0`): when the count is `> 0`, tally-code-votes.sh has already serialized normalized accepted OOS into `oos-accepted-review.md` and emit-tally is a **no-op** on that file — neither `skills/shared/scripts/oos-serialize.sh` nor the missing-`oos.md` truncate runs (tally output is authoritative on the review-core path; #3550). The serialize-or-truncate fallback (invoke `oos-serialize.sh` when `--oos-file` names an existing file, else truncate to empty) executes only when `OOS_ACCEPTED_COUNT == 0`, preserving standalone emit paths. It copies summary files to parent tmpdirs when `--session-env-path` or `--implement-tmpdir` is provided.

Stdout is `KEY=value` only: `EMIT_OK`, `ROUND_SUMMARY_FILE`, and `REVIEW_SUMMARY_FILE`.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.

Harness: `skills/review/scripts/test-emit-tally.sh`, wired through `make test-emit-tally`.
