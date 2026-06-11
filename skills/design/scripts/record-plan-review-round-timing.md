# record-plan-review-round-timing.sh

Records one `/design` Step 3 plan-review round row in the timing ledger.

Args: `--design-tmpdir PATH --round N --start-s S --end-s E`.

The helper canonicalizes the design tmpdir, binds `LARCH_TIMING_LEDGER` to `$DESIGN_TMPDIR/timing-ledger.tsv`, counts accepted findings from `accepted-plan-findings.md`, rejected in-scope plan findings from `### [Plan Review] FINDING_N` headings in `rejected-findings.md`, and accepted OOS rows from `voting-tally.md` where `Item` is `OOS_N` and `Result` is exactly `accepted`. It never counts `oos.md`. The emitted row uses `python3 python/cli.py timing record-round --skill design --step "design Step 3 — plan review"`.

Callers treat failures as warnings only.
