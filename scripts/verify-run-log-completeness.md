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

Data rows must remain tab-delimited. Space-aligned edits are invalid and can
mis-bind columns in the verifier.

- `always` — required for every committed `/implement` run dir covered by the manifest.
- `step5` — required once the Step 5 review/tally phase has been reached.
- `step7a` — required once the Step 7a pre-bump flush has been reached.
- `step8` — required once the Step 8 version-bump phase has been reached.
- `step9a1` — required once the Step 9a.1 OOS/statistics phase has been reached.
- `exn-agg-validate-fail` — applies only when `execution-issues.ndjson` records a findings-aggregator validation failure (`merged output failed validation`). When active, at least one `round-*/aggregator-validate.stderr` file must exist in the run directory (glob row in the TSV).
- `exn-agg-dispatch-fail` — applies only when `execution-issues.ndjson` records a findings-aggregator dispatch failure (`dispatch-with-waterfall exited non-zero` or `DISPATCH_OK=false`). When active, at least one `round-*/aggregator-dispatch.stderr` file must exist.

`relative_path` may contain a single `*` segment (for example `round-*/aggregator-validate.stderr`) to require a matching committed round artifact when the corresponding `exn-*` condition is active.

The verifier infers later-phase reachability from committed run-dir signals
already present in the tree (for example `final-summary.md`, `oos-issues.ndjson`,
`manifest.json` `pr_number`, or `status=done`) so pre-Step-7a and mid-run
partial directories do not produce false missing-file failures for later batches.

`batch_slug` normally matches `scripts/larch-log-batches.sh`. The reserved value
`direct-file` covers committed files that are part of the run-dir contract but
are written outside `larch-log.sh` batch plumbing, such as `final-summary.md`.

## Testing override

When `LARCH_VERIFY_MANIFEST` is set to a non-empty value, the verifier reads
that TSV instead of `docs/run-logs-required-files.tsv`. This is intended for
harnesses only; production callers should omit it.

- **Absolute paths** are used as given.
- **Relative paths** are resolved from the repository root (the directory
  containing `docs/` inferred from `verify-run-log-completeness.sh`'s install
  location), not from the process current working directory. A leading `./` is
  stripped; repeated `//` segments in the joined path are collapsed. `..`
  segments in the relative tail are rejected, and when the manifest parent
  directory exists the resolved path is canonicalized and must remain under the
  repository root.

Do **not** export `LARCH_VERIFY_MANIFEST` from shell profiles, shared CI
images, or other ambient environment: an exported value silently overrides the
canonical manifest. Prefer a per-command assignment
(`LARCH_VERIFY_MANIFEST=… cmd …`) when an explicit override is required. The
`make test-verify-run-log-completeness` recipe runs under `env -u
LARCH_VERIFY_MANIFEST`, and `scripts/test-verify-run-log-completeness.sh`
unsets any inherited value at startup so default-case assertions use
`docs/run-logs-required-files.tsv`.

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
