# test-read-design-classification.sh

Offline regression harness for `scripts/read-design-classification.sh`.

Invocation: `bash scripts/test-read-design-classification.sh`.

It covers:

- Valid explicit-path reads for `SIMPLE`.
- `DESIGN_TMPDIR` fallback reads for `HARD`.
- Invalid classification fallback to `HARD` with the warning contract.
- Missing-file fallback to `HARD` with the warning contract.
