### FINDING_1: Duplicate get-issue-state test case labels
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Proposed missing-value regression cases reuse existing `(f)` and `(g)` harness labels, which already cover gh-failure and gh-success, so the new cases could overwrite, duplicate, or skip existing assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Append missing-value tests as (h) and (i) (or reletter downstream cases) and update the plan/testing section accordingly
  - From Cursor-Pragmatic: Add cases as (h) and (i) (or next free letters) and update the plan and get-issue-state.md harness section accordingly

### FINDING_2: Codex JSONL conversion drops final-message logs
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Edge, Cursor-Innovation, Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The wrapped Codex sites redirect stdout to JSONL event files and remove `--capture-stdout` without adding `--output-last-message`, leaving `codex.log`, `coder-codex.log`, copied `coder-output.log`, and `CODER_LOG_FILE` empty or missing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Mirror launch-codex-implement.sh:334-338: keep shell redirect to codex-events.jsonl and add --output-last-message "$run_dir/codex.log" (and -- before the prompt if needed)
  - From Cursor-Arch: Add --output-last-message "$round_dir/coder-codex.log" on the codex exec argv; keep cp/tool_log behavior or point tool_log at the last-message file explicitly
  - From Codex-Arch: Add --output-last-message "$run_dir/codex.log" and --output-last-message "$round_dir/coder-codex.log" to the respective codex exec argv, then assert the result log remains non-empty and contains FIXED/APPLIED/SKIPPED-style content while JSONL stays in the events file
  - From Codex-Edge: Add --output-last-message "$run_dir/codex.log" in lint-fix-loop.sh and --output-last-message "$round_dir/coder-codex.log" in review-and-fix.sh while keeping --json stdout redirected to the events file. Extend tests to assert the tool log still contains the expected final message/result line, not only that events are non-empty.
  - From Cursor-Innovation: Mirror launch-review: add --output-last-message "$round_dir/coder-codex.log" (and --json -- -- before the prompt); keep cp to coder-output.log; extend run-external-agent-stub to honor --output-last-message when --json is present
  - From Codex-Innovation: Add --output-last-message "$run_dir/codex.log" and "$round_dir/coder-codex.log" to the Codex argv, and assert those logs contain the final agent message
  - From Codex-Pragmatic: Add --output-last-message "$run_dir/codex.log" and --output-last-message "$round_dir/coder-codex.log" to the respective codex exec argv, and test that final APPLIED/SKIPPED text remains in the legacy log path
  - From Codex-Requirements: Add --output-last-message "$run_dir/codex.log" and --output-last-message "$round_dir/coder-codex.log" to those codex exec argv, keep stdout redirected to events, and test the primary/copied coder log still contains the final response

### FINDING_3: Token ledger raw labels use hyphens instead of underscores
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The plan passes hyphenated slugs to `record_usage_from_events`, while existing token ledger raw labels use underscores, fragmenting per-bucket attribution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Use underscore raw labels for record_usage_from_events (codex_lint_fix, codex_negotiation, codex_review_fix) while keeping hyphen entries only in TIMING_TASK_KINDS_ALLOWED for future timing-ledger --task-kind

### FINDING_4: Telemetry calls reference undefined PLUGIN_ROOT
- **Reviewer(s)**: Cursor-Arch, Cursor-dyn-lib-api-surface, Codex-Arch, Cursor-Edge, Codex-dyn-lib-api-surface
- **Severity**: important
- **Concern**: Planned telemetry calls in `lint-fix-loop.sh` and `run-negotiation-round.sh` use `$PLUGIN_ROOT`, but those scripts do not define it, so `set -u` paths can abort or resolve the parser path incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}" (same pattern as launch-codex-ci.sh:12) before sourcing lib-codex-launcher-common.sh
  - From Cursor-Arch: Define PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}" at top of script (negotiation already sources lib-external-launcher-common.sh)
  - From Codex-Arch: Define PLUGIN_ROOT in both scripts using the launcher pattern PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}" before the telemetry call, and add regression coverage with CLAUDE_PLUGIN_ROOT unset
  - From Cursor-Edge: Define PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}" (or source lib-codex-launcher-common.sh from a path derived from SCRIPT_DIR) before record_usage; mirror launch-codex-implement.sh
  - From Codex-dyn-lib-api-surface: Define PLUGIN_ROOT near SCRIPT_DIR, e.g. PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}", then source/call through that root
  - From Codex-dyn-lib-api-surface: Define PLUGIN_ROOT near SCRIPT_DIR, e.g. PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}", and keep sourcing lib-external-launcher-common.sh from SCRIPT_DIR

### FINDING_5: Negotiation sidecar path is unspecified
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The negotiation Codex branch mentions a sidecar stderr redirect without naming the concrete path, leaving implementations free to use a nonexistent, undocumented, or unallowlisted file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Name sidecar explicitly (e.g. "${OUTPUT_FILE%.txt}.sidecar" matching launch-codex-ci.sh:171), document in run-negotiation-round.md, and add allowlist coverage if write-round should publish it

### FINDING_6: lint-fix-loop test plan assumes nonexistent Codex stub
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The proposed `test-lint-fix-loop` coverage assumes a `STUB_BIN/codex` fixture, but the harness currently uses `RUN_EXTERNAL_AGENT` commit wrappers, so new JSONL assertions may not exercise `run_codex`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a dedicated wrapper/stub case that simulates run_codex (honors --json, writes synthetic JSONL to the stdout redirect target, preserves wrapper.log stderr shape); do not assume STUB_BIN/codex exists

### FINDING_7: review-and-fix stub does not emit JSONL after capture removal
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The `run-external-agent-stub` still writes APPLIED lines through `--output` capture semantics, so after dropping `--capture-stdout`, tests expecting non-empty `coder-codex-events.jsonl` may not exercise the new JSONL path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Teach run-external-agent-stub.sh to emit a minimal JSONL line on stdout when --json is present in forwarded argv (and keep writing --output last-message content for cp/tool_log)

### FINDING_8: Timing task kinds are added without timing ledger emissions
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Pragmatic
- **Severity**: latent
- **Concern**: The plan adds `codex-*` timing task kinds and docs but does not wire `timing-ledger.sh record-vendor-task` calls at the direct/non-launcher sites, leaving unused allowlist entries and misleading documentation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Either add timing-ledger record-vendor-task calls (with validated --timing-task-kind) in the same PR or document these kinds as token-ledger-only until wired
  - From Codex-Arch: Either add start/end capture plus timing-ledger.sh record-vendor-task calls for codex-lint-fix, codex-negotiation, and codex-review-fix, or remove the lib-timing-kinds changes and document these as token-ledger raw labels only
  - From Codex-Pragmatic: Choose one contract: either add timing rows with start/end/exit status for the three sites, or drop the lib-timing-kinds and timing docs changes and describe these as token-ledger raw labels only

### FINDING_9: Codex exec argv lacks prompt separator
- **Reviewer(s)**: Cursor-Arch
- **Severity**: nit
- **Concern**: Planned `codex exec` invocations add `--json` but omit the `--` separator before prompt bodies, allowing prompts starting with `-` to be parsed as flags.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Prompt bodies starting with - can be misparsed as flags Add -- before "$prompt_body" (and negotiation prompt via stdin is unaffected) matching launcher argv shape

### FINDING_10: Negotiation telemetry can overwrite Codex exit status
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The direct negotiation Codex branch adds telemetry after `codex exec` without preserving the Codex exit code, so a failed reviewer run can be reported as success if telemetry returns zero.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Capture codex_rc immediately after codex exec, run telemetry best-effort, then return or exit with codex_rc so the existing EXIT_CODE handling still sees the reviewer failure
  - From Codex-Innovation: Capture codex_rc immediately around codex exec, run telemetry best-effort, then make the branch return the original codex_rc; add a failing-codex regression
  - From Codex-Pragmatic: Capture codex_rc immediately after codex exec, run telemetry best-effort, then make the branch/case return the original codex_rc before existing EXIT_CODE handling
  - From Codex-Requirements: Capture codex rc before telemetry with codex_rc=0; codex ... || codex_rc=$?, run telemetry best-effort, then propagate codex_rc; add a failing-codex test that still writes events and asserts exit 2 plus RESPONSE_FILE

### FINDING_11: Negotiation reuses stale events and sidecar files
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Concern**: The plan introduces negotiation Codex events and sidecar files but only removes `OUTPUT_FILE` before rerun, so stale JSONL or stderr artifacts can be parsed or published when Codex exits before writing fresh output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: After deriving codex_events and the sidecar path, rm -f both before invoking codex. Capture the codex exit code, record usage from the freshly-created events file, then return the original success/failure behavior.

### FINDING_12: Failed Codex attempts are not recorded
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Concern**: Usage recording is specified only after successful Codex wrapper returns, so failed Codex attempts that spend tokens before fallback or dispatch can produce events but never write usage records.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Structure each Codex dispatch as rc=0; run wrapper || rc=$?; codex_launcher_record_usage_from_events ...; return "$rc". This preserves fallback behavior while recording usage for failed attempts that produced parseable events.

### FINDING_13: get-issue-state missing-value guard accepts flag-looking values
- **Reviewer(s)**: Codex-Edge
- **Severity**: nit
- **Concern**: A simple arity guard for `--issue` and `--repo` still allows the next flag token, such as `--repo`, to be consumed as a value, yielding an unknown-flag error instead of a requires-value error.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: For --issue and --repo, also reject a next token that starts with -- before assignment, or use a small value-required helper that checks both arity and flag-looking values for these numeric/repo options.

### FINDING_14: Raw Codex JSONL may be committed to larch-logs
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic, Cursor-dyn-glob-pattern-logic
- **Severity**: important
- **Concern**: The plan allowlists hyphen-named Codex JSONL event streams into committed run logs despite existing policy excluding raw `*.events.jsonl`; those streams can contain prompts, reviewer text, repo snippets, responses, or tool output beyond token counters.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Keep raw Codex events excluded; generate a usage-only sanitized artifact or token-record summary for committed logs, or add an events sanitizer that drops all non-usage payload before allowlisting
  - From Codex-Pragmatic: Add a staging sanitizer for these files that keeps only usage/token fields, or publish a minimized usage artifact instead of raw events, with tests proving prompt/body fields are stripped
  - From Cursor-dyn-glob-pattern-logic: Add a SECURITY.md subsection distinguishing excluded *.events.jsonl (dot, launcher-style) from allowlisted *-codex-events.jsonl (hyphen, redacted via stage_round_artifact), and note prompt/token leakage posture

### FINDING_15: Tests do not assert telemetry bucket records
- **Reviewer(s)**: Codex-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: Planned tests assert event artifacts exist but do not prove telemetry was parsed and recorded with the intended Codex bucket, so wrong labels, malformed events, or missing `record_usage_from_events` calls could pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Set an isolated LARCH_TOKEN_LEDGER in each harness and assert a vendor=codex row with nonzero input/cache_read/output/total and the expected raw bucket label
  - From Codex-Requirements: Extend each Item B harness to use an isolated token ledger or token-record path, emit a parse-codex-usage-compatible usage event, and assert the expected codex-review-fix, codex-lint-fix, and codex-negotiation vendor telemetry record
