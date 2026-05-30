# Review Round 5

- Mode: `diff`
- 13 accepted, 26 rejected (26 exonerated)

## Accepted Findings

### FINDING_1: code-quality: scripts/launch-claude-review.sh:199-206
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] On failure, full subprocess stderr replay and bounded fenced tail both emit to chat from the same SUBPROCESS_STDERR. A Claude validation error (e.g. prompt outside allowed roots) can flood the transcript with the full stderr plus a near-duplicate fenced tail, exceeding the 5 KB bounded-surfacing goal. Use one chat-facing bounded path; gate _larch_emit_redacted_subprocess_stderr to file-only or voter-specific callers.
- **Suggested revision**: Address the concern above.


### FINDING_11: risk-integration: scripts/test-lib-failed-agent-stderr-tail.sh:43-49
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Non-numeric LARCH_FAILED_AGENT_STDERR_TAIL_LINES fallback to 30 is implemented but not tested per plan edge cases. Setting LARCH_FAILED_AGENT_STDERR_TAIL_LINES=abc could regress to empty/disabled tail behavior without CI catching it. Add harness cases for abc/30abc asserting failed_agent_stderr_tail_lines prints 30 and render still tails 30 lines.
- **Suggested revision**: Address the concern above.


### FINDING_12: risk-integration: scripts/test-launch-claude-subprocess.sh:51-53
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan requires .stderr-tail before .done on failure; test only checks both files exist post-run. Reordering writes so .done precedes .stderr-tail could break collector handoff while tests stay green. Assert ordering via stat timestamps or a stub that errors if .done exists before .stderr-tail is written.
- **Suggested revision**: Address the concern above.


### FINDING_14: risk-integration: skills/review/scripts/collect-findings.sh:283-285
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] replay_collector_failed_stderr_tails is untested when captured collector stderr is empty. Empty capture plus failed results and existing .stderr-tail sidecars might fail to reach chat if replay regresses. Add test-collect-findings case: sidecars present, LARCH_FAILED_AGENT_STDERR_TAIL_LINES=0 on collector, assert wrapper stderr still shows tails.
- **Suggested revision**: Address the concern above.


### FINDING_19: security: scripts/launch-claude-review.sh:199-206
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] On failure the launcher still re-emits the full redacted subprocess stderr file without line/byte bounds in addition to the new bounded stderr-tail fence. A single Claude validation failure can flood the orchestrator transcript with far more tool output than the 30-line/5 KiB tail contract while still being redacted-only. Cap or disable the legacy full stderr re-emit; rely on write_failed_agent_stderr_tail / collector §3.8 for bounded diagnostics.
- **Suggested revision**: Address the concern above.


### FINDING_22: security: scripts/compose-collector-failure-log.sh:57-74
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Failure logs cat .stderr-tail sidecars directly while .launch-stderr uses render_failed_agent_stderr_tail. A corrupted or stale unredacted .stderr-tail sidecar could reach execution-issues before append-tool-failure --redact. Dump .stderr-tail through render_failed_agent_stderr_tail like launch-stderr.
- **Suggested revision**: Address the concern above.


### FINDING_25: correctness: scripts/lib-failed-agent-stderr-tail.sh:168-182
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Ancestor phase .stderr-tail is chosen before the current slot .launch-stderr. Phase 2 codex leaves foo-phase2.txt.stderr-tail; phase 3 Claude launcher fails with only foo-phase3.txt.launch-stderr (e.g. timeout cap). Collector/chat show the phase-2 codex tail, not the launcher error. Check ${reviewer_file}.launch-stderr (render on demand) before collector_stderr_tail_candidates ancestor .stderr-tail lookup; add a harness with competing phase2 tail and phase3 launch-stderr.
- **Suggested revision**: Address the concern above.


### FINDING_31: correctness: scripts/lib-failed-agent-stderr-tail.sh:156-183
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Collector launch-stderr resolution omits ancestor-phase files required by the plan. Final REVIEWER_FILE is a later phase stem with no .launch-stderr while an earlier phase's .launch-stderr holds the launcher validation error; chat and dedup never surface it. Walk phase stems for the first non-empty *.launch-stderr (mirror .stderr-tail fallback) or amend the plan if primary-stem-only is intended.
- **Suggested revision**: Address the concern above.


### FINDING_40: **security** `scripts/collect-agent-results.sh:170-172,1434-1446` — `resolve_collector_stderr_tail_file` prefers an existing `${candidate}.stderr-tail` and §3.8 `_emit_collector_stderr_tail_file` streams that file to FD 2 with only `sanitize_diagnostic_line` (control-character stripping), not `redact-secrets.sh` or `redact-tmpdir-paths.sh`. Production writers use `write_failed_agent_stderr_tail` (dual-redacted at write time), but any pre-existing sidecar beside reviewer outputs is treated as chat-ready; `skills/review/scripts/test-collect-findings.sh:112-118` plants unredacted tails and expects them verbatim on FD 2, so raw subprocess or tool output placed in `.stderr-tail` bypasses the #3202 redaction pipeline. **Suggested fix:** At emit time, never trust `.stderr-tail` bytes; re-run `render_failed_agent_stderr_tail` from the authoritative source (`.sidecar`, `${OUTPUT}.stderr`, or `.launch-stderr`) or pipe the sidecar through both redactors before `larch_err`.
- **Reviewer**: dyn-redaction-coverage-output.txt
- **Concern**: - **security** `scripts/collect-agent-results.sh:170-172,1434-1446` — `resolve_collector_stderr_tail_file` prefers an existing `${candidate}.stderr-tail` and §3.8 `_emit_collector_stderr_tail_file` streams that file to FD 2 with only `sanitize_diagnostic_line` (control-character stripping), not `redact-secrets.sh` or `redact-tmpdir-paths.sh`. Production writers use `write_failed_agent_stderr_tail` (dual-redacted at write time), but any pre-existing sidecar beside reviewer outputs is treated as chat-ready; `skills/review/scripts/test-collect-findings.sh:112-118` plants unredacted tails and expects them verbatim on FD 2, so raw subprocess or tool output placed in `.stderr-tail` bypasses the #3202 redaction pipeline. **Suggested fix:** At emit time, never trust `.stderr-tail` bytes; re-run `render_failed_agent_stderr_tail` from the authoritative source (`.sidecar`, `${OUTPUT}.stderr`, or `.launch-stderr`) or pipe the sidecar through both redactors before `larch_err`.
- **Suggested revision**: Address the concern above.


### FINDING_41: **security** `scripts/compose-collector-failure-log.sh:57-74` — `dump_section` applies `_redacted_launch_stderr_body` (via `render_failed_agent_stderr_tail`) for `*.launch-stderr`, but uses raw `cat` for `*.stderr-tail` while still embedding `${REVIEWER_FILE}.diag` unredacted. Composed output is appended to `execution-issues.md` through `append-tool-failure.sh --redact`, which runs only `redact-secrets.sh`, not `redact-tmpdir-paths.sh`, so tmpdir/session paths in a trusted-but-wrong `.stderr-tail` or `.diag` can reach durable operator logs without the dual pipeline used at capture. **Suggested fix:** Route `.stderr-tail` through `render_failed_agent_stderr_tail` (or an equivalent read-time dual-redact helper) in `dump_section`, matching the `.launch-stderr` branch.
- **Reviewer**: dyn-redaction-coverage-output.txt
- **Concern**: - **security** `scripts/compose-collector-failure-log.sh:57-74` — `dump_section` applies `_redacted_launch_stderr_body` (via `render_failed_agent_stderr_tail`) for `*.launch-stderr`, but uses raw `cat` for `*.stderr-tail` while still embedding `${REVIEWER_FILE}.diag` unredacted. Composed output is appended to `execution-issues.md` through `append-tool-failure.sh --redact`, which runs only `redact-secrets.sh`, not `redact-tmpdir-paths.sh`, so tmpdir/session paths in a trusted-but-wrong `.stderr-tail` or `.diag` can reach durable operator logs without the dual pipeline used at capture. **Suggested fix:** Route `.stderr-tail` through `render_failed_agent_stderr_tail` (or an equivalent read-time dual-redact helper) in `dump_section`, matching the `.launch-stderr` branch.
- **Suggested revision**: Address the concern above.


### FINDING_43: **security** `scripts/launch-claude-review.sh:186-203` — On non-zero exit, `_larch_emit_redacted_subprocess_stderr` replays the full captured subprocess stderr file to chat (unbounded) and can run with only `redact-secrets.sh` when `redact-tmpdir-paths.sh` is absent (`pipeline="$redact"`), while the new bounded tail path in `lib-failed-agent-stderr-tail.sh:103` requires both scripts. The same failure also calls `emit_failed_agent_stderr_tail_larch_err`, so operators may see duplicate diagnostics with inconsistent redaction strength. **Suggested fix:** Align subprocess replay with the bounded tail contract (use `render_failed_agent_stderr_tail` / drop full-file replay when the sidecar exists), and fail closed unless both redactors are executable—mirror `render_failed_agent_stderr_tail`’s guard.
- **Reviewer**: dyn-redaction-coverage-output.txt
- **Concern**: - **security** `scripts/launch-claude-review.sh:186-203` — On non-zero exit, `_larch_emit_redacted_subprocess_stderr` replays the full captured subprocess stderr file to chat (unbounded) and can run with only `redact-secrets.sh` when `redact-tmpdir-paths.sh` is absent (`pipeline="$redact"`), while the new bounded tail path in `lib-failed-agent-stderr-tail.sh:103` requires both scripts. The same failure also calls `emit_failed_agent_stderr_tail_larch_err`, so operators may see duplicate diagnostics with inconsistent redaction strength. **Suggested fix:** Align subprocess replay with the bounded tail contract (use `render_failed_agent_stderr_tail` / drop full-file replay when the sidecar exists), and fail closed unless both redactors are executable—mirror `render_failed_agent_stderr_tail`’s guard.
- **Suggested revision**: Address the concern above.


### FINDING_47: **risk-integration** `scripts/hook-anti-read-poll.sh:16-46,316-323` — Widening `hooks/hooks.json` to `Read|Bash` means every Bash PostToolUse runs this hook, but non-polling Bash does not exit before expensive work: after the `tool_name` gate it still performs multiple full-payload `jq` extractions (`cwd`, `session_id`/`conversation_id`), two `cksum` passes, `mkdir`/`chmod` on `${TMPDIR}/larch-read-poll`, then `jq` for `tool_input.command` and the full `extract_bash_task_output_poll_token` path (sed normalization, line loop, segment split, grep read-verb checks). A call like `ls` (harness `=== non-poll Bash is ignored ===`) still pays that cost; only state-file read/write is skipped when no token matches. With Bash far more frequent than Read, this materially increases per-invocation hook latency and the chance of brushing the 5s `hooks/hooks.json` timeout on large multiline commands, without a cheap prefilter (e.g. exit 0 when `command` lacks `tasks/` + `.output`). **Suggested fix:** Add a fast reject immediately after parsing `tool_input.command` (case-insensitive `*tasks/*` + `*.output*` substring) before session hashing and `state_dir` setup; defer `mkdir` and TSV I/O until a token is found. Optionally move `cwd`/session `jq` below that gate for the Bash branch only.
- **Reviewer**: dyn-hook-blast-radius-output.txt
- **Concern**: - **risk-integration** `scripts/hook-anti-read-poll.sh:16-46,316-323` — Widening `hooks/hooks.json` to `Read|Bash` means every Bash PostToolUse runs this hook, but non-polling Bash does not exit before expensive work: after the `tool_name` gate it still performs multiple full-payload `jq` extractions (`cwd`, `session_id`/`conversation_id`), two `cksum` passes, `mkdir`/`chmod` on `${TMPDIR}/larch-read-poll`, then `jq` for `tool_input.command` and the full `extract_bash_task_output_poll_token` path (sed normalization, line loop, segment split, grep read-verb checks). A call like `ls` (harness `=== non-poll Bash is ignored ===`) still pays that cost; only state-file read/write is skipped when no token matches. With Bash far more frequent than Read, this materially increases per-invocation hook latency and the chance of brushing the 5s `hooks/hooks.json` timeout on large multiline commands, without a cheap prefilter (e.g. exit 0 when `command` lacks `tasks/` + `.output`). **Suggested fix:** Add a fast reject immediately after parsing `tool_input.command` (case-insensitive `*tasks/*` + `*.output*` substring) before session hashing and `state_dir` setup; defer `mkdir` and TSV I/O until a token is found. Optionally move `cwd`/session `jq` below that gate for the Bash branch only.
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: scripts/lib-failed-agent-stderr-tail.sh:156-184
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] resolve_collector_stderr_tail_file only checks launch-stderr on the final REVIEWER_FILE path, not on earlier waterfall phase paths walked for .stderr-tail. Phase-1 launcher failure writes slot.txt.launch-stderr but terminal REVIEWER_FILE is slot-phase3.txt; collector finds no phase-3 tail and never reads base launch-stderr, so the #3202 launcher failure stays invisible in chat. While iterating collector_stderr_tail_candidates, also render from each ${_candidate}.launch-stderr before giving up (or add explicit phase-1 launch-stderr to the candidate list).
- **Suggested revision**: Address the concern above.


