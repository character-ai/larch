# Run-log Python CLI contract

`python3 python/cli.py run-log ...` owns run-log staging, validation, and publication.

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

For `--skill implement`, `run-log commit` validates and sanitizes the mutable
staging tree. It emits `SECRET_SCRUB_VIOLATIONS=N` and does not create a Git
commit. Other skill cutovers remain separate work.

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
- `run-log commit`
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
- `run-log lifecycle-start`
- `run-log lifecycle-finalize`
- `run-log lifecycle-failure`
- `run-log lifecycle-cancel`
- `run-log lifecycle-early-return`

The archive lifecycle verbs use their own machine envelopes. `run-log sync`
lists the configured `run-logs/` prefix once and emits `CORPUS_ROOT`,
`LISTED_ARCHIVES`, `PRESENT_RUNS`, `DOWNLOADED_RUNS`, `REPAIRED_RUNS`, and
`SYNC_OK=true`. See [Run-log archive format](run-log-archive.md).

The universal lifecycle starts each invocation with a UUID and declared skill
name after the configured bucket preflight succeeds. Child runs also record the
parent skill and run ID, but retain their own archive. Every terminal verb
writes `final-report.md`, records a missing transcript as an execution issue
when capture is unavailable, and attempts the same create-only publication.
Publication failure returns nonzero and retains the durable pending archive.

`exists` exits 0 only after argument, log-root, slug, and batch validation
succeed. It sets `UNCHANGED=true` when the batch file exists.

Git-publishing paths retain default-branch and post-merge stderr-only hard stops.

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

Step 18 runs `run-log commit` after its execution-issue and transcript safety
nets, then calls `run-log publish` for the final sanitized tree. A successful
call creates one immutable remote object and one validated unpacked cache
directory. A failed upload returns nonzero, retains the durable pending archive,
and stops teardown. Re-entry retries the content-pinned pending archive.

## Post-merge Git history

Past regressions: #2120, #2128, #2140, #2182, and #2552 (PR #2530 reintroduced the pattern via a `LARCH_LOG_COMMIT_POSTMERGE_SHIP_PR=1` bypass in `run-log`).

Current implement runs do not publish run logs through Git. The post-merge
commit prohibition still applies to every repository mutation and to the
uncut-over skill paths.
