# Run-log Python CLI contract

`python3 python/cli.py run-log ...` owns run-log staging, validation, and publication.
The language-neutral URI, provider, archive, cache, sync, and error rules live
in [Run-log storage contracts](run-log-archive.md).

## Envelope

Lifecycle verbs emit:

```text
LOG_WRITTEN=true|false
LOG_PATH=<path-or-empty>
BYTES=<n>
SHA256=<hex-or-empty>
COMMIT_SHA=<hex-or-empty>
UNCHANGED=true|false
```

Validation and I/O failures use the same envelope with `LOG_WRITTEN=false`,
empty `LOG_PATH`, empty `SHA256`, empty `COMMIT_SHA`, `BYTES=0`,
`UNCHANGED=false`, and `ERROR=<message>`.

`COMMIT_SHA` is a legacy compatibility field and remains empty for current
run-log operations. It does not imply a Git write.

The CLI owns mechanics, not content classification. A scrub or recognized
secret-survival failure blocks publication, but a clean pattern scan does not
make a log public-safe. See the canonical
[artifact classification and redaction contract](security/artifacts-redaction-and-publication.md#redaction-invariants).

## Verbs

- `run-log init`
- `run-log write`
- `run-log write-round`
- `run-log append`
- `run-log exists`
- `run-log manifest`
- `run-log flush`
- `run-log refresh`
- `run-log capture-transcript`
- `run-log verify-completeness`
- `run-log append-entry`
- `run-log append-failure`
- `run-log publish-breadcrumbs`
- `run-log archive`
- `run-log materialize`
- `run-log publish`
- `run-log sync`
- `run-log migrate-layout plan|apply|verify`
- `run-log lifecycle-start`
- `run-log lifecycle-finalize`
- `run-log lifecycle-failure`
- `run-log lifecycle-cancel`
- `run-log lifecycle-early-return`

The archive lifecycle verbs use their own machine envelopes. Provider failures
use the normalized error set in the storage contract. `run-log sync`
lists the configured `run-logs/` prefix once and emits `CORPUS_ROOT`,
`LISTED_ARCHIVES`, `PRESENT_RUNS`, `DOWNLOADED_RUNS`, `REPAIRED_RUNS`, and
`SYNC_OK=true`. See [Run-log storage contracts](run-log-archive.md).

Storage preflight and lifecycle start resolve repository-root
`tools-config.toml`, derive the client repository from local Git origin, list
at most one result under the exact `larch/<client-repo>/` prefix, and emit:

```text
STORAGE_BASE_URI=<canonical base>
CLIENT_REPO=<derived repository name>
TOOL_REPO_URI=<canonical base>/larch/<client-repo>
RUN_LOGS_URI=<tool repository URI>/run-logs/
PREFLIGHT_OK=true
```

Lifecycle start emits the first four values with its lifecycle envelope.
Persisted context pins the same tool URI, client repository, and
storage-origin ID; publication fails if config, environment, or Git identity
changes mid-run.

The universal lifecycle starts each invocation with a declared skill and either
a caller-supplied `--run-id` or a generated UUID after the configured prefix
preflight succeeds. `--log-root <absolute-path>` selects specialized staging;
`--adopt-existing` adopts a matching manifest already created there. The start
envelope returns `CONTEXT_FILE`, whose durable JSON record binds repository,
tool repository URI, client repository, storage-origin ID, skill, run ID, log
root, and run directory. Child runs also record the
parent skill and run ID, but retain their own archive. Every terminal verb
writes `final-report.md`, records a missing transcript as an execution issue
when capture is unavailable, and attempts the same create-only publication.
Publication failure returns nonzero and retains the durable pending archive.

## One-time tool-first S3 migration

`run-log migrate-layout` is the operator-only command for
`character-ai/larch#7966`. It migrates the frozen larch-tool corpora from:

```text
s3://zhupanov/larch/run-logs/
s3://zhupanov/agent-lint/run-logs/
```

to:

```text
s3://zhupanov/larch/larch/run-logs/
s3://zhupanov/larch/agent-lint/run-logs/
```

`plan` downloads, validates, and hashes every source archive. It writes a
self-hashed canonical plan. `apply` requires
`--authorize-live-migration`. It creates missing target objects, verifies each
downloaded target, and writes a resumable report. `verify` requires
`--authorize-report-publication`. It independently checks the complete source
and target inventories, materializes every target with the normal reader, and
publishes the final report create-only under `migration-reports/`.

The command accepts only the issue's exact S3 roots in live mode. It never
deletes or overwrites an object. Modern archives keep their exact bytes.
Pinned legacy larch archives are rebuilt with a canonical root
`archive-manifest.json`, then checked against the pinned source-member
inventory. Keep the private work directory, plan, and partial report until
verification succeeds so an interrupted apply can resume from the same plan.

`exists` exits 0 only after argument, log-root, slug, and batch validation
succeed. It sets `UNCHANGED=true` when the batch file exists.

`run-log refresh` keeps the legacy `REFRESH_COMMITTED=true` success field, but
an implement refresh now updates only the mutable session staging tree. It
does not commit or publish that snapshot. Skip and failure paths emit
`REFRESH_COMMITTED=false REASON=<token>`.

`run-log capture-transcript` always exits 0 for terminal statuses and emits
`SESSION_TRANSCRIPT_STATUS=<status>`.

Implement Step 18 captures the transcript before its final execution-issues
flush. A failed final flush or archive publication returns nonzero and retains
the session; only a verified remote object plus unpacked cache permits teardown.

`verify skill-called` preserves the `VERIFIED=true|false` and `REASON=<token>`
contract. Malformed regex faults exit 1 with stderr only.

## `token measure-cache-efficiency`

Run:

```bash
python3 python/cli.py token measure-cache-efficiency
```

The command ranks cache-create versus cache-read outliers per run and per step.
It synchronizes the current repository once, then reads `token-report.json` and
`token-report-final.json` from the unpacked cache. It also uses the existing
ledger fallback from `report_tokens_scan.py` when available.

Output is measurement only. It does not change token capture, report JSON
shapes, or CI gates.

The consumer repo root is resolved once before synchronization, not from the
plugin checkout. The command writes under
the `measure-cache-efficiency` owner in the [analyzer state tree](analysis-state.md)
and prints its absolute path:

```text
WROTE<TAB><absolute-analysis-state-path>
```

The TSV has a `# per_run` section and a `# per_step` section. The command scans
`design` and `implement` separately. Every per-run and per-step row preserves
the scan-origin skill, so matching step labels across skills stay separate.
Per-step ratios sum each run's effective cache-create contribution before
dividing by summed cache-read.

## Implement archive publication

Step 0 adopts `$IMPLEMENT_TMPDIR/larch-logs` into the lifecycle under the
implement run ID. Step 18 runs the matching lifecycle terminal verb after its
execution-issue and transcript safety nets. The shared terminal owner validates
and sanitizes that final staging tree. A successful
call creates one immutable remote object and one validated unpacked cache
directory. A failed upload returns nonzero, retains the durable pending archive,
and stops teardown. Re-entry retries the content-pinned pending archive.

## Git isolation

Run-log staging, archive publication, cache promotion, and sync do not create
branches, commits, pushes, pull requests, or merges.
