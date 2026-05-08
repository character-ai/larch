# test-relevant-checks-validation.sh

Purpose: regression-test validation and noclobber allocation in `scripts/run-relevant-checks-captured.sh`.

The harness rejects invalid `--site` labels, tmpdirs outside the accepted session root, missing tmpdirs, relative tmpdirs, and symlink tmpdirs. It also pre-creates an attempt log and asserts that the helper allocates the next attempt without clobbering the existing file.

Primary callers: `make test-relevant-checks-validation` and `make test-harnesses`.

Edit in sync: update this harness with `scripts/run-relevant-checks-captured.sh` and `scripts/run-relevant-checks-captured.md` whenever site grammar, tmpdir containment, failure reason tokens, or attempt allocation changes.
