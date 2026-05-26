# test-decompose-aggregator.sh

Offline regression for `decompose-aggregator.sh`: concatenation, merge prompt presence, `AGGREGATOR_STATUS` against a stub waterfall. Also verifies the aggregator builds its single-slot row with `tool=codex` and threads `--require-result-pattern '^[[:space:]]*## Recommendation'` to `dispatch-with-waterfall.sh`.

Run via `make test-decompose-aggregator` or `bash skills/design/scripts/test-decompose-aggregator.sh`.
