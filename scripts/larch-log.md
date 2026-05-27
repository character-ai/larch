# larch-log.sh contract

`scripts/larch-log.sh` is the router for committed larch runtime logs under
`larch-logs/<skill>/<run-id>/`.

Primary verbs:

- `init` creates `manifest.json`. Schema version 2 records redacted provenance
  placeholders: `operator_cwd` is the stable string `"<OPERATOR_CWD>"`,
  `operator_repo_root` is `"<REPO_ROOT>"` when the caller is inside a git repo
  and `null` otherwise, and `model_roster.main` comes from
  `${CLAUDE_CODE_MODEL:-${CLAUDE_MODEL:-unknown}}`. The manifest keeps these
  fields for schema compatibility without committing operator-local absolute
  paths. New runs include an empty `steps_ran` object for per-step skip flags;
  `pr_number` and in-progress `status` are not written at init (post-flush
  lifecycle fields are owned by explicit flush paths and recovery tagging).
- `write` atomically replaces replace-mode batches.
- `write-round` copies registered per-round review artifacts from
  `--source-dir` into `round-<N>/` under the run directory. It strips `CMD_JSON`
  lines from `.meta` sidecars and removes top-level `.result` from included
  `*-output.txt.json` / `*-output-*.txt.json` tool-envelope sidecars before
  applying the normal tmpdir and secrets redaction. Session tmpdirs may retain
  raw `.meta` / JSON sidecars for retry state, but committed `round-<N>/`
  artifacts always use the trimmed form and fail closed if trimming fails. It
  writes only to the log root; `commit` later picks up the round directory.
  The allow-list includes scout artifacts (`scout-round*-status.env`,
  `scout-round*-manifest.json`, `scout-round*-manifest.json.raw`,
  `scout-archetype-yield.tsv`), dynamic-archetype files
  (`reviewer-dyn-*.md`, `dyn-*-prompt.md`), voter parse-retry first-pass sidecars
  (`*-vote-output-first-pass.txt`), and NS-retry specialist first-pass sidecars
  (`*-output-first-pass.txt`). Files under `dynamic-archetypes/`
  inside `--source-dir` are walked one level deep and flattened to the round
  root (no nested `dynamic-archetypes/` directory in committed output).
  Raw `*.events.jsonl` files remain excluded by design, including local Codex
  telemetry inputs such as `codex.events.jsonl`, `coder-codex.events.jsonl`, and
  `<output-base>.events.jsonl`; they may contain prompts, responses, repo
  snippets, and tool output. Downstream consumers should read the sanitized
  per-bucket telemetry rows in `larch-tokens-*.jsonl` instead.
- `append` atomically appends append-mode NDJSON batches.
- `exists` probes a batch path.
- `manifest` updates mutable manifest fields. Dotted keys `steps_ran.<step>` set per-step boolean flags under `.steps_ran` (shell step name after the dot; value must be `true` or `false`). Other keys use flat `field=value` syntax. Values that look like JSON-native scalars (`null`, `true`, `false`, integers) are passed via `--argjson` so they are stored with the correct JSON type; all other values are passed via `--arg` (stored as strings).
- `commit` stages and commits one run directory without pushing. It refuses
  with a stderr diagnostic when `$IMPLEMENT_TMPDIR/post-merge-sentinel` exists
  or when the current branch is `main`/the `origin/HEAD` default branch,
  preventing incidental post-merge log-only commits from prompt-side and
  refresh paths. This rejection is unconditional — no bypass env var is
  honored (see `skills/implement/SKILL.md` NEVER #19). During the commit copy
  it treats `breadcrumbs/` as a commit-only artifact class sourced from the
  session tmpdir, not from the batch table.

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
`redact-tmpdir-paths.sh` and `redact-secrets.sh`. `write-round` applies
sidecar-specific trimmers from `scripts/lib-redact.sh` before this shared
redaction pipeline. Batches that declare the
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

The `init`, `write`, `write-round`, `append`, `exists`, `manifest`, and `commit` verbs require
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
points at the canonical repo subtree), no copy is performed. Before copy or git
operations, `commit` refreshes `manifest.json` `updated_at` in the source tree so the
committed manifest timestamp reflects flush time. The `rel` pathspec passed
to all git operations is built explicitly as `larch-logs/<skill>/<run-id>` (not derived
by stripping the repo root prefix from `repo_path`) so the commit is always scoped to
exactly the current run's directory regardless of symlink resolution differences.

**Breadcrumb commit artifact**: `commit` treats `breadcrumbs/` as a commit-only
artifact class owned by the shared `larch_log_publish_breadcrumbs_shared` helper
in `scripts/lib-larch-log.sh`, not by the batch table. Runtime streams are
sourced from `LARCH_BREADCRUMB_SOURCE_DIR` when set, else from the log-root
parent's `breadcrumbs/`, and the helper stages only depth-1 regular `*.ndjson`
files through
`redact-tmpdir-paths.sh | redact-secrets.sh --streaming --state-file <tmp>`
before atomically publishing `larch-logs/<skill>/<run-id>/breadcrumbs/`.
A missing source directory or a source tree with zero accepted `*.ndjson`
entries is a successful no-op and leaves any previously committed
`breadcrumbs/` directory untouched.
Enforced triggers such as non-session-tmpdir paths, symlinks, hardlinks, invalid
accepted basenames, or redaction failures fail closed for the whole directory;
hidden entries, non-regular files, and non-`*.ndjson` regular files are silently
ignored. See [SECURITY.md § Breadcrumb stream redaction](../SECURITY.md#breadcrumb-stream-redaction)
for the security posture and [docs/run-logs.md § breadcrumbs/](../docs/run-logs.md#breadcrumbs)
for the operator-facing directory contract.

**Batch registry**: all slugs, extensions, modes, and sanitizer hooks live in
`scripts/larch-log-batches.sh`. See `scripts/larch-log-batches.md` for the full
list, including `session-transcript` (the redacted Claude Code session `.jsonl`
captured at Step 18 of `/implement` for post-hoc auditability).

## Push Ownership

`commit` never pushes. `/implement` log persistence is owned by
explicit lifecycle flush points: the external-implementer dispatcher flush,
the pre-bump direct `larch-log.sh commit`, and `scripts/refresh-run-logs.sh`
before lifecycle pushes. The surrounding lifecycle push carries those commits
to the remote. Dedicated larch-log-only pushes are intentionally avoided.

Related files: `scripts/lib-larch-log.sh`, `scripts/larch-log-batches.sh`, and
the `scripts/larch-log-flush.sh` helper plus `scripts/test-larch-log.sh`
harness.
