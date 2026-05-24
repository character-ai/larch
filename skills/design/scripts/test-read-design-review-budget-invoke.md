# test-read-design-review-budget-invoke.sh

Offline harness for `read-design-review-budget.sh` (JSON / jq / grep fallbacks) and `invoke-plan-validator-if-not-quick.sh` (quick tier skips `design-driver.sh`).

## Running

`make test-read-design-review-budget-invoke` (via `scripts/harness-timer.sh`).

## Contract

Uses temp `run-params.json` files and a fake `PATH` prefix so `python3` / `jq` resolve to no-op scripts, exercising the grep literal branches in `read-design-review-budget.sh`.
