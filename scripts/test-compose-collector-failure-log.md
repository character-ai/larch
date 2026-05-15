# test-compose-collector-failure-log.sh

Regression harness for `scripts/compose-collector-failure-log.sh`.

Primary callers: `make test-compose-collector-failure-log`, and the
`test-harnesses-4` shard through `make test-harnesses`.

Run directly:

```bash
scripts/test-compose-collector-failure-log.sh
```

It covers:

- happy path: reviewer file and `.diag` both non-empty — structured record, reviewer output, and stderr sections present in order
- empty reviewer file: `(empty: <path>)` placeholder in reviewer-output section
- missing reviewer file: `(file missing: <path>)` placeholder
- empty `.diag`: `(empty: <path>)` placeholder in stderr section
- missing `.diag`: `(file missing: <path>)` placeholder in stderr section
- empty `--structured-record`: exit 2 with diagnostic on stderr
- missing `--output`: exit 2 with diagnostic on stderr
- `--output` parent missing: exit 2 with diagnostic on stderr
- atomic write: output path absent when script exits non-zero
- non-empty invariant: all valid cases produce a non-empty output file

Update alongside `scripts/compose-collector-failure-log.sh`.
