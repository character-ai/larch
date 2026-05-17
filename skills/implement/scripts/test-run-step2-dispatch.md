# test-run-step2-dispatch.sh contract

Regression harness for `skills/implement/scripts/run-step2-dispatch.sh`.

Primary caller: `make test-run-step2-dispatch`.

Coverage:

- Missing required flags exit 2.
- `PLAN_FILE`, `POST_PLAN_WORKFLOW_PATH`, `LARCH_AUTO_MODE`, and
  `CURSOR_PRESENT` are derived from `$IMPLEMENT_TMPDIR/session-env.sh`.
- `$IMPLEMENT_TMPDIR/feature-description.txt` is forwarded as the conventional
  `--feature-file`.
- Downstream stdout remains visible to the caller for Step 2 envelope parsing.
- The Q/A redispatch-only `--answers` exception is passed through exactly when
  supplied.

Update alongside `skills/implement/scripts/run-step2-dispatch.sh`.
