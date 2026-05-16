# larch-log.sh contract

`scripts/larch-log.sh` is the router for committed larch runtime logs under
`larch-logs/<skill>/<run-id>/`.

Primary verbs:

- `init` creates `manifest.json`. Schema version 2 auto-captures
  `operator_cwd` from the caller's `$PWD`, `operator_repo_root` from
  `git -C "$PWD" rev-parse --show-toplevel`; outside a git repo,
  `operator_repo_root` is `null`, and `model_roster.main` from
  `${CLAUDE_CODE_MODEL:-${CLAUDE_MODEL:-unknown}}`. These provenance fields are written to
  the manifest directly and are not passed through the batch payload
  redaction pipeline.
- `write` atomically replaces replace-mode batches.
- `append` atomically appends append-mode NDJSON batches.
- `exists` probes a batch path.
- `manifest` updates mutable manifest fields. Values that look like JSON-native scalars (`null`, `true`, `false`, integers) are passed via `--argjson` so they are stored with the correct JSON type; all other values are passed via `--arg` (stored as strings). This matters for numeric fields like `pr_number`.
- `commit` stages and commits one run directory without pushing. It refuses
  with a stderr diagnostic when `$IMPLEMENT_TMPDIR/post-merge-sentinel` exists
  or when the current branch is `main`/the `origin/HEAD` default branch,
  preventing post-merge log-only commits.

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
`plan-goals` sanitizer must contain a non-empty `## Implementation Plan` section
that is not a pointer-only placeholder. Batches that declare the `json-lines`
sanitizer must be empty or contain one valid JSON value per non-empty line.
Batches that declare the `json-object` sanitizer must parse as one JSON object.
Batches that declare the `mermaid` sanitizer (in `larch-log-batches.sh`) also use
`sanitize-mermaid-fragment.sh --from-md` and fail closed on rejection; no
current batch uses the Mermaid sanitizer — it is reserved for future opt-in.

**Log-root resolution** is single-tier (see `lib-larch-log.sh`):

1. `$LARCH_LOG_ROOT`, set by the required `--log-root <dir>` flag or explicitly
   exported for test isolation.

The `init`, `write`, `append`, `exists`, `manifest`, and `commit` verbs require
an absolute `--log-root <dir>` unless `$LARCH_LOG_ROOT` is already exported.
`/implement` passes `$IMPLEMENT_TMPDIR/larch-logs` explicitly so in-progress
runtime payloads stay out of the git working tree until `commit` is called.

`REPO_ROOT` (used by `commit`) and `LARCH_LOG_REPO_ROOT` (used by `commit` via
`larch_log_repo_run_dir`) both resolve via `git -C "$PWD" rev-parse --show-toplevel`
at script load time so logs land in the consumer repo rather than the plugin install
cache. Both remain empty when invoked outside a git worktree; `commit` fails with
a descriptive error in that case.

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

## Push Ownership

`commit` never pushes. `/implement` log persistence is owned by
`scripts/larch-log-flush.sh`, which is tail-called by commit primitives after
business commits, and by the surrounding lifecycle push that carries those
commits to the remote. Dedicated larch-log-only pushes are intentionally avoided.

Related files: `scripts/lib-larch-log.sh`, `scripts/larch-log-batches.sh`, and
the `scripts/larch-log-flush.sh` helper plus `scripts/test-larch-log.sh`
harness.
