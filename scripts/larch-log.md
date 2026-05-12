# larch-log.sh contract

`scripts/larch-log.sh` is the router for committed larch runtime logs under
`larch-logs/<skill>/<run-id>/`.

Primary verbs:

- `init` creates `manifest.json`.
- `write` atomically replaces replace-mode batches.
- `append` atomically appends append-mode NDJSON batches.
- `exists` probes a batch path.
- `manifest` updates mutable manifest fields.
- `commit` stages and commits one run directory at terminal time.

Every verb emits a quiet KEY=value envelope:

```text
LOG_WRITTEN=true|false
LOG_PATH=<path>
BYTES=<n>
SHA256=<hex>
COMMIT_SHA=<sha-or-empty>
UNCHANGED=true|false
```

Payload content is never written to stdout. Payloads pass through
`redact-tmpdir-paths.sh` and `redact-secrets.sh`; the `diagrams` batch also
uses `sanitize-mermaid-fragment.sh --from-md` and fails closed on rejection.

Related files: `scripts/lib-larch-log.sh`, `scripts/larch-log-batches.sh`, and
the `scripts/test-larch-log.sh` harness.
