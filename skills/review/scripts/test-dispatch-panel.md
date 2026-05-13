# test-dispatch-panel.sh Contract

Regression harness for `skills/review/scripts/dispatch-panel.sh`.

It uses a stub Claude subprocess launcher to verify the both-down branch emits `PANEL_MODE=both-down`, launches one slot, and writes the expected sentinel.

Run with `bash skills/review/scripts/test-dispatch-panel.sh` or `make test-dispatch-panel`.
