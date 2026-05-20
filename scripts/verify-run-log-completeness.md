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
The current manifest is scoped to committed `/implement` runs that reach the
Step 7a pre-bump flush; design-only and other pre-Step-7a bailout paths may
produce committed partial logs that omit Step-7a-only batches such as
`session-transcript.jsonl`.

## Callers

- `make test-verify-run-log-completeness` — local verification
- `make test-harnesses-7` — local shard that includes the verifier harness
- `.github/workflows/ci.yaml` `test-harnesses` job (shard 7) — CI coverage via the Makefile harness

## Edit-in-sync

Update `docs/run-logs-required-files.tsv` when the set of required committed files changes
(e.g., a new batch is added or an existing batch is removed). Keep the TSV's
`batch_slug` / `extension` columns aligned with `scripts/larch-log-batches.sh`
and update `docs/run-logs.md` in the same PR. The test harness is
`scripts/test-verify-run-log-completeness.sh`.
