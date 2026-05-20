# verify-run-log-completeness.sh contract

## Purpose

`scripts/verify-run-log-completeness.sh` checks a committed `larch-logs/implement/<RUN_ID>/`
directory against the required-file manifest at `docs/run-logs-required-files.tsv` and emits
`OK` or `MISSING=<comma-list>`.

## Interface

```text
verify-run-log-completeness.sh <larch-logs/implement/RUN_ID/>
```

Exit 0 with `OK` when all required files are present. Exit 1 with `MISSING=<comma-separated
relative paths>` when one or more required files are absent. Exit 1 with an error message on
stderr when the manifest or run dir cannot be found.

## Manifest format

`docs/run-logs-required-files.tsv` is a tab-separated file with columns:
`relative_path`, `condition`, `batch_slug`, `extension`. Only rows with
`condition=always` are checked. The first row (header) is skipped automatically.

## Callers

- `make test-verify-run-log-completeness` — local verification
- CI workflow `.github/workflows/verify-run-logs.yml` — validates newly added run dirs on PRs

## Edit-in-sync

Update `docs/run-logs-required-files.tsv` when the set of required committed files changes
(e.g., a new batch is added or an existing batch is removed). Update
`docs/run-logs.md` in the same PR. The test harness is `scripts/test-verify-run-log-completeness.sh`.
