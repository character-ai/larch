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
  Raw static specialist outputs are excluded for both Cursor and Codex,
  including their exact (`-output.txt`), phased (`-output-phase*.txt`),
  retry (`-output-retry.txt`), and sidecar (`.meta`, `.json`, `.cap-hit`)
  forms. NS-retry sidecar files (`*-ns-retry*.txt`) remain committed — the
  `ns-retry-sidecars` audit scan reads them as an anomaly signal.
  Dynamic Codex twins (`dyn-*-codex-output.txt` and
  `dyn-*-codex-output-phase*.txt`) and their unphased/phased `.meta`, `.json`,
  and `.cap-hit` sidecars follow the same retention path as dynamic Cursor
  outputs. `round_artifact_included()` mirrors this retention path with an
  explicit clause for the known dynamic Codex families
  (`dyn-*-codex-output.txt` and `dyn-*-codex-output-phase*.txt`) and their
  `.meta`, `.json`, and `.cap-hit` sidecars. Retry outputs
  (`dyn-*-codex-output-retry*`) are explicitly denied and are not covered by
  this clause; other or future output shapes may still fall through to the
  broad `*-output*` allow. Dynamic Codex `.prompt`, dynamic-shaped
  `*-vote-prompt.txt`, and unphased `.events.jsonl` sidecars remain excluded
  (phased Dynamic Codex does not produce `.events.jsonl` in real runs). The
  retained dynamic Codex families rely on the documented pattern-based redaction
  posture in [SECURITY.md](../SECURITY.md).
  Dynamic reviewer prompt files (`dyn-*-prompt.md`) are excluded — each
  re-embeds the full diff, plan, and feature description; only the archetype
  section differs and is captured by the archetype pool (see below).
  Raw scout manifests (`scout-round*-manifest.json.raw`) are excluded —
  byte-identical to the cooked `.json` in nearly all committed runs; the
  cooked `.json` is canonical. Cross-round identical `scout-round*-manifest.json`
  files are also skipped: round N's manifest is omitted when it is byte-identical
  to the same-named file in round N-1 (via `cmp -s`).
  Proposal-stage finding aggregates — `findings.md`, `accepted-findings.md`,
  `oos.md`, and `rejected-findings-full.md` — are explicitly denied.
  `review-findings-full.jsonl` is the canonical store; `scripts/render-findings-view.sh`
  reconstructs any dropped view on demand. `oos-accepted-review.md`,
  `rejected-findings.md`, `voting-tally.md`, and `findings-classification.tsv`
  are kept (audit scan inputs and the human round digest).
  Voter output files (`*-vote-output.txt`, `*-vote-output-*.txt`,
  `*-vote-output-first-pass.txt`) are capped at 2 KB by `stage_round_artifact`;
  files over that limit are truncated with a `[TRUNCATED: original N bytes]` marker.
  The `codex-impl-transcript` batch written via `larch-log.sh write` is capped at
  8 KB with the same marker.
  The allow-list includes scout artifacts (`scout-round*-status.env`,
  `scout-round*-manifest.json`, `scout-archetype-yield.tsv`),
  voter parse-retry first-pass sidecars (`*-vote-output-first-pass.txt`),
  and NS-retry specialist first-pass sidecars (`*-output-first-pass.txt`).
  Files under `dynamic-archetypes/` inside `--source-dir` are walked one
  level deep and flattened to the round root (no nested `dynamic-archetypes/`
  directory in committed output).
  `aggregator-output.txt` is skipped when byte-identical to `findings.md`
  in the same source directory (avoids committing a duplicate of the staged
  aggregate).

  **`round-meta.json` (Phase 3c)** — seven per-round sidecar files
  (`review-tally.env`, `collector-results.env`, `collect-agent-results.log`,
  `review-summary.json`, `coder.env`, `coder-codex.wrapper.log`,
  `coder-cursor.wrapper.log`) are consolidated into a single JSON object at
  `round-N/round-meta.json` rather than committed individually. The object has
  named sections: `tally` (KV from `review-tally.env`), `collector` (raw text),
  `collect_log` (raw text), `summary` (JSON passthrough of `review-summary.json`),
  `coder` (KV from `coder.env`), and `wrapper_logs.{cursor,codex}` (raw text).
  Sections absent from the source directory are omitted. The file is redacted
  through the same path as other round artifacts.

  **Archetype pool (Phase 3c)** — `reviewer-dyn-*.md` archetype definition
  files are not committed per-round. Instead each unique definition is written
  once to `larch-logs/shared/archetypes/<sha256-12>.md` (content-addressed,
  idempotent: existing hash → no write). The corresponding `panel-manifest.ndjson`
  entries for `dyn-*` slots receive a new `archetype_ref` field containing the
  SHA256-12 identifier. The pool directory is inside the log root and is copied
  to `larch-logs/shared/` by `commit`.

  **Retroactive sweep** — `scripts/consolidate-round-sidecars.sh` migrates
  existing committed round directories to the new layout (see that script for
  usage; invoke once from a dedicated log-only PR).
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
  session tmpdir, not from the batch table. It also copies the shared archetype
  pool from `<LARCH_LOG_ROOT>/shared/` to `larch-logs/shared/` in the repo when
  that directory is present, and includes `larch-logs/shared` in the git
  `add`/`status`/`diff`/`commit` pathspecs so new pool entries ride the same
  flush commit as the per-run data.

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
`python/cli.py mermaid sanitize --from-md` and fail closed on rejection; no
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
in `scripts/lib-larch-log.sh`, not by the batch table. The helper redacts each
session-root `larch-quiet-<script>-<pid>.log` file (derived via `dirname` of
the breadcrumbs source path from `LARCH_BREADCRUMB_SOURCE_DIR` or the log-root
parent's `breadcrumbs/`) through
`redact-tmpdir-paths.sh | redact-secrets.sh --streaming --state-file <tmp>`,
then **concatenates** all redacted content into a single
`larch-logs/<skill>/<run-id>/breadcrumbs/quiet.log` file (with per-source-file
header lines `=== <basename> ===`) instead of publishing individual files.
This reduces file count significantly for sessions with many scripts.
Legacy `*.ndjson` stream files are not published.

A session root with zero accepted quiet logs is a successful no-op when nothing
is staged; it leaves any previously committed `breadcrumbs/` directory untouched.
Enforced triggers such as non-session-tmpdir paths, symlinks, hardlinks, invalid
accepted basenames, or redaction failures fail closed for the whole directory;
legacy ndjson files and non-matching basenames are silently ignored. See
[SECURITY.md § Breadcrumb stream redaction](../SECURITY.md#breadcrumb-stream-redaction)
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

## Vendor failure-diagnostics carrier (#3713)

`round_artifact_included` denies `*.failure-diag`, `*.sidecar.history`, and
`*.events.history` so the per-output failure carrier is never committed by the
per-output write-round path (F14). The durable implement path for vendor-agent
failures is the `vendor-failure-diagnostics` batch, staged by
`scripts/flush-vendor-failure-diagnostics.sh`. See
`docs/vendor-agent-diagnostics-audit.md`.
## Concise prune/log audit update

Implement `write-round` default logs are concise by construction: raw reviewer output, vote-output prose, NS-retry transcripts, and pre-prune manifests are debug-gated, while `prune-decision.env` and `prune-nit.env` are included. `round-meta.json` carries `reviewer_signals[]` with `output_basename`, `slot_label`, `result_kind`, `ns_retry_reason`, and `first_pass_trailing_content`, produced from source-dir reviewer outputs (including `dynamic-archetypes/`) before default transcript exclusion. `ns_retry_reason` is restricted to the allowed token vocabulary (`NO_ISSUES_FOUND_TOO_THIN`, `OUTPUT_EMPTY`, `JSON_PARSE_FAIL`, `UNKNOWN`); composition failures fail the flush rather than silently omitting signals. Audit scans treat `reviewer_signals[]` as the primary carrier; `result:"skip"` in migrated scans means the concise carrier is missing, not a clean run.
