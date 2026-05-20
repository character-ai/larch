# scout-dynamic-archetypes.sh Contract

`scripts/scout-dynamic-archetypes.sh` asks a Claude Sonnet subprocess to propose optional, ephemeral specialist reviewer archetypes for `/review`.

Primary caller: `skills/review/scripts/dispatch-panel.sh`. Other callers should treat it as an implementation detail of the review panel dispatcher.

Accepted flags: `--mode diff|description`, `--diff-file` for diff mode, `--scope-files` for description mode, and exactly one of `--description-text` or `--description-file` (file path is validated like other context inputs; prefer `--description-file` for large descriptions because Linux caps per-`argv` string length below the 256 KB scout limit), optional `--plan-file`, required `--max-archetypes 0..8`, required `--output`, optional `--session-env-path` (exported for nested timing/session consumers), and optional `--timeout` (default `180` seconds).

Invariants:

- Dynamic archetypes are opt-in and capped at 8.
- The scout is non-fatal. Claude failures, malformed JSON, timeout, and validation failures all write `{"archetypes":[]}` and emit a non-`ok` `SCOUT_STATUS`.
- The script invokes `scripts/launch-claude-subprocess.sh` by default, not raw `claude`, so subprocess path validation, read-only preamble, context hardening, timing-ledger integration, and dirty-tree sidecars stay centralized.
- `SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH` may override that launcher path for tests or controlled integrations. Treat the override target as trusted executable configuration: it can change the subprocess binary and the hardening path applied to scout prompts.
- Diff, scope-file, optional `--description-file`, and optional plan-file inputs are validated before prompt assembly with the same regular-file, non-symlink, allowed-root, and 256 KB-per-file constraints enforced by `launch-claude-subprocess.sh`. Allowed roots are the plugin root, the scout output directory, and when available the caller session directory (`dirname "$SESSION_ENV_PATH"`) or `IMPLEMENT_TMPDIR`. Inline `--description-text` is also capped at 256 KB before prompt assembly.
- The output JSON is validated before publication. Valid archetypes require a safe slug name, allowed focus area (`code-quality`, `risk-integration`, `correctness`, `architecture`, `security`), integer weight `1..8`, non-empty rationale, and non-empty prompt body.
- If the Claude subprocess wraps an otherwise valid JSON object in markdown code fences, the script strips the fenced wrapper before validation. Other malformed JSON remains a non-fatal `parse-failed` scout result.
- Prompt bodies containing a standalone `---` line, literal `</reviewer_` closing tags, or literal `</scout_notes>` wrapper terminators are rejected so synthesized agent frontmatter and untrusted wrapper tags cannot be corrupted. Rationale text is likewise rejected when it contains newlines, a standalone `---` line, or `</scout_notes>`.
- Duplicate names keep the first archetype and emit `WARN`; reserved static slugs are rejected.
- When validation yields more accepted archetypes than `--max-archetypes`, the script truncates to the cap and emits a `WARN`.
- Dynamic archetypes are ephemeral files under the review tmpdir and bypass the `agent-sync` CI job.
- When Claude is invoked (`--max-archetypes > 0`), the on-disk sidecar `${OUTPUT}.raw` preserves the subprocess output verbatim, even when fence-wrapped JSON is later parsed from a separate temp file. When `scripts/larch-log.sh write-round` commits that sidecar into round-N logs, it stages the copy through the normal redaction path (`stage_round_artifact` → `larch_log_redact_file`), so committed bytes may differ from the live tmpdir file. `--max-archetypes 0` skips the launch entirely and does not create `${OUTPUT}.raw`.

Stdout is `KEY=value`: `SCOUT_STATUS`, `SCOUT_OUTPUT`, `SCOUT_ARCHETYPE_COUNT`, `SCOUT_LATENCY_MS`, optional `SCOUT_FAIL_REASON` on `SCOUT_STATUS=parse-failed`, and optional `WARN`. Scout-local `SCOUT_FAIL_REASON` values are `json_parse`, `invalid_archetypes_shape`, `validation_jq_error`, and `fence_strip_io`. `dispatch-panel.sh` may also emit wrapper-level `SCOUT_FAIL_REASON` values such as `dispatch_manifest_validation`, `missing_status_sidecar`, and `unknown` when it validates cached scout artifacts or logs a parse-failure fallback. `dispatch-panel.sh` additionally emits `SCOUT_STATUS=validation-failed` when `scout-dynamic-archetypes.sh` exits non-zero before the manifest can be evaluated; the scout script itself does not emit this status. Scout stdout may emit `SCOUT_STATUS=ok`, `empty`, `parse-failed`, `claude-failed`, or `timeout`.

Harness: `scripts/test-scout-dynamic-archetypes.sh`.

Edit in sync: update this file, `scripts/test-scout-dynamic-archetypes.sh`, `skills/review/scripts/dispatch-panel.sh`, and `skills/review/scripts/dispatch-panel.md` when changing scout JSON schema, validation, scout statuses, dispatcher `validation-failed` handling, or invocation flags.
