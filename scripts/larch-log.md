# larch-log.sh contract

`scripts/larch-log.sh` is the router for committed larch runtime logs under
`larch-logs/<skill>/<run-id>/`.

Primary verbs:

- `init` creates `manifest.json`. Schema version 2 auto-captures
  `operator_cwd` from the caller's `$PWD` and `operator_repo_root` from
  `git -C "$PWD" rev-parse --show-toplevel`; outside a git repo,
  `operator_repo_root` is `null`. These provenance fields are written to
  the manifest directly and are not passed through the batch payload
  redaction pipeline.
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
`plan-goals` sanitizer must contain a non-empty `## Implementation Plan` section
that is not a pointer-only placeholder. Batches that declare the `json-lines`
sanitizer must be empty or contain one valid JSON value per non-empty line.
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

## `--no-push` discipline

`commit` pushes by default. Callers should pass `--no-push` when a subsequent
branch push, force-with-lease push, or code-commit push is guaranteed to follow
and can carry the larch-log commit together with nearby work. This avoids
standalone larch-log-only push events.

Use a direct push (no `--no-push`) when:

- The caller is a terminal lifecycle step with no later push guaranteed (e.g.,
  the `PR_CLOSED=true` teardown path in `implement-finalize.sh`, where the PR
  branch has already been merged or removed).
- Omitting the push would violate a downstream invariant (e.g., the ci-merge
  pre-merge flush in `ship-pr.sh`, where `merge-pr.sh` requires
  `local HEAD == remote PR headRefOid`; an unpushed local commit would fail
  that check and stall the merge).

In `/implement`, the rebase-retry flush (`scripts/ship-pr.sh`, Step 8b path)
is the canonical `--no-push` call site — the surrounding force-push carries it.

Related files: `scripts/lib-larch-log.sh`, `scripts/larch-log-batches.sh`, and
the `scripts/test-larch-log.sh` harness.
