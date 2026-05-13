# larch-log.sh contract

`scripts/larch-log.sh` is the router for committed larch runtime logs under
`larch-logs/<skill>/<run-id>/`.

Primary verbs:

- `init` creates `manifest.json`.
- `write` atomically replaces replace-mode batches.
- `append` atomically appends append-mode NDJSON batches.
- `exists` probes a batch path.
- `manifest` updates mutable manifest fields. Values that look like JSON-native scalars (`null`, `true`, `false`, integers) are passed via `--argjson` so they are stored with the correct JSON type; all other values are passed via `--arg` (stored as strings). This matters for numeric fields like `pr_number`.
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
`redact-tmpdir-paths.sh` and `redact-secrets.sh`. Batches that declare the
`mermaid` sanitizer (in `larch-log-batches.sh`) also use
`sanitize-mermaid-fragment.sh --from-md` and fail closed on rejection; no
current batch uses this sanitizer — it is reserved for future opt-in.

**Log-root resolution** is single-tier (see `lib-larch-log.sh`):

1. `$LARCH_LOG_ROOT`, set by the required `--log-root <dir>` flag or explicitly
   exported for test isolation.

The `init`, `write`, `append`, `exists`, `manifest`, and `commit` verbs require
an absolute `--log-root <dir>` unless `$LARCH_LOG_ROOT` is already exported.
`/implement` passes `$IMPLEMENT_TMPDIR/larch-logs` explicitly so in-progress
runtime payloads stay out of the git working tree until `commit` is called.

`REPO_ROOT` (used by `commit`) and `LARCH_LOG_REPO_ROOT` (used by `write`/`append`/`init`
via `lib-larch-log.sh`) both resolve via `git -C "$PWD" rev-parse --show-toplevel` so
logs land in the consumer repo rather than the plugin install cache. Both use the
two-assignment pattern to avoid `(A || B) && C` shell-precedence issues; both fall
back to `SCRIPT_DIR/..` outside a git repo.

**`commit` copy semantics**: `commit` computes `src_path` via `larch_log_run_dir`
(which resolves under the explicit log root) and `repo_path` via
`larch_log_repo_run_dir` (always `$LARCH_LOG_REPO_ROOT/larch-logs/<skill>/<run-id>/`).
When the two paths differ, `commit` copies the staging tree into the repo path before
running `git add` / `git commit`. When they are equal (the explicit log root already
points at the canonical repo subtree), no copy is performed.

**Batch registry**: all slugs, extensions, modes, and sanitizer hooks live in
`scripts/larch-log-batches.sh`. See `scripts/larch-log-batches.md` for the full
list, including `session-transcript` (the redacted Claude Code session `.jsonl`
captured at Step 18 of `/implement` for post-hoc auditability).

Related files: `scripts/lib-larch-log.sh`, `scripts/larch-log-batches.sh`, and
the `scripts/test-larch-log.sh` harness.
