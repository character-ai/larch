# compose-collector-failure-log.sh

Composes a guaranteed-non-empty failure log from a `collect-agent-results.sh` collector record and its reviewer output sidecars. Output always contains the structured collector record first, so `execution-issues.md` entries are never empty even when the reviewer output file and its `.diag` are both absent or zero-byte.

## Contract

```
compose-collector-failure-log.sh \
    --reviewer-file <path> \
    --structured-record <record-line> \
    --output <path>
```

- `--reviewer-file <path>`: the `REVIEWER_FILE=` path from the collector's structured output line. May not exist; may be 0 bytes; both are valid.
- `--structured-record <record-line>`: the full `REVIEWER_FILE=…|TOOL=…|STATUS=…|EXIT_CODE=…|HEALTHY=…|FAILURE_REASON=…` line as emitted by `collect-agent-results.sh`. Required; must be non-empty.
- `--output <path>`: destination file. Must be writable; parent directory must exist.

Exit 0 on success. Exit 2 on invalid arguments (`--structured-record` empty, `--output` parent missing, unknown flag).

## Output structure

```
## Structured collector record

<record-line>

## Reviewer output (<REVIEWER_FILE>)

<contents, or "(empty: <path>)" / "(file missing: <path>)" / "(no path provided)">

## Reviewer stderr (<REVIEWER_FILE>.diag)

<contents, or "(empty: <path>)" / "(file missing: <path>)">
```

The `.diag` section is omitted entirely when `--reviewer-file` is empty.

## Atomic write

Output is written to a `mktemp` file and `mv`-promoted to `--output`, so a partial write never lands at the destination path.

## Primary callers

- `/design` heavy-worker (Step 3 plan-review) — for each non-`OK` collector status in `skills/design/references/plan-review.md` failure-logging section.

## Harness

`scripts/test-compose-collector-failure-log.sh` — 10 cases covering happy path, empty/missing files, validation errors, and atomic write. Wired into `make lint`.

## Edit-in-sync

When changing the output format (section headers, placeholder strings), update:
- This `.md` sibling
- `scripts/test-compose-collector-failure-log.sh` (section-header assertions)
- `skills/design/references/plan-review.md` (the example in the failure-logging recipe block)
