# test-run-step5-review.sh contract

Regression harness for `scripts/run-step5-review.sh`.

Primary caller: `make test-run-step5-review`.

Coverage:

- Missing required flags exit 2.
- Base `--round-cap 5` is fixed; the launcher does **not** pass `--panel` because panel selection lives inside `review-and-fix.sh` → `review-core.sh`.
- `LARCH_DYNAMIC_ARCHETYPES_MAX` in session-env is forwarded as an explicit
  `--dynamic-archetypes <N>` arg so `/implement` operator flags override any
  ambient shell env in downstream `review-and-fix.sh` resolution.
- `CODEX_PRESENT`, `CURSOR_PRESENT`, conventional `$IMPLEMENT_TMPDIR/plan.txt`, `session-id`, and the conventional feature/session-env paths are forwarded to the downstream `review-and-fix.sh` argv.
- Downstream stdout remains visible to the caller for Step 5 parsing.

Update alongside `scripts/run-step5-review.sh`.

- Ledger regression coverage asserts stdout preservation, canonical recording for `coder-main-agent-required`, fallback fail-open behavior, exact `STEP5_REVIEW_LEDGER_*` emission for MAV, and no duplicate prompt-side records.
