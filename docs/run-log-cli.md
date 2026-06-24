# Run-log Python CLI contract

`python3 python/cli.py run-log ...` owns the committed run-log lifecycle.

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

`run-log commit` may also emit `SECRET_SCRUB_VIOLATIONS=N`.
`run-log flush` reports scrub warnings on stderr only.

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

`exists` exits 0 only after argument, log-root, slug, and batch validation
succeed. It sets `UNCHANGED=true` when the batch file exists.

Default-branch and post-merge commit refusals remain stderr-only hard stops.

`run-log refresh` emits `REFRESH_COMMITTED=true` on commit success, or
`REFRESH_COMMITTED=false REASON=<token>` for skip/failure paths.

`run-log capture-transcript` always exits 0 for terminal statuses and emits
`SESSION_TRANSCRIPT_STATUS=<status>`.

`verify skill-called` preserves the `VERIFIED=true|false` and `REASON=<token>`
contract. Malformed regex faults exit 1 with stderr only.

## Post-merge commit history

Past regressions: #2120, #2128, #2140, #2182, and #2552 (PR #2530 reintroduced the pattern via a `LARCH_LOG_COMMIT_POSTMERGE_SHIP_PR=1` bypass in `run-log`).

If a future need arises to land merged-outcome data in the run-log tree, do it BEFORE the squash-merge (write speculative `OUTCOME=merged` into `final-summary.md` and include it in the final pre-merge log flush commit so it rides into the squash-merge tree, rollback on merge failure) — never after.
