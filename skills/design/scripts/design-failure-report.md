# design-failure-report.sh

`design-failure-report.sh` is the `/design` teardown report gate. It files at most one report per run through `python3 "$PLUGIN_ROOT/python/cli.py" stall-recovery ... --profile generic --artifact-prefix design-failure`.

## Decision order

The gate skips when a terminal, escalation-success, or operator-action sentinel already exists. Cancelled outcomes write operator-action audit artifacts and do not file. Failed outcomes require a valid `design-failure-terminal-state.env`; missing or invalid state fails closed to `design-failure-chat-print.md`. Successful outcomes are limited to `approved` and `approved-partition`, and only file escalation-success when durable escalation evidence exists.

Terminal classify and compose calls pass `--primary-state-file "$DESIGN_TMPDIR/design-failure-terminal-state.env"`, `--session-env-file "$DESIGN_TMPDIR/source-env.sh"`, `--finalize-state-file` when present, and `--implement-tmpdir "$DESIGN_TMPDIR"`.

## Outputs

The helper writes `design-failure-terminal-report.env`, `design-failure-escalation-success.env`, `design-failure-operator-action.env`, `design-failure-chat-print.md`, and `design-failure-operator-action-chat.md` as applicable. Stdout is KV-only so `render-final-summary.sh` can capture it without polluting `final-summary.md`.

## Harness

`test-design-failure-report.sh` covers precedence, failed outcome fallback, terminal reporting, escalation-success, operator-action skips, and duplicate suppression.
