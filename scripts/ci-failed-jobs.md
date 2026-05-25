# ci-failed-jobs.sh

`scripts/ci-failed-jobs.sh` classifies failed GitHub Actions jobs from a run so
`scripts/ship-pr.sh` can replay the fixable ones locally without executing
strings from the GitHub API.

## Interface

```text
ci-failed-jobs.sh --run-id RUN_ID --repo OWNER/REPO [--output-tsv PATH]
```

The helper runs:

```text
gh run view RUN_ID --repo OWNER/REPO --json jobs --jq '.jobs[] | select(.conclusion=="failure") | .name'
```

`jobs` is the `gh run view --json` field this helper depends on.

## Output

Machine-readable output is emitted through `scripts/lib-quiet.sh` using
`emit_kv`; `larch_quiet_init` runs before any `emit_kv` call.

- `FAILED_JOBS_COUNT=N`
- `FAILED_JOBS_FIXABLE=job,job:shard`
- `FAILED_JOBS_UNFIXABLE=job=reason,job:shard=reason`

When `--output-tsv` is supplied, the file contains:

```text
JOB_NAME<TAB>SHARD<TAB>CLASS
```

There is intentionally no local command column. `ship-pr.sh` owns the fixed
case-statement argv dispatcher.

## Exit Codes

- `0`: gh returned job data, including when no jobs failed.
- `1`: gh failed for a non-transient reason.
- `2`: usage error.
- `3`: gh reported `is still in progress; logs will be available`.

The script does not source `lib-net.sh`; callers decide whether to retry
transient network failures.

## Mapping

Fixable jobs are `lint`, `lint-mermaid`, `shellcheck`, `test-harnesses`,
`agent-lint`, `agnix`, `smoke-dialectic`, and `agent-sync`. `gitleaks` and
`trufflehog` are `no-local-equivalent` because CI runs history scans.

Matrix names of the form `test-harnesses (7)` normalize to
`JOB_NAME=test-harnesses` and `SHARD=7`. Non-digit shard text is ignored, so
`test-harnesses (abc)` falls back to the unsharded local target. Job names must
match `^[A-Za-z][A-Za-z0-9_-]*$`; malformed names are classified as
`no-local-equivalent`.

## Harness

Covered by `scripts/test-ci-failed-jobs.sh`.
