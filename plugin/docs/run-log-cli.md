# Run-log CLI contract

`python3 python/cli.py run-log ...` owns the remaining Python run-log staging,
validation, and publication verbs. `scripts/larch.sh run-log manifest ...` owns
durable manifest updates. `scripts/larch.sh run-log ...` also owns storage
preflight and the five shared lifecycle verbs.
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

## Remaining Python-owned verbs

- `run-log init`
- `run-log write`
- `run-log write-round`
- `run-log append`
- `run-log exists`
- `run-log checkpoint`
- `run-log refresh`
- `run-log prepare-terminal-snapshot`
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
## Rust-owned manifest updates

`scripts/larch.sh run-log manifest --log-root <root> --skill <skill> --run-id
<run-id> --field <key=value>` preserves the legacy argument and `LOG_*`
envelope contract. It accepts existing schema-v2 manifests, rejects immutable
identity fields, and applies status, step, reserved, and extension updates.
Historical v1 manifests remain readable through the shared reader but are not
write targets; unknown or malformed versions fail closed without rewriting the
file.

`larch_adapters::run_log_manifest::ManifestStore` is the only durable
manifest writer. It publishes through `larch_adapters::atomic_write_utf8_in`,
which writes and syncs a same-directory temporary file, atomically renames it,
then syncs the containing directory.

The Rust-owned archive lifecycle verbs use their own machine envelopes.
Provider failures
use the normalized error set in the storage contract. `run-log sync`
lists the configured `run-logs/` prefix once and emits `CORPUS_ROOT`,
`LISTED_ARCHIVES`, `PRESENT_RUNS`, `DOWNLOADED_RUNS`, `REPAIRED_RUNS`, and
`SYNC_OK=true`. See [Run-log storage contracts](run-log-archive.md).

Storage preflight and lifecycle start resolve repository-root
`tools-config.toml` plus the environment and derive the client repository from
local Git origin. Enabled storage lists at most one result under the exact
`larch/<client-repo>/` prefix. Disabled storage invokes no provider command.
Both emit:

```text
RUN_LOG_STORAGE=<enabled|disabled>
RUN_LOG_STORAGE_REASON=<closed-reason-token>
STORAGE_BASE_URI=<canonical base or empty>
CLIENT_REPO=<derived repository name>
TOOL_REPO_URI=<canonical tool repository URI or empty>
RUN_LOGS_URI=<run-logs URI or empty>
STORAGE_PREFLIGHT=<ok|skipped-disabled>
PREFLIGHT_OK=true
```

Lifecycle start adds `RUN_ID`, `SKILL`, `LOG_ROOT`, `RUN_DIR`, `CONTEXT_FILE`,
and `LIFECYCLE_STARTED=true`. In disabled mode it prints:

```text
**⚠ Run-log publication is disabled (<reason>). This skill will run, but no remote run-log archive or synchronized cache entry will be created.**
```

Persisted context pins publication mode, reason, client repository, and either
the enabled canonical storage identity or disabled local namespace ID. An
enabled run fails if config, environment, Git origin, or storage identity
changes. A disabled run stays disabled even if configuration appears later.

The universal lifecycle starts each invocation with a declared skill and either
a caller-supplied `--run-id` or a generated UUID after lifecycle admission
succeeds. `--log-root <absolute-path>` selects specialized staging;
`--adopt-existing` adopts a matching manifest already created there. The start
envelope returns `CONTEXT_FILE`, whose durable JSON record binds repository,
publication identity, skill, run ID, log root, and run directory. Child runs
also record the parent skill and run ID, but retain their own run identity.
Every terminal verb writes `final-report.md` and records a missing transcript
as an execution issue when capture is unavailable.

Enabled success emits `RUN_LOG_PUBLICATION=published`,
`LIFECYCLE_FLUSHED=true`, and `LIFECYCLE_TERMINALIZED=true` with verified
remote and cache fields. Disabled success invokes no archive, provider, cache,
or pending-publication operation. It warns:

```text
**⚠ Run-log publication skipped because storage was disabled at lifecycle start (<reason>).**
```

It then emits:

```text
RUN_ID=<run-id>
SKILL=<skill>
OUTCOME=<terminal-outcome>
RUN_LOG_STORAGE=disabled
RUN_LOG_STORAGE_REASON=<closed-reason-token>
RUN_LOG_PUBLICATION=skipped-disabled
LIFECYCLE_FLUSHED=false
LIFECYCLE_TERMINALIZED=true
```

Disabled success removes staging and context. Terminal errors retain diagnostic
state, emit `RUN_LOG_PUBLICATION=failed`, `LIFECYCLE_FLUSHED=false`, and
`LIFECYCLE_TERMINALIZED=false`, then return nonzero.

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

`run-log checkpoint` stages a narrow mutable recovery snapshot. It does not
terminalize the lifecycle or publish an archive.

`run-log prepare-terminal-snapshot` is the Step 18 preparation owner. After the
closing token and timing marks, it refreshes the final summary, token and timing
reports, vendor diagnostics, architectural outcome batches, ship handoff,
session transcript, execution issues, and manifest reachability. It emits
`TERMINAL_SNAPSHOT_STATUS=prepared|failed` and the exact
`SESSION_TRANSCRIPT_STATUS`. Failure returns nonzero and preserves staging.

`run-log capture-transcript` always exits 0 for terminal statuses and emits
`SESSION_TRANSCRIPT_STATUS=<status>`.

Implement Step 18 always attempts transcript capture when a source is
configured, then appends the final execution-issues tail. A failed snapshot or
enabled archive publication returns nonzero and retains the session. Step 19
cleanup requires `$IMPLEMENT_TMPDIR/.run-log-terminalized`, which Step 18 writes
only after a verified remote object plus unpacked cache, successful
`skipped-disabled` terminalization, or explicit `skipped-suppressed` state.

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
implement run ID. Step 18 prepares the complete final snapshot, then runs the
matching lifecycle terminal verb exactly once. The shared terminal owner
validates and sanitizes that final staging tree when publication is enabled.
Enabled success creates one immutable remote object and one validated unpacked
cache directory. A failed upload returns nonzero, retains the durable pending
archive, and blocks Step 19. Re-entry retries the content-pinned pending
archive. Disabled success creates none of those artifacts and records its
terminal state before Step 19 removes session material.

## Git isolation

Run-log staging, archive publication, cache promotion, and sync do not create
branches, commits, pushes, pull requests, or merges.
