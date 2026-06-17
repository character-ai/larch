# test-step-16-17.sh

Offline harness for `step-16-17.sh` and the `step-17.sh --no-print-stdout` handoff contract.

## Fixtures

The harness copies `step-16-17.sh`, `step-16.sh`, and `step-17.sh` into a temporary plugin root and installs a stub `python/cli.py`. The stub avoids network and GitHub calls while simulating rejected-findings, Slack, final-report, and `run-log append-failure` behavior.

## Coverage

The harness asserts happy-path marker emission, body equality with `summary-final.md`, `.step17-printed` ownership, and `.step17-emitted` non-ownership. It also covers Step 16 failure, Slack skipped, Slack failed with Warnings and `--redact`, stale-summary render failure, empty render failure, and post-persist upsert failure. The stale-summary case proves non-zero Step 17 rc suppresses markers even when an older non-empty summary remains. The upsert-failure case proves Tool Failures logging happens before the shell handoff exits `0` and markers emit.
