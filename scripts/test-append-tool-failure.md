# test-append-tool-failure.sh

Harness for `scripts/append-tool-failure.sh`. The primary contract lives
in `scripts/append-tool-failure.md`. Wired into `make lint` via the
`test-append-tool-failure` target.

Run directly:

```bash
scripts/test-append-tool-failure.sh
```

The test creates temporary execution-issues logs and captured-output
files, then verifies verbatim preservation, category routing, redaction,
verdict / retry-count header suffixes, missing-input failure behavior, and
log preservation when the delegated append helper fails.
