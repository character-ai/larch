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

**Repo-root resolution**: `REPO_ROOT` (used by `commit`) and `LARCH_LOG_REPO_ROOT`
(used by `write`/`append`/`init` via `lib-larch-log.sh`) both resolve via
`git -C "$PWD" rev-parse --show-toplevel` so logs land in the consumer
repo's `larch-logs/` tree rather than the plugin install cache. Resolution
uses a two-assignment pattern (`VAR="$(git ...)" || true; [ -n "$VAR" ] || VAR="$(fallback)"`) to avoid the
`(A || B) && C` shell-precedence trap where `C` (`pwd -P`) always runs even when `A` (git) succeeds. Both fall
back to `SCRIPT_DIR/..` when invoked outside a git repo. `LARCH_LOG_ROOT`
in the environment overrides the `lib-larch-log.sh` path (existing escape hatch).

**Batch registry**: all slugs, extensions, modes, and sanitizer hooks live in
`scripts/larch-log-batches.sh`. See `scripts/larch-log-batches.md` for the full
list, including `session-transcript` (the redacted Claude Code session `.jsonl`
captured at Step 18 of `/implement` for post-hoc auditability).

Related files: `scripts/lib-larch-log.sh`, `scripts/larch-log-batches.sh`, and
the `scripts/test-larch-log.sh` harness.
