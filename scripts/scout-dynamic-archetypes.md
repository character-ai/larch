# scout-dynamic-archetypes.sh Contract

`scripts/scout-dynamic-archetypes.sh` asks a Claude Sonnet subprocess to propose optional, ephemeral specialist reviewer archetypes for `/review`.

Primary caller: `skills/review/scripts/dispatch-panel.sh`. Other callers should treat it as an implementation detail of the review panel dispatcher.

Accepted flags: `--mode diff|description`, `--diff-file` for diff mode, `--scope-files` and `--description-text` for description mode, optional `--plan-file`, required `--max-archetypes 0..4`, required `--output`, optional `--session-env-path`, and optional `--timeout` (default `180` seconds).

Invariants:

- Dynamic archetypes are opt-in and capped at 4.
- The scout is non-fatal. Claude failures, malformed JSON, timeout, and validation failures all write `{"archetypes":[]}` and emit a non-`ok` `SCOUT_STATUS`.
- The script invokes `scripts/launch-claude-subprocess.sh`, not raw `claude`, so subprocess path validation, read-only preamble, context hardening, timing-ledger integration, and dirty-tree sidecars stay centralized.
- The output JSON is validated before publication. Valid archetypes require a safe slug name, allowed focus area (`code-quality`, `risk-integration`, `correctness`, `architecture`, `security`), integer weight `1..8`, non-empty rationale, and non-empty prompt body.
- Prompt bodies containing a standalone `---` line or literal `</reviewer_` closing tags are rejected so synthesized agent frontmatter and untrusted wrapper tags cannot be corrupted.
- Duplicate names keep the first archetype and emit `WARN`; reserved static slugs are rejected.
- Dynamic archetypes are ephemeral files under the review tmpdir and bypass the `agent-sync` CI job.

Stdout is `KEY=value`: `SCOUT_STATUS`, `SCOUT_OUTPUT`, `SCOUT_ARCHETYPE_COUNT`, `SCOUT_LATENCY_MS`, and optional `WARN`.

Harness: `scripts/test-scout-dynamic-archetypes.sh`.

Edit in sync: update this file, `scripts/test-scout-dynamic-archetypes.sh`, `skills/review/scripts/dispatch-panel.sh`, and `skills/review/scripts/dispatch-panel.md` when changing scout JSON schema, validation, statuses, or invocation flags.
