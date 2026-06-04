# test-design-postplan-emit.sh

Regression harness for `design-postplan-emit.sh`.

The primary contract lives in `design-postplan-emit.md`; this sibling exists for the script-documentation invariant and should be updated with that primary when harness coverage changes.

## Quiet-mode warning regression

The harness includes a default-quiet case that removes `run-params.json`, invokes `design-postplan-emit.sh` with `LARCH_QUIET_DISABLE` unset, and asserts stdout contains a `WARN=` line with the `read-design-classification` defaulting message.
