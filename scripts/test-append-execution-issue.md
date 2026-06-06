# test-append-execution-issue.sh

Harness for `scripts/append-execution-issue.sh`. The primary contract lives in
`scripts/append-execution-issue.md`. Wired into `make lint` via the
`test-append-execution-issue` target.

Run directly:

```bash
scripts/test-append-execution-issue.sh
```

The test verifies usage envelopes with `USAGE=`, missing required arguments, and
successful appends under the `Warnings` category.
