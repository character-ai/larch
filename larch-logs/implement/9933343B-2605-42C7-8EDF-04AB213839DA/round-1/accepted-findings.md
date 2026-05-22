### FINDING_1: correctness: .claude/skills/audit-runs/scripts/audit-scan-run.sh:370-372
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] cursor-ci-stall-causes aggregate jq failure yields channels {} while count lists all matched files, contradicting informational histogram intent and audit-scan-run.md implication that UNKNOWN absorbs bad/missing channels. Three sidecars where one has .channel as an array or histogram jq errors: emitted NDJSON shows count=3 and channels={}, so audits report stalls without any channel distribution. Mirror ns-retry-sidecars UNKNOWN rollup when count>0 but channels_json is {} after jq; optionally add channels_detail; update audit-scan-run.md.
- **Suggested revision**: Address the concern above.


### FINDING_10: security: scripts/lib-cursor-launcher-common.sh:139-151
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] New stall sidecar runs ps -ef and greps [c]ursor (80 lines), capturing system-wide argv lines. On shared hosts, unrelated users processes whose argv matches cursor can be written into committed cursor-ci-stall-*.json run logs, leaking their commands/paths. Restrict ps to current uid or to the PID subtree rooted at target_pid; document residual risk.
- **Suggested revision**: Address the concern above.


### FINDING_11: security: scripts/lib-cursor-launcher-common.sh:167-189
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] git status --porcelain and rebase patch excerpt are embedded in JSON sidecars. Patch hunks or rare embedded secrets in working tree can be copied into durable run-log artifacts used for audits. Add redaction/size caps aligned with append-tool-failure --redact or omit rebase excerpt unless rebase is active.
- **Suggested revision**: Address the concern above.


### FINDING_12: security: scripts/lib-cursor-launcher-common.sh:160-165
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Transcript tails from OUTPUT and OUTPUT.diag are persisted in last_transcript_lines. If stdout/diag ever contained sensitive session strings, sidecars increase exposure versus prior behavior. Redact or cap transcript capture similarly to other log writers.
- **Suggested revision**: Address the concern above.


### FINDING_15: security: scripts/lib-cursor-launcher-common.sh:139-199
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Stall sidecars store raw ps -ef and lsof output without redaction. Committed or shared run logs can leak API keys, tokens, or sensitive argv from Cursor or wrapper processes visible in process listings. Apply a redaction pass before jq write, align with append-tool-failure redaction, or restrict publication of raw sidecars.
- **Suggested revision**: Address the concern above.


### FINDING_16: risk-integration: scripts/lib-cursor-launcher-common.sh:160-193
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] last_transcript_lines merges stdout then stderr tails, not interleaved last-50. Audits may draw wrong conclusions about the final event order before a stall when output alternates between streams. Use one combined chronological tail or document the non-interleaved contract explicitly.
- **Suggested revision**: Address the concern above.


### FINDING_17: correctness: scripts/lib-cursor-launcher-common.sh:171-199
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Sidecar path uses second-granularity timestamp only. Two stalls in the same second could collide on filenames. Add PID or random suffix to guarantee uniqueness.
- **Suggested revision**: Address the concern above.


### FINDING_19: correctness: scripts/lib-cursor-launcher-common.sh:160-193
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Transcript capture uses tail -n 25 per stream while plan asks for last 50 lines of stdout/stderr; jq only trims combined lines. Evidence only in stdout lines 26-50 from EOF is never ingested, so stall JSON can miss the fragment needed to classify stdout stalls. Raise tail depth to 50 per stream (or implement the plan’s exact 50-line semantics) and align docs.
- **Suggested revision**: Address the concern above.


### FINDING_2: correctness: scripts/lib-cursor-launcher-common.sh:171-199
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Sidecar filename uses only unix seconds; second stall in same second overwrites prior JSON via mv -f. Two stall sidecars in one second: first diagnostic file is lost, weakening Phase 1 forensics. Use pid, nanoseconds, or mktemp suffix in basename to guarantee uniqueness.
- **Suggested revision**: Address the concern above.


### FINDING_20: correctness: .claude/skills/audit-runs/scripts/audit-scan-run.sh:353-372
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] cursor-ci-stall-causes scan count equals glob file count including invalid JSON. Stray or corrupt cursor-ci-stall-*.json files inflate count vs real stalls, skewing audit summaries. Count only jq-parseable files or add separate parsed vs files fields plus documentation.
- **Suggested revision**: Address the concern above.


### FINDING_24: **correctness** `scripts/lib-cursor-launcher-common.sh:171-199` — The sidecar basename is `cursor-ci-stall-$(date +%s).json` with a single shared `*.tmp` sibling, so two emissions in the same second into the same resolved `round-N/` directory (two concurrent `launch-cursor-ci.sh` processes sharing one `IMPLEMENT_TMPDIR`, or any other same-second collision) contend for the same paths; the second `mv` can overwrite the first artifact or race on the temp file. **Suggested fix:** make names unique with a suffix such as `$$`, `$RANDOM`, or a `mktemp`-generated stem under `sidecar_dir`, then atomically rename to the final name.
- **Reviewer**: dyn-shell-correctness-output.txt
- **Concern**: - **correctness** `scripts/lib-cursor-launcher-common.sh:171-199` — The sidecar basename is `cursor-ci-stall-$(date +%s).json` with a single shared `*.tmp` sibling, so two emissions in the same second into the same resolved `round-N/` directory (two concurrent `launch-cursor-ci.sh` processes sharing one `IMPLEMENT_TMPDIR`, or any other same-second collision) contend for the same paths; the second `mv` can overwrite the first artifact or race on the temp file. **Suggested fix:** make names unique with a suffix such as `$$`, `$RANDOM`, or a `mktemp`-generated stem under `sidecar_dir`, then atomically rename to the final name.
- **Suggested revision**: Address the concern above.


### FINDING_25: **correctness** `scripts/lib-cursor-launcher-common.sh:154-169,318-332` — After `elapsed` crosses the stall threshold, `cursor_launcher_emit_cursor_ci_stall_json_sidecar` runs `lsof`, two `tail`s, and `git status` / `git rebase --show-current-patch` **before** any `SIGTERM`/`SIGKILL` to the wrapper or children. `|| true` only masks non-zero exit, not hangs (index lock, slow hooks, huge FD tables), so this new work can postpone kill delivery and leave the “stalled” cursor alive longer than the stall detector intended. **Suggested fix:** cap wall time for each diagnostic (e.g. `timeout`/`gtimeout` when present), move best-effort capture after sending `SIGTERM`, or run the heavy capture in the background with an explicit upper wait bound so the kill path cannot be blocked indefinitely.
- **Reviewer**: dyn-shell-correctness-output.txt
- **Concern**: - **correctness** `scripts/lib-cursor-launcher-common.sh:154-169,318-332` — After `elapsed` crosses the stall threshold, `cursor_launcher_emit_cursor_ci_stall_json_sidecar` runs `lsof`, two `tail`s, and `git status` / `git rebase --show-current-patch` **before** any `SIGTERM`/`SIGKILL` to the wrapper or children. `|| true` only masks non-zero exit, not hangs (index lock, slow hooks, huge FD tables), so this new work can postpone kill delivery and leave the “stalled” cursor alive longer than the stall detector intended. **Suggested fix:** cap wall time for each diagnostic (e.g. `timeout`/`gtimeout` when present), move best-effort capture after sending `SIGTERM`, or run the heavy capture in the background with an explicit upper wait bound so the kill path cannot be blocked indefinitely.
- **Suggested revision**: Address the concern above.


### FINDING_28: **risk-integration** `.claude/skills/audit-runs/scripts/audit-scan-run.sh:366-372` — `channels_json` is built with `jq -s '…' 2>/dev/null` without `-c` (or an equivalent compact pass). Default `jq` formatting is pretty-printed and can embed newlines, so the following `emit "{\"scan\":\"cursor-ci-stall-causes\",…,\"channels\":$channels_json}"` can write a logical NDJSON record across multiple physical lines and break line-oriented consumers of the audit scan stream even though each fragment is valid JSON. **Suggested fix:** build `channels_json` with compact output, e.g. add `-c` to that `jq -s` invocation (matching patterns like `scan_ns_retry_sidecars` which uses `jq … -c`), or pipe the result through `jq -c .`.
- **Reviewer**: dyn-bash32-portability-output.txt
- **Concern**: - **risk-integration** `.claude/skills/audit-runs/scripts/audit-scan-run.sh:366-372` — `channels_json` is built with `jq -s '…' 2>/dev/null` without `-c` (or an equivalent compact pass). Default `jq` formatting is pretty-printed and can embed newlines, so the following `emit "{\"scan\":\"cursor-ci-stall-causes\",…,\"channels\":$channels_json}"` can write a logical NDJSON record across multiple physical lines and break line-oriented consumers of the audit scan stream even though each fragment is valid JSON. **Suggested fix:** build `channels_json` with compact output, e.g. add `-c` to that `jq -s` invocation (matching patterns like `scan_ns_retry_sidecars` which uses `jq … -c`), or pipe the result through `jq -c .`.
- **Suggested revision**: Address the concern above.


### FINDING_3: risk-integration: scripts/lib-cursor-launcher-common.sh:154-171
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Stall path runs lsof before kill; lsof can block, delaying SIGTERM after stall is already detected. Rare stuck kernel state: operator waits well beyond stall_threshold before cursor is terminated. Wrap lsof with a short hard timeout or defer expensive capture after initiating kill per policy.
- **Suggested revision**: Address the concern above.


### FINDING_5: risk-integration: scripts/audit-scan-run.sh:354-372
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Histogram jq rollup can fail while count stays positive Audit NDJSON shows count>0 with channels {} misleading no channel data Emit UNKNOWN bucket matching count or error with detail on rollup failure
- **Suggested revision**: Address the concern above.


### FINDING_6: correctness: scripts/lib-cursor-launcher-common.sh:171-199
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Sidecar filename uses second-granularity unix time Two stalls same second can collide on mv and lose one JSON sidecar Include pid random suffix or mktemp-based unique name per stall
- **Suggested revision**: Address the concern above.


### FINDING_7: risk-integration: scripts/test-launch-cursor-ci.sh:250-279
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Missing assertion for git_state object from plan Phase 1 Regression in git capture could ship unnoticed Add jq -e checks on .git_state shape optional porcelain in harness
- **Suggested revision**: Address the concern above.


