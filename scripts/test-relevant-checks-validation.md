# test-relevant-checks-validation.sh

Purpose: regression-test validation and noclobber allocation in `scripts/run-relevant-checks-captured.sh`.

The harness rejects invalid `--site` labels, tmpdirs outside the accepted session roots, missing tmpdirs, relative tmpdirs, symlink tmpdirs, and `/tmp` paths nested deeper than direct children (e.g., `/tmp/foo/claude-implement-bar`). It also asserts that direct `/tmp/claude-implement-*` children DO validate (the `session-setup.sh` cache-unavailable fallback path), and pre-creates an attempt log to assert that the helper allocates the next attempt without clobbering the existing file.

Primary callers: `make test-relevant-checks-validation` and `make test-harnesses`.

Edit in sync: update this harness with `scripts/run-relevant-checks-captured.sh` and `scripts/run-relevant-checks-captured.md` whenever site grammar, tmpdir containment, failure reason tokens, or attempt allocation changes.
