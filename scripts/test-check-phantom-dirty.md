# test-check-phantom-dirty.sh

Regression harness for `scripts/check-phantom-dirty.sh`.

The primary contract lives in `scripts/check-phantom-dirty.md`. This harness
creates temporary git repositories and verifies the wrapper's status mapping,
NUL-delimited path preservation, baseline-failure degradation, tracked-only
classification, and `--step` token validation.

Run it with:

```bash
make test-check-phantom-dirty
```

## Edit-in-sync

Update this harness with any behavior change to `scripts/check-phantom-dirty.sh`.
