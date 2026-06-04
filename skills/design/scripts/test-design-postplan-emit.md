# test-design-postplan-emit.sh

Regression harness for `design-postplan-emit.sh`.

The primary contract lives in `design-postplan-emit.md`; this sibling exists for the script-documentation invariant and should be updated with that primary when harness coverage changes.

## Quiet-mode warning regression

The harness includes default-quiet cases with `LARCH_QUIET_DISABLE` unset: one removes `run-params.json` and one keeps a readable `run-params.json` missing `design_classification`. Both assert stdout contains a `WARN=` line with the `read-design-classification` defaulting message.
