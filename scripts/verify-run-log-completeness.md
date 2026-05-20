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
`relative_path`, `condition`, `batch_slug`, `extension`. The first row
(header) is skipped automatically. `condition` is step-scoped:

- `always` — required for every committed `/implement` run dir covered by the manifest.
- `step5` — required once the Step 5 review/tally phase has been reached.
- `step7a` — required once the Step 7a pre-bump flush has been reached.
- `step8` — required once the Step 8 version-bump phase has been reached.
- `step9a1` — required once the Step 9a.1 OOS/statistics phase has been reached.

The verifier infers later-phase reachability from committed run-dir signals
already present in the tree (for example `final-summary.md`, `oos-issues.ndjson`,
`manifest.json` `pr_number`, or `status=done`) so pre-Step-7a and mid-run
partial directories do not produce false missing-file failures for later batches.

## Callers

- `make test-verify-run-log-completeness` — local verification
- `make test-harnesses-7` — local shard that includes the verifier harness
- `.github/workflows/ci.yaml` `test-harnesses` job (shard 7) — CI coverage via the Makefile harness

## Edit-in-sync

Update `docs/run-logs-required-files.tsv` when the set of required committed files changes
(e.g., a new batch is added or an existing batch is removed). Keep the TSV's
`batch_slug` / `extension` columns aligned with `scripts/larch-log-batches.sh`
and update `docs/run-logs.md` in the same PR. For Step-7a batches, keep
`session-transcript.jsonl` aligned with the manifest and verifier reachability
rules. The test harness is
`scripts/test-verify-run-log-completeness.sh`.
