# launch-review.sh

selects the vendor path while preserving the former review-launcher contracts:
Codex and Cursor support generic prompts plus specialist `--agent-file` modes;

## Invariants

  is set in the environment (default off). No lifecycle sidecars are written
  on the disabled path.
- When `IMPLEMENT_TMPDIR` is set and `LARCH_RENDER_CACHE_DIR` is unset,
  the launcher exports `LARCH_RENDER_CACHE_DIR=$IMPLEMENT_TMPDIR/render-cache`
  so all `render-specialist-prompt.sh` subprocesses in the same Bash invocation
  share the session render cache.
- `--output` is validated through `scripts/lib-validate-meta-path.sh` before
  launcher side effects.
- Codex and Cursor append `OUTER_LAUNCHER=<repo>/scripts/launch-review.sh`
  metadata and store `${OUTPUT}.prompt` so `collect-agent-results.sh` can replay
  retries through the same launcher with `--tool <tool>`.
  prompt hardening, model resolution, and snapshot-guard logic.
- Timing rows default to `<tool>-review`; CLI `--timing-task-kind` values must
  be non-empty and non-flag-like.
- Token budget cap handling is shared across all three tool paths via
  `--token-budget-cap` or `LARCH_TOKEN_BUDGET_CAP_REVIEW`.
- Codex receives a compact read-only hardening preamble through
  per-invocation `CODEX_HOME/config.toml`; Cursor receives the same compact
  prohibition in the wrapped prompt plus a `--mode plan` enforcement note.
- Cursor auth setup runs the Darwin preflight, then best-effort pre-reads the
  `cursor-user` / `cursor-access-token` keychain service into `CURSOR_API_KEY`
  before composing argv. A successful pre-read becomes an explicit `--api-key`
  argument.
- Every external spawn site is wrapped by the shared helpers in
  `scripts/lib-external-launcher-common.sh`: Darwin-only per-tool startup locks
  CLI initialization, delayed release starts at process spawn, stale locks are
  recovered, and auth/startup failures are retried up to
  `LARCH_EXTERNAL_AUTH_RETRIES` attempts. Tunables:
  `LARCH_EXTERNAL_SERIAL_LOCK_DELAY`, `LARCH_EXTERNAL_SERIAL_LOCK_TTL`,
  `LARCH_EXTERNAL_SERIAL_LOCK_TRIES`, and
  `LARCH_EXTERNAL_SERIAL_LOCK_FORCE_UNAME`.
- When Codex or Cursor review launches finish their auth-retry loops with a
  non-zero exit and `IMPLEMENT_TMPDIR` is set, the launcher best-effort appends
  captured sidecar diagnostics to `$IMPLEMENT_TMPDIR/execution-issues.md`
  through `scripts/append-tool-failure.sh --redact` under
  `External Reviewer Issues`, including an auth verdict and the final auth-loop
  attempt count. Cursor verdicts inspect both `${OUTPUT}.sidecar` and
  `${OUTPUT}.diag` because stderr can land in either place.
- The Cursor path calls `cursor_launcher_setup_private_config_dir` (from
  `lib-cursor-launcher-common.sh`) immediately before the auth-retry loop to
  give each invocation a fresh private `CURSOR_CONFIG_DIR` directory (seeded
  from `~/.cursor/cli-config.json` when present). This eliminates the
  `cli-config.json` rename race that occurs when many `cursor agent` processes
  share the default `~/.cursor` config dir. Cleanup runs in the EXIT trap
  (`_publish_done_on_exit`) so leaked dirs are removed even on timeout or
  signal. Auth state (keychain entries `cursor-user` / `cursor-access-token`)
  lives in macOS Keychain, not in `cli-config.json`, so the private dir does
  not affect keychain-based auth; the existing `external_serial_lock_acquire`
  keychain-bootstrap lock is retained unchanged.
- Cursor JSON envelopes with an explicit empty `.result` are promoted to the
  literal `CURSOR_EMPTY_RESPONSE` in the reviewer output file after JSON
  post-processing. Missing `.result`, malformed JSON, or non-JSON prose keep the
  existing fallback behavior; only the explicit empty-result backend response
  gets the distinct marker.
- Codex sets `CODEX_SANDBOX_MODE=read-only` and emits a static
  `STATUS=clean MODE=baseline REASON=codex-sandbox-read-only` sidecar without
  running the scan — `--sandbox read-only` blocks writes at the syscall level,
  making the after-the-fact scan redundant. Cursor still runs the full scan.
- Codex captures both stdout AND stderr to `${OUTPUT}.sidecar` (`>>"$SIDECAR" 2>&1`)
  so that token-usage lines printed to either stream are available for the
  `token-ledger.sh record-vendor` scraper. Mirrors `launch-codex-implement.sh`.
- `--commit-count <n>` (optional): passed through to `render-specialist-prompt.sh`
  on `--agent-file` paths; when `1 ≤ n ≤ 5`, the rendered specialist prompt omits
  the `git log` instruction from its diff preamble. Stored in the specialist prompt
  sentinel (`${OUTPUT}.prompt`) so retry replay produces an identical prompt.
  Ignored on `--prompt` / `--prompt-file` paths.
- `--plan-file <path>` (optional): forwarded to `render-specialist-prompt.sh` on `--agent-file`
  diff-mode paths. Embeds the plan file's content inline in the prompt between `<implementation_plan>`
  tags so the reviewer can verify code against the plan. Stored in the Codex specialist prompt
  Ignored on `--prompt` / `--prompt-file` paths.
- `--feature-file <path>` (optional): forwarded to `render-specialist-prompt.sh` on `--agent-file`
  diff-mode paths. Embeds the feature description file's content inline between `<feature_description>`
  Ignored on `--prompt` / `--prompt-file` paths.

## Primary Callers

- `skills/implement/SKILL.md` quick review fan-out.
- `skills/design/SKILL.md` and design references for plan/sketch reviewers.
- `skills/review/SKILL.md` specialist and generic review fan-out.
- `scripts/collect-agent-results.sh` empty-output retry replay.

## Harness

Run `make test-launch-review`. The harness ports the previous Codex, Cursor,

## Edit In Sync

Update `scripts/test-launch-review.sh`, `scripts/collect-agent-results.sh`,
`scripts/test-collect-agent-retry.sh`, `docs/linting.md`, external-reviewer
docs, and the skill call sites whenever argv grammar, sidecar shape, retry
metadata, timing, budget-cap, or read-only hardening behavior changes.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.
