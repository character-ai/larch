# test-run-step5-review.sh contract

Regression harness for `scripts/run-step5-review.sh`.

Primary caller: `make test-run-step5-review`.

Coverage:

- Missing required flags exit 2.
- `POST_PLAN_WORKFLOW_PATH=SIMPLE` derives `--panel simple --round-cap 5`.
- `POST_PLAN_WORKFLOW_PATH=HARD` derives `--panel hard --round-cap 7`.
- `CODEX_PRESENT`, `CURSOR_PRESENT`, `PLAN_FILE`, `session-id`, and the
  conventional feature/session-env paths are forwarded to the downstream
  `review-and-fix.sh` argv.
- Downstream stdout remains visible to the caller for Step 5 parsing.

Update alongside `scripts/run-step5-review.sh`.
