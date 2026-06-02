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
- Optional `--stderr-sink PATH` is accepted on both Codex and Cursor lanes,
  validated with the same `[A-Za-z0-9._/-]` allowlist as `--output`, threaded
  to inner `run-external-agent.sh` invocations, and recorded in the outer
  `.meta` as `STDERR_SINK=` when non-empty (for collector retry round-trip).
- Optional `--risk high|low` is captured and forwarded as `OUTER_LAUNCHER_RISK`
  in the outer `.meta` so `collect-agent-results.sh` replays empty-output
  retries with the caller's risk-gated effort setting.
- Codex and Cursor append `OUTER_LAUNCHER=<repo>/scripts/launch-review.sh`
  metadata and store `${OUTPUT}.prompt` so `collect-agent-results.sh` can replay
  retries through the same launcher with `--tool <tool>`.
- Shared launcher wiring covers prompt hardening, model resolution, and snapshot-guard logic.
- Timing rows default to `<tool>-review`; CLI `--timing-task-kind` values must
  be non-empty and non-flag-like.
- Token budget cap handling is shared across all three tool paths via
  `--token-budget-cap` or `LARCH_TOKEN_BUDGET_CAP_REVIEW`.
- When `IMPLEMENT_TMPDIR/session-id` is absent, the launcher exports
  `LARCH_TOKEN_SESSION_ID` from `$DESIGN_TMPDIR/session-id` when that file
  exists (standalone `/design` parity across Codex and Cursor branches).
- Codex receives a compact read-only hardening preamble through
  per-invocation `CODEX_HOME/config.toml`; Cursor receives the same compact
  prohibition in the wrapped prompt plus a `--mode ask` enforcement note.
- Optional `--codex-add-dir DIR` narrows Codex `codex exec --add-dir` to a
  directory under the session root that owns `--output` (scout passes staged-context only).
  Rejects symlinks, control characters, `..`, and paths outside the session root.
- Cursor auth setup runs the Darwin preflight, then best-effort pre-reads the
  `cursor-user` / `cursor-access-token` keychain service into `CURSOR_API_KEY`,
  then normalizes/exports `CURSOR_API_KEY` via `cursor_auth_export_env`. Auth is
  delivered to the Cursor child via that environment variable (issue #3375) —
  **no** `--api-key` argv element, so the key never reaches argv, `.meta`
  `CMD_JSON`, or `ps`.
- Every external spawn site is wrapped by the shared helpers in
  `scripts/lib-external-launcher-common.sh`: Darwin-only per-tool startup locks
  CLI initialization, delayed release starts at process spawn, stale locks are
  recovered, and auth/startup failures are retried up to
  `LARCH_EXTERNAL_AUTH_RETRIES` attempts. Tunables:
  `LARCH_EXTERNAL_SERIAL_LOCK_DELAY`, `LARCH_EXTERNAL_SERIAL_LOCK_TTL`,
  `LARCH_EXTERNAL_SERIAL_LOCK_TRIES`, and
  `LARCH_EXTERNAL_SERIAL_LOCK_FORCE_UNAME`.
- When Codex or Cursor review launches finish their auth-retry loops with a
  non-zero exit, the launcher best-effort appends captured sidecar diagnostics
  to an `execution-issues.md` through `scripts/append-tool-failure.sh --redact`
  under `External Reviewer Issues`, including a failure verdict and the final
  auth-loop attempt count. The log path resolves to
  `$IMPLEMENT_TMPDIR/execution-issues.md` when `IMPLEMENT_TMPDIR` is set, else
  `$DESIGN_TMPDIR/execution-issues.md` so `/design` voter failures are recorded
  rather than silently dropped (#3378). The verdict is computed by
  `external_failure_verdict`: `auth-retries-exhausted`, `quota`
  (usage-limit/quota, distinct from auth), `non-auth`, or `unclassified`.
  Cursor verdicts inspect both `${OUTPUT}.sidecar` and `${OUTPUT}.diag` because
  stderr can land in either place.
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
- Cursor runs `cursor agent -p --trust --mode ask --output-format json`; `ask`
  and `plan` are both read-only Cursor modes, and the dirty-tree sidecar remains
  the post-run mutation detector.
- Cursor JSON envelopes with an explicit empty `.result` are promoted to the
  literal `CURSOR_EMPTY_RESPONSE` in the reviewer output file after JSON
  post-processing. Missing `.result`, malformed JSON, or non-JSON prose keep the
  existing fallback behavior; only the explicit empty-result backend response
  gets the distinct marker. When the terminal state is still empty after the
  auth/transient loop, the launcher also writes `${OUTPUT}.diag` in the
  established `TOOL=cursor` / `FAILURE_REASON=…` KV grammar (envelope `type`,
  `subtype`, `is_error`, `error`, `usage`, optional `duration` / request-id
  fields, empty-result retry count). All extracted fields are sanitized
  (newlines/pipes stripped, length capped) before interpolation. The full
  envelope is always copied to `${OUTPUT}.json` before `.result` extraction.
- **Exit-0 empty `.result` transient retry (cursor-only).** Inside the cursor
  auth loop, after the exit-code transient branch and before auth retry: when
  `EXIT_CODE==0`, `jq` is available, `$OUTPUT` is non-empty JSON,
  `(.result // "") == ""`, and no quota/auth signal is detected in `$SIDECAR`,
  `${OUTPUT}.diag`, or the raw `$OUTPUT` envelope, the launcher treats the
  response as transient and re-runs the same `cursor agent` invocation after
  backoff. Empty-result retries share the same `TRANSIENT_ATTEMPT` counter as
  exit-code transients (bounded by `MAX_TRANSIENT_RETRIES=2`, so at most three
  total `cursor agent` backend calls per auth pass across both failure modes).
  This does **not** apply when `.result` is the legitimate no-findings
  sentinel `{"no_issues_found": true}` (non-empty string) or any other
  non-empty `.result`. Malformed/non-JSON `$OUTPUT` skips this branch (`jq`
  probe false). `LARCH_CURSOR_RETRY_EMPTY_RESULT` defaults on; set to `0` to
  disable retry only (diagnostics still written). Codex has no `.result`
  envelope — do not mirror this branch into the codex launcher.
- **Per-process launch jitter (cursor-only).** Before the cursor auth loop, a
  one-time random sleep in `0..LARCH_CURSOR_LAUNCH_JITTER_MS` (default `250`,
  non-numeric → default, `0` disables) de-synchronizes parallel slot launches.
  See `docs/configuration-and-permissions.md`.
- Cursor JSON envelopes with high `usage.outputTokens` but a very short
  extracted `.result` are promoted to `CURSOR_DEGRADED_RESPONSE` before the
  result is installed. The heuristic is skipped for legitimate terse sentinels
  and structures validated by `scripts/validate-research-output.sh --validation-mode`:
  `NO_ISSUES_FOUND`, JSON containing `"no_issues_found": true` (on the first
  or last non-empty line when the last differs from the first — covers
  Cursor's narration-then-sentinel shape, #3283), inline TSV records,
  and voter ballot grammar with at least one `FINDING_N: YES|NO|EXONERATE`
  line (#3283). Current thresholds are `outputTokens > 1000` and extracted
  result bytes `< 500`.
- Codex sets `CODEX_SANDBOX_MODE=read-only` and emits a static
  `STATUS=clean MODE=baseline REASON=codex-sandbox-read-only` sidecar without
  running the scan — `--sandbox read-only` blocks writes at the syscall level,
  making the after-the-fact scan redundant. Cursor still runs the full scan.
- Codex runs with `--json`: stdout JSONL events land in `${OUTPUT}.events.jsonl`,
  while stderr remains in `${OUTPUT}.sidecar`. Auth and transient-infra
  classification inspect stderr only, but usage-limit/quota classification also
  consults the events stream: because `codex exec --json` reports a usage limit
  as a `{"type":"error",…}` / `turn.failed` event on stdout (with an empty stderr
  sidecar and `--output-last-message` file), the launcher mirrors that signal
  into the sidecar via `external_launcher_mirror_quota_from_events` before
  classifying, so the sidecar-based quota guard short-circuits the `{5,7}`
  transient-retry loop instead of re-hitting the limit and reports a `quota`
  verdict rather than a generic non-auth exit 7 (#3390). Token capture is
  fail-closed through `scripts/parse-codex-usage.sh`: exit 0 records
  per-bucket `token-ledger.sh record-vendor codex` fields; non-zero appends
  the parser diagnostic to `${OUTPUT}.sidecar` and writes no Codex token row.
  See [scripts/parse-codex-usage.md](parse-codex-usage.md) for the KV
  contract and fail-closed validation semantics.
- On successful Codex or Cursor review launches, an empty `${OUTPUT}.sidecar`
  is populated with an informational status marker
  (`codex-status: ok...` or `cursor-status: ok...`). This distinguishes "no
  stderr emitted during a successful run" from "sidecar was never populated";
  no production consumer parses the marker, and vote tallying reads only the
  main `.txt` output.
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
