# test-rate-assertions.sh contract

`skills/report-tokens/scripts/test-rate-assertions.sh` verifies the default rate values
and `cost_vendor` outputs in `run-analysis.sh`.

## Purpose

Guard against silent rate drift. If a vendor rate default is updated incorrectly, the
source-level grep checks fail immediately. The runtime checks extract the embedded Python
from the heredoc and run spot-checks against `cost_vendor` to confirm the computation
also matches documented values.

## Primary caller

- `make lint` (via pre-commit hook on `skills/report-tokens/scripts/**`).
- Developers running `bash skills/report-tokens/scripts/test-rate-assertions.sh` directly.

## What is checked

Source-level pattern assertions (grep) for every vendor rate field, and runtime
`cost_vendor` spot-checks:

- `cost_vendor("codex", {total: 1M})` → `$5.00` (aggregate path)
- `cost_vendor("cursor", {input: 1M, total: 1M})` → `$0.50` (input path)

## Edit-in-sync

Update the expected rate values in this harness whenever the defaults in `run-analysis.sh`
are intentionally changed.
