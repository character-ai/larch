# test-decompose-panel-dispatch.sh

Offline regression for `decompose-panel-dispatch.sh`: eight NDJSON slots, prompt substitution, `DEGRADED_PANEL` / `PANEL_STATUS` wiring against a stub waterfall. Also verifies the panel threads `--require-result-pattern '^[[:space:]]*## Recommendation'` to the waterfall and that `panel-outputs.ndjson` rows record the dispatcher's resolved final paths from `ALL_OUTPUT_FILES_PATH` (so phase-2/phase-3 fallback content reaches operator presentation).

Run via `make test-decompose-panel-dispatch` or `bash skills/design/scripts/test-decompose-panel-dispatch.sh`.
