# test-read-result-env.sh

Regression harness for `scripts/read-result-env.sh`.

## Coverage

The harness exercises allowlisted output, dropped non-allowlisted keys, repeated `--allow`, blank-line handling, malformed nonblank lines, first-`=` splitting for primary and fallback inputs, WARN/ERROR replay, symlink/missing/non-regular primary refusal, compatibility fallback behavior, symlink breadcrumb preservation, fallback input refusal, carriage-return rejection, single-quote encoding, sourceability, and the empty-output case when no keys are allowlisted.

## Run

```bash
bash scripts/test-read-result-env.sh
```

Or `make test-read-result-env`.

## Wiring

Relevant-checks routing runs this harness for edits to `scripts/read-result-env.sh`, `scripts/read-result-env.md`, `scripts/test-read-result-env.sh`, or this contract file. Structure checks additionally pin the helper executable and its `/design` call sites.
