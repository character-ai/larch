# test-run-step5-review.sh contract

Regression harness for `scripts/run-step5-review.sh`.

Primary caller: `make test-run-step5-review`.

Coverage:

- Missing required flags exit 2.
- `POST_PLAN_WORKFLOW_PATH=SIMPLE` or `HARD` derives a base `--round-cap 5`
  (plus prior degraded-round inflation); the launcher does **not** pass
  `--panel` — the unified hard panel is applied inside `review-and-fix.sh` →
  `review-core.sh`.
- `LARCH_DYNAMIC_ARCHETYPES_MAX` in session-env is forwarded as an explicit
  `--dynamic-archetypes <N>` arg so `/implement` operator flags override any
  ambient shell env in downstream `review-and-fix.sh` resolution.
- `CODEX_PRESENT`, `CURSOR_PRESENT`, `PLAN_FILE`, `session-id`, and the
  conventional feature/session-env paths are forwarded to the downstream
  `review-and-fix.sh` argv.
- Downstream stdout remains visible to the caller for Step 5 parsing.

Update alongside `scripts/run-step5-review.sh`.
