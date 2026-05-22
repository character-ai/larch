# test-run-step2-dispatch.sh contract

Regression harness for `skills/implement/scripts/run-step2-dispatch.sh`.

Primary caller: `make test-run-step2-dispatch`.

Coverage:

- Missing required flags exit 2.
- Plan path is always `$IMPLEMENT_TMPDIR/plan.txt`; `WORKFLOW_PATH` is `HARD` for the Step 2 dispatcher argv; `CURSOR_PRESENT` is derived from `$IMPLEMENT_TMPDIR/session-env.sh`.
- `$IMPLEMENT_TMPDIR/feature-description.txt` is forwarded as the conventional
  `--feature-file`.
- Downstream stdout remains visible to the caller for Step 2 envelope parsing.
- The Q/A redispatch-only `--answers` exception is passed through exactly when
  supplied.

Update alongside `skills/implement/scripts/run-step2-dispatch.sh`.
