# test-read-design-review-budget-invoke.sh

Offline harness for `read-design-review-budget.sh` (JSON / jq / grep fallbacks) and `invoke-plan-validator-if-not-quick.sh` (quick tier skips `design-driver.sh`).

## Running

`make test-read-design-review-budget-invoke` (via `scripts/harness-timer.sh`).

## Contract

Uses temp `run-params.json` files and a fake `PATH` prefix so `python3` / `jq` resolve to no-op scripts, exercising the grep literal branches in `read-design-review-budget.sh`.

Coverage also includes:

- **Unreadable / missing run-params JSON**: `read-design-review-budget.sh` returns `full` when the path is not readable; `invoke-plan-validator-if-not-quick.sh` treats a missing or unreadable `run-params.json` as quick tier (exit 0, empty stdout) without calling the driver.
- **`sketch_budget` heuristic**: non-zero `sketch_budget` with no `review_budget` yields `full` via the python3 path.
- **jq branch**: a python3-only fakebin (stub `python3` exits 1) prefixes `PATH`, then a jq-only directory containing a symlink to the real `jq` binary (so co-located system `python3` never shadows the stub). That exercises `jq` parsing of `review_budget`. If `command -v jq` finds nothing, the harness prints `SKIP: jq not on PATH; skipping jq-path branch` and continues.
- **Grep fallbacks**: both `python3` and `jq` stubbed — `review_budget` string `full`, empty object `{}` (terminal `full` default), and the existing `quick` / `sketch_budget` zero cases.
- **`invoke-plan-validator-if-not-quick.sh` guards**: missing `PLAN_FILE`, empty `DESIGN_TMPDIR`, and empty `CLAUDE_PLUGIN_ROOT` each produce a non-zero exit (asserted under `set +e`).
- **Full-tier validator outcomes**: `fixtures/parse-plan-commands/basic-plan.md` for `VALIDATE_STATUS=ok`, and `fixtures/validate-plan-commands/demo-plan.md` for `VALIDATE_STATUS=defects-found` with `VALIDATE_DEFECT_COUNT=1` and `STEP_COMPLETED=VALIDATE_PLAN_COMMANDS`.
