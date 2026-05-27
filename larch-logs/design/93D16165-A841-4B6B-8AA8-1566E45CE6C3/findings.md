### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-get-issue-state.sh:117-129
- **Concern**: Proposed new cases reuse labels (f) and (g) but harness already defines (f) gh-failure and (g) gh-success. Scenario: New regression cases would overwrite or duplicate existing assertions; CI would not test missing-value guards
- **Proposed resolution**: Append missing-value tests as (h) and (i) (or reletter downstream cases) and update the plan/testing section accordingly

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-fix-loop.sh:222-224
- **Concern**: Plan drops --capture-stdout and redirects stdout to codex-events.jsonl but never adds --output-last-message to codex exec. Scenario: --output codex.log stays empty; CODER_LOG_FILE still points at codex.log (lines 344, 409, 435) with no transcript
- **Proposed resolution**: Mirror launch-codex-implement.sh:334-338: keep shell redirect to codex-events.jsonl and add --output-last-message "$run_dir/codex.log" (and -- before the prompt if needed)

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:256-258
- **Concern**: Same capture removal without --output-last-message. Scenario: coder-codex.log empty; cp to coder-output.log (line 258) and CODER_LOG_FILE consumers get an empty log
- **Proposed resolution**: Add --output-last-message "$round_dir/coder-codex.log" on the codex exec argv; keep cp/tool_log behavior or point tool_log at the last-message file explicitly

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:17-20
- **Concern**: Plan passes hyphen slugs (codex-lint-fix, etc.) to codex_launcher_record_usage_from_events raw=. Scenario: Token ledger raw= uses underscores elsewhere (codex_ci_fix, codex_implement, codex_review); hyphen labels fragment per-bucket attribution in token-ledger.sh/timing-report consumers
- **Proposed resolution**: Use underscore raw labels for record_usage_from_events (codex_lint_fix, codex_negotiation, codex_review_fix) while keeping hyphen entries only in TIMING_TASK_KINDS_ALLOWED for future timing-ledger --task-kind

### FINDING_5:
- **Reviewer(s)**: Cursor-Arch, Cursor-dyn-lib-api-surface
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/lint-fix-loop.sh:217-224
- **Concern**: Plan calls codex_launcher_record_usage_from_events "$PLUGIN_ROOT" but script defines no PLUGIN_ROOT. Scenario: Runtime empty/wrong plugin root breaks parse-codex-usage.sh path; telemetry silently no-ops
- **Proposed resolution**: Add PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}" (same pattern as launch-codex-ci.sh:12) before sourcing lib-codex-launcher-common.sh

### FINDING_6:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/run-negotiation-round.sh:84-86
- **Concern**: Negotiation telemetry step uses PLUGIN_ROOT placeholder with no definition in script. Scenario: external_launcher_record_usage_from_events cannot resolve scripts/parse-codex-usage.sh
- **Proposed resolution**: Define PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}" at top of script (negotiation already sources lib-external-launcher-common.sh)

### FINDING_7:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:60-61
- **Concern**: Negotiation codex branch specifies 2>"<sidecar-log>" but no concrete sidecar path. Scenario: Split-stream refactor may write stderr to a nonexistent path, leave 2>&1 behavior, or pick an ad hoc name that is not allowlisted/documented
- **Proposed resolution**: Name sidecar explicitly (e.g. "${OUTPUT_FILE%.txt}.sidecar" matching launch-codex-ci.sh:171), document in run-negotiation-round.md, and add allowlist coverage if write-round should publish it

### FINDING_8:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:111-117
- **Concern**: Plan says test-lint-fix-loop uses STUB_BIN/codex; harness only uses RUN_EXTERNAL_AGENT commit wrappers. Scenario: test-lint-fix-loop.sh has no codex stub; new codex-events.jsonl assertions will not exercise run_codex without new fixture work
- **Proposed resolution**: Add a dedicated wrapper/stub case that simulates run_codex (honors --json, writes synthetic JSONL to the stdout redirect target, preserves wrapper.log stderr shape); do not assume STUB_BIN/codex exists

### FINDING_9:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:55-86
- **Concern**: run-external-agent-stub writes APPLIED lines to --output via capture-stdout semantics; plan only extends stub for --json. Scenario: After dropping --capture-stdout, events file may stay empty while tests assert non-empty coder-codex-events.jsonl
- **Proposed resolution**: Teach run-external-agent-stub.sh to emit a minimal JSONL line on stdout when --json is present in forwarded argv (and keep writing --output last-message content for cp/tool_log)

### FINDING_10:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:94-99
- **Concern**: New codex-* timing kinds added to lib-timing-kinds.sh but no timing-ledger.sh record-vendor-task at the three sites. Scenario: Allow-list entries never emitted; timing-report.sh stays blind to these buckets until a follow-up wires --timing-task-kind
- **Proposed resolution**: Either add timing-ledger record-vendor-task calls (with validated --timing-task-kind) in the same PR or document these kinds as token-ledger-only until wired

### FINDING_11:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: nit
- **Focus area**: correctness
- **Location**: scripts/lint-fix-loop.sh:223
- **Concern**: skills/review-and-fix/scripts/review-and-fix.sh:257. Scenario: Plan adds --json without the codex exec -- separator used in launch-codex-implement.sh:335-337
- **Proposed resolution**: Prompt bodies starting with - can be misparsed as flags Add -- before "$prompt_body" (and negotiation prompt via stdin is unaffected) matching launcher argv shape

### FINDING_12:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-fix-loop.sh:6-15, scripts/run-negotiation-round.sh:29-34
- **Concern**: Proposed telemetry calls use PLUGIN_ROOT in scripts that do not define it. Scenario: Both scripts run under set -u; after a successful Codex run the new record_usage_from_events call would expand an unbound PLUGIN_ROOT and abort instead of completing the workflow
- **Proposed resolution**: Define PLUGIN_ROOT in both scripts using the launcher pattern PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}" before the telemetry call, and add regression coverage with CLAUDE_PLUGIN_ROOT unset

### FINDING_13:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-fix-loop.sh:222-224, skills/review-and-fix/scripts/review-and-fix.sh:256-258
- **Concern**: The wrapped Codex JSONL conversion omits --output-last-message for the human result log. Scenario: After dropping --capture-stdout, Codex stdout becomes JSONL and run-external-agent no longer writes codex.log or coder-codex.log; review-and-fix then copies an empty coder-output.log, so SKIPPED finding extraction and operator diagnostics silently disappear
- **Proposed resolution**: Add --output-last-message "$run_dir/codex.log" and --output-last-message "$round_dir/coder-codex.log" to the respective codex exec argv, then assert the result log remains non-empty and contains FIXED/APPLIED/SKIPPED-style content while JSONL stays in the events file

### FINDING_14:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/run-negotiation-round.sh:84-132
- **Concern**: The direct Codex branch plan adds a post-run telemetry command without preserving the Codex exit status. Scenario: The script currently captures EXIT_CODE from the case branch status; if external_launcher_record_usage_from_events runs after codex exec and returns 0, a failed Codex negotiation is reported as success with RESPONSE_FILE even when codex exited non-zero
- **Proposed resolution**: Capture codex_rc immediately after codex exec, run telemetry best-effort, then return or exit with codex_rc so the existing EXIT_CODE handling still sees the reviewer failure

### FINDING_15:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/lib-timing-kinds.sh:5-67, scripts/timing-ledger.md:33-35
- **Concern**: The plan adds timing task kinds but does not add any timing-ledger emissions for the three sites. Scenario: These direct/non-launcher sites would only write token-ledger usage records; lib-timing-kinds.md would claim scripts emit timing task kinds that are never passed to timing-ledger.sh, leaving dead allowlist entries and misleading docs
- **Proposed resolution**: Either add start/end capture plus timing-ledger.sh record-vendor-task calls for codex-lint-fix, codex-negotiation, and codex-review-fix, or remove the lib-timing-kinds changes and document these as token-ledger raw labels only

### FINDING_16:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-fix-loop.sh:217-225
- **Concern**: Plan calls codex_launcher_record_usage_from_events with $PLUGIN_ROOT but the script never defines PLUGIN_ROOT or CLAUDE_PLUGIN_ROOT. Scenario: Under set -euo pipefail the telemetry call resolves plugin_root to empty and invokes /scripts/parse-codex-usage.sh (or fails), so codex-lint-fix vendor rows are silently dropped while the run otherwise succeeds
- **Proposed resolution**: Define PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}" (or source lib-codex-launcher-common.sh from a path derived from SCRIPT_DIR) before record_usage; mirror launch-codex-implement.sh

### FINDING_17:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-fix-loop.sh:222-224; skills/review-and-fix/scripts/review-and-fix.sh:256-258
- **Concern**: Missing replacement for captured Codex final output when --capture-stdout is removed. Scenario: The plan redirects Codex stdout to *-codex-events.jsonl but does not add --output-last-message for the two wrapper sites that currently rely on --capture-stdout to populate codex.log or coder-codex.log. Successful runs will leave the advertised CODER_LOG_FILE empty or absent, losing the required final-line/result transcript and making later diagnostics misleading.
- **Proposed resolution**: Add --output-last-message "$run_dir/codex.log" in lint-fix-loop.sh and --output-last-message "$round_dir/coder-codex.log" in review-and-fix.sh while keeping --json stdout redirected to the events file. Extend tests to assert the tool log still contains the expected final message/result line, not only that events are non-empty.

### FINDING_18:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/run-negotiation-round.sh:63-85
- **Concern**: Stale Codex events and sidecar files are not cleared before reuse. Scenario: The script currently removes only OUTPUT_FILE before a negotiation round. The plan introduces sibling codex_events and a sidecar log but does not require removing them before launch, so rerunning with the same --output can parse and ledger stale token usage if Codex exits before writing fresh JSONL or stderr.
- **Proposed resolution**: After deriving codex_events and the sidecar path, rm -f both before invoking codex. Capture the codex exit code, record usage from the freshly-created events file, then return the original success/failure behavior.

### FINDING_19:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/lint-fix-loop.sh:217-225; skills/review-and-fix/scripts/review-and-fix.sh:249-261
- **Concern**: Usage recording is specified only after successful Codex wrapper returns. Scenario: Codex can spend tokens and then fail, after which lint-fix-loop may fall back to Cursor or review-and-fix may dispatch Cursor. With the planned structure, those failed Codex attempts write events but never call codex_launcher_record_usage_from_events, silently undercounting vendor usage.
- **Proposed resolution**: Structure each Codex dispatch as rc=0; run wrapper || rc=$?; codex_launcher_record_usage_from_events ...; return "$rc". This preserves fallback behavior while recording usage for failed attempts that produced parseable events.

### FINDING_20:
- **Reviewer(s)**: Codex-Edge
- **Severity**: nit
- **Focus area**: correctness
- **Location**: scripts/get-issue-state.sh:35-44
- **Concern**: Missing-value guard does not catch another flag used as the value. Scenario: The proposed [ $# -lt 2 ] guard fixes final-argv cases, but get-issue-state.sh --issue --repo owner/repo still consumes --repo as the issue value and then errors on owner/repo as an unknown flag instead of reporting --issue requires a value.
- **Proposed resolution**: For --issue and --repo, also reject a next token that starts with -- before assignment, or use a small value-required helper that checks both arity and flag-looking values for these numeric/repo options.

### FINDING_21:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:256-258
- **Concern**: Item B adds --json and redirects stdout to coder-codex-events.jsonl but keeps copying coder-codex.log into coder-output.log without --output-last-message. Scenario: Prior art (launch-review.sh:506-510) splits JSONL (stdout) from final prose via --output-last-message; with --json only, APPLIED:/SKIPPED: lines never reach coder-output.log and grep at review-and-fix.sh:1169 silently misses skips
- **Proposed resolution**: Mirror launch-review: add --output-last-message "$round_dir/coder-codex.log" (and --json -- -- before the prompt); keep cp to coder-output.log; extend run-external-agent-stub to honor --output-last-message when --json is present

### FINDING_22:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/larch-log.sh:67-90
- **Concern**: Plan bypasses the existing *.events.jsonl deny rule and commits raw Codex JSONL streams. Scenario: `write-round` only strips meta CMD_JSON and top-level result JSON, so hyphen-named Codex event streams can publish prompts, reviewer text, repo snippets, and other session data to larch-logs after only generic secret redaction
- **Proposed resolution**: Keep raw Codex events excluded; generate a usage-only sanitized artifact or token-record summary for committed logs, or add an events sanitizer that drops all non-usage payload before allowlisting

### FINDING_23:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/run-negotiation-round.sh:66-132
- **Concern**: Telemetry call after codex exec can overwrite the reviewer exit status. Scenario: The script currently reads `$?` after the case; if external_launcher_record_usage_from_events runs after a failing codex command it returns 0 and the script emits RESPONSE_FILE as success
- **Proposed resolution**: Capture codex_rc immediately around codex exec, run telemetry best-effort, then make the branch return the original codex_rc; add a failing-codex regression

### FINDING_24:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-fix-loop.sh:222-224; skills/review-and-fix/scripts/review-and-fix.sh:256-258
- **Concern**: Non-launcher Codex conversions omit --output-last-message for the primary transcript. Scenario: After --json stdout is redirected to events and --capture-stdout is removed, codex.log and coder-codex.log stay empty even though callers expose them as CODER_LOG_FILE or copy them to coder-output.log
- **Proposed resolution**: Add --output-last-message "$run_dir/codex.log" and "$round_dir/coder-codex.log" to the Codex argv, and assert those logs contain the final agent message

### FINDING_25:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/test-lint-fix-loop.sh:280-286; scripts/test-run-negotiation-round.sh:96-104; skills/review-and-fix/scripts/test-review-and-fix.sh:55-86
- **Concern**: Planned tests prove event files exist but not that telemetry is recorded with the intended bucket. Scenario: A change that adds --json and creates non-empty events but omits record_usage_from_events or uses the wrong raw label would pass the proposed artifact-only assertions
- **Proposed resolution**: Set an isolated LARCH_TOKEN_LEDGER in each harness and assert a vendor=codex row with nonzero input/cache_read/output/total and the expected raw bucket label

### FINDING_26:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-get-issue-state.sh:117-129
- **Concern**: Plan assigns new cases (f)/(g) for missing --issue/--repo values but those labels already cover gh-failure and gh-success tests. Scenario: Renumbering would break existing harness labels or duplicate case ids; new regressions may be added under wrong ids or skipped
- **Proposed resolution**: Add cases as (h) and (i) (or next free letters) and update the plan and get-issue-state.md harness section accordingly

### FINDING_27:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-fix-loop.sh:222-224; skills/review-and-fix/scripts/review-and-fix.sh:256-258,1169
- **Concern**: The plan redirects Codex JSONL stdout away from the existing output files but does not add --output-last-message for the two wrapper-based coder sites. Scenario: The Codex final response no longer lands in codex.log or coder-codex.log; review-and-fix can miss SKIPPED lines and CODER_LOG_FILE points at an empty or missing response
- **Proposed resolution**: Add --output-last-message "$run_dir/codex.log" and --output-last-message "$round_dir/coder-codex.log" to the respective codex exec argv, and test that final APPLIED/SKIPPED text remains in the legacy log path

### FINDING_28:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/run-negotiation-round.sh:84-132
- **Concern**: The plan adds a telemetry call after direct codex exec without preserving the codex exit status first. Scenario: In the current script EXIT_CODE is read after the case; if telemetry is the last command in the codex branch, a failed codex run can be reported as success
- **Proposed resolution**: Capture codex_rc immediately after codex exec, run telemetry best-effort, then make the branch/case return the original codex_rc before existing EXIT_CODE handling

### FINDING_29:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/larch-log.sh:67-89,112-123; scripts/lib-larch-log.sh:88-95
- **Concern**: The plan allowlists raw hyphen-named Codex events into committed larch-logs while only applying generic token/path redaction. Scenario: Codex --json events can carry prompt, response, and tool-output content beyond token counters; bypassing the existing *.events.jsonl exclusion may commit sensitive session material
- **Proposed resolution**: Add a staging sanitizer for these files that keeps only usage/token fields, or publish a minimized usage artifact instead of raw events, with tests proving prompt/body fields are stripped

### FINDING_30:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: nit
- **Focus area**: architecture
- **Location**: scripts/lib-timing-kinds.sh:5-67; scripts/timing-ledger.md:33-35
- **Concern**: The plan adds timing task-kind allowlist entries and docs but does not add timing-ledger record-vendor-task calls for these direct/non-launcher sites. Scenario: The new lib-timing-kinds entries are unused and docs saying the scripts emit them would be misleading
- **Proposed resolution**: Choose one contract: either add timing rows with start/end/exit status for the three sites, or drop the lib-timing-kinds and timing docs changes and describe these as token-ledger raw labels only

### FINDING_31:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/run-negotiation-round.sh:84-132
- **Concern**: Plan calls external_launcher_record_usage_from_events after direct codex exec without preserving the codex exit status. Scenario: In this script EXIT_CODE is taken from the last command in the codex branch; a failed codex exec followed by a successful telemetry call can make EXIT_CODE=0, emit success, and skip the reviewer-command failure path
- **Proposed resolution**: Capture codex rc before telemetry with codex_rc=0; codex ... || codex_rc=$?, run telemetry best-effort, then propagate codex_rc; add a failing-codex test that still writes events and asserts exit 2 plus RESPONSE_FILE

### FINDING_32:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/lint-fix-loop.sh:222-224; skills/review-and-fix/scripts/review-and-fix.sh:256-258; scripts/run-external-agent.sh:206-212
- **Concern**: Plan drops --capture-stdout for wrapped Codex sites but does not preserve final-message output. Scenario: run-external-agent no-capture mode never writes its --output file; after stdout is redirected to JSONL, lint-fix-loop codex.log and review-and-fix coder-codex.log/coder-output.log can be empty or missing while tests only check events and wrapper.log
- **Proposed resolution**: Add --output-last-message "$run_dir/codex.log" and --output-last-message "$round_dir/coder-codex.log" to those codex exec argv, keep stdout redirected to events, and test the primary/copied coder log still contains the final response

### FINDING_33:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-lint-fix-loop.sh; scripts/test-run-negotiation-round.sh; skills/review-and-fix/scripts/test-review-and-fix.sh
- **Concern**: Item B tests do not assert telemetry recorded despite the Round 1 acceptance criterion. Scenario: A malformed synthetic event or wrong bucket label could still create a non-empty events file and pass wrapper-log assertions while no token-ledger entry is written, leaving the per-bucket telemetry gap unfixed
- **Proposed resolution**: Extend each Item B harness to use an isolated token ledger or token-record path, emit a parse-codex-usage-compatible usage event, and assert the expected codex-review-fix, codex-lint-fix, and codex-negotiation vendor telemetry record

### FINDING_34:
- **Reviewer(s)**: Codex-dyn-lib-api-surface
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-fix-loop.sh:6-15,217-225
- **Concern**: Plan calls codex_launcher_record_usage_from_events with $PLUGIN_ROOT, but lint-fix-loop.sh does not define PLUGIN_ROOT. Scenario: The successful Codex path reaches the new telemetry call under set -euo pipefail and aborts on an unbound PLUGIN_ROOT before recording usage
- **Proposed resolution**: Define PLUGIN_ROOT near SCRIPT_DIR, e.g. PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}", then source/call through that root

### FINDING_35:
- **Reviewer(s)**: Codex-dyn-lib-api-surface
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/run-negotiation-round.sh:27-35,66-86
- **Concern**: Plan calls external_launcher_record_usage_from_events with $PLUGIN_ROOT, but run-negotiation-round.sh does not define PLUGIN_ROOT. Scenario: The Codex negotiation branch reaches the new telemetry call under set -uo pipefail and aborts on an unbound PLUGIN_ROOT; if unset handling changed, the first argument would not be the required plugin root path
- **Proposed resolution**: Define PLUGIN_ROOT near SCRIPT_DIR, e.g. PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}", and keep sourcing lib-external-launcher-common.sh from SCRIPT_DIR

### FINDING_36:
- **Reviewer(s)**: Cursor-dyn-glob-pattern-logic
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:34-37
- **Concern**: Plan allowlists hyphen Codex JSONL in committed run logs but does not update SECURITY.md. Scenario: SECURITY.md states raw Codex --json streams (*.events.jsonl) are session-local and excluded from larch-logs publication; after the PR, *-codex-events.jsonl would be publishable while policy text still claims all Codex JSONL event streams stay tmpdir-only
- **Proposed resolution**: Add a SECURITY.md subsection distinguishing excluded *.events.jsonl (dot, launcher-style) from allowlisted *-codex-events.jsonl (hyphen, redacted via stage_round_artifact), and note prompt/token leakage posture
