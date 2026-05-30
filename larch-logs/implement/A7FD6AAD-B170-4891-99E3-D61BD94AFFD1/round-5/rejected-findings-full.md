### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: correctness: scripts/lib-failed-agent-stderr-tail.sh:203-224
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Aggressive digit normalization in failed_agent_stderr_signature can collapse distinct failures. Two errors differing only by line numbers hash equal; second failure is over-suppressed. Tighten normalization if production shows false dedup; document limitation in operator docs.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: risk-integration: scripts/test-launch-claude-review.sh:401-356
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Plan acceptance requires preserved full subprocess stderr re-emit for dispatch-code-voters; new tests cover fence/sidecar only. Removing _larch_emit_redacted_subprocess_stderr while keeping bounded fence could break voter execution-issues warnings undetected. Assert redacted full-line subprocess stderr on FD 2 in addition to the fenced tail block.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: risk-integration: scripts/test-dispatch-with-waterfall.sh:2848-2849
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Waterfall test only asserts .launch-stderr file exists on phase-3 hard fail. Empty or wrong sidecar could slip through; launcher root cause might stay invisible until production. Assert non-empty launch-stderr content from stub or wire a minimal waterfall-to-collector surfacing check.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: risk-integration: skills/review/scripts/test-collect-findings.sh:91-94
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Test comments refer to tee but implementation uses stderr file capture and replay. Future edits may reintroduce wrong tee pattern believing tests require it. Align comments and failure messages with capture-and-replay behavior in collect-findings.sh.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: code-quality: scripts/run-external-agent.sh:297-316
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] FAILED --capture-stdout path can print redacted output preview and fenced stderr-tail from the same OUTPUT_FILE. Merged-stderr cursor/codex failures show duplicate redacted blocks in FD 2 for the #3119-style empty-output case. Skip the preview when _stderr_src equals OUTPUT_FILE or content would duplicate the sidecar fence.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: risk-integration: skills/review/scripts/collect-findings.sh:283-290
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] replay_collector_failed_stderr_tails runs when collector stderr is empty and does not apply failed_agent_stderr_signature dedup. Quiet-session routing can drop §3.8 stderr capture; replay then prints one full tail per failed slot even when root causes match multiplying redacted content in chat. Share collector dedup logic in replay or tee collect-agent-results stderr so §3.8 output is always captured once.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: security: SECURITY.md:256
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Publishable *.stderr-tail artifacts live under the larch-logs gitleaks path allowlist after dual redaction at publish. A novel secret shape missed by redact-secrets.sh can be committed to a public fork without gitleaks catching it. Keep documented ops discipline; consider targeted gitleaks rules or a harness scan for stderr-tail artifacts outside allowlisted fixtures.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: security: scripts/lib-failed-agent-stderr-tail.sh:105-106
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Redaction spool temps use default mktemp permissions without chmod 600. On a shared TMPDIR host another user could read spool bytes between tail/redact and rm. chmod 600 immediately after each mktemp for spool and launch-stderr render temps.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_26

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_26: architecture: skills/review/scripts/collect-findings.sh:87-149
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] replay_collector_failed_stderr_tails has no signature dedup. When collector_stderr stays empty but .stderr-tail sidecars exist, /review replays one full fenced block per failed slot (no ↩ suppression). Reuse failed_agent_stderr_signature and the collector sig-map logic in replay, or require collector stderr capture so replay is rare.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_27

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_27: correctness: scripts/lib-failed-agent-stderr-tail.sh:193-207
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Phase stem fallback can surface an older phase tail for a new phase failure. Phase 3 fails with empty sidecar; phase 2 still has .stderr-tail from an earlier failure. Operator sees phase-2 root cause for a phase-3 slot. Narrow fallback conditions or rm ancestor .stderr-tail when advancing phases; document limits in lib-failed-agent-stderr-tail.md.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_28

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_28: correctness: scripts/lib-failed-agent-stderr-tail.sh:203-224
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Heuristic dedup signature over-normalizes digits and paths. Distinct API/port failures hash equal; slots after the first emit only the suppression line and hide differing stderr. Reduce normalization aggressiveness or dedup on exact redacted tail bytes only.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_29

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_29: correctness: scripts/collect-agent-results.sh:1470-1472
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] cap_hit results skip §3.8 stderr-tail emission. A cap-hit reviewer still has diagnostic stderr in sidecars; operator never sees it in chat or dedup pass. Emit tails for cap_hit unless product semantics require silence.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality: scripts/collect-agent-results.sh:1434-1494
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Collector reimplements fenced tail emission instead of calling a lib helper; test enforces the local name. Two sanitization/emission paths can drift (lib vs collector); harder to extend replay/dedup consistently. Add emit_failed_agent_stderr_tail_file_larch_err to the lib; delete _emit_collector_stderr_tail_file; fix test-run-external-agent assertion.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_30

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_30: security: scripts/lib-failed-agent-stderr-tail.sh:964-967
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Redaction can empty the spool; render/write fail quietly. Stderr is only tokens; after redact the spool is empty, .stderr-tail is removed, chat gets at most WARN unavailable—same unrecoverable state as #3119 for secret-heavy stderr. Surface a bounded placeholder when source was non-empty but render returned empty.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_32

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_32: correctness: scripts/test-launch-claude-subprocess.sh:51-53
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Harness does not assert .stderr-tail is written before .done. A future reorder could break the collector handoff race while tests still pass. Assert mtime ordering or document-order in the failure-path case.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_33

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_33: architecture: scripts/lib-failed-agent-stderr-tail.sh:12-13
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Lib no longer matches plan's dependency-free / single-raw-&gt;2 invariant. Plan-level quiet-init guarantees rely on caller discipline and agent-lint exclusions rather than structure. Update plan/docs to lib-quiet coupling or split raw emitters from the sourced lib.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_34

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_34: correctness: skills/review/scripts/collect-findings.sh:283-284
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Replay fallback does not apply collector signature dedup. If collector stderr were empty with multiple identical .stderr-tail sidecars, /review could emit duplicate fences. Reuse dedup in replay or tee collector stderr live per FINDING_3.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_35

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_35: **code-quality** `scripts/collect-agent-results.sh:1434-1447`, `scripts/lib-failed-agent-stderr-tail.sh:186-196`, `skills/review/scripts/collect-findings.sh:74-85` — §3.8 and the `/review` replay path reimplement the same fenced tail loop locally (`_emit_collector_stderr_tail_file`, `_write_failed_stderr_tail_block`) instead of calling a single lib helper, while `scripts/lib-failed-agent-stderr-tail.md:30` claims the collector emits via shared lib machinery. The lib only exposes `emit_failed_agent_stderr_tail_larch_err` for `${output_file}.stderr-tail`, not arbitrary tail paths (retry/NS-retry/phase/`larch-launch-stderr-tail.*`), so the duplication is understandable but brittle: fence text, sanitization, and quiet routing can drift across three sites. `scripts/test-run-external-agent.sh:451-454` even asserts the collector-local symbol exists, locking in the fork. **Suggested fix:** Add `emit_failed_agent_stderr_tail_file_larch_err <tail_file>` (and optionally a dedup-aware batch helper) to `lib-failed-agent-stderr-tail.sh`, call it from §3.8 and from `replay_collector_failed_stderr_tails`, delete the parallel emitters, and point the regression grep at the lib function name.
- **Reviewer**: dyn-fd-contract-output.txt
- **Concern**: - **code-quality** `scripts/collect-agent-results.sh:1434-1447`, `scripts/lib-failed-agent-stderr-tail.sh:186-196`, `skills/review/scripts/collect-findings.sh:74-85` — §3.8 and the `/review` replay path reimplement the same fenced tail loop locally (`_emit_collector_stderr_tail_file`, `_write_failed_stderr_tail_block`) instead of calling a single lib helper, while `scripts/lib-failed-agent-stderr-tail.md:30` claims the collector emits via shared lib machinery. The lib only exposes `emit_failed_agent_stderr_tail_larch_err` for `${output_file}.stderr-tail`, not arbitrary tail paths (retry/NS-retry/phase/`larch-launch-stderr-tail.*`), so the duplication is understandable but brittle: fence text, sanitization, and quiet routing can drift across three sites. `scripts/test-run-external-agent.sh:451-454` even asserts the collector-local symbol exists, locking in the fork. **Suggested fix:** Add `emit_failed_agent_stderr_tail_file_larch_err <tail_file>` (and optionally a dedup-aware batch helper) to `lib-failed-agent-stderr-tail.sh`, call it from §3.8 and from `replay_collector_failed_stderr_tails`, delete the parallel emitters, and point the regression grep at the lib function name.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_36

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_36: **code-quality** `scripts/lib-failed-agent-stderr-tail.sh:4-5,15-40,227-236` — The header and contract still describe a “no raw `>&2` except `emit_failed_agent_stderr_tail_raw`” invariant, but the library now sources `lib-quiet.sh` and contains additional raw-`>&2` fallbacks in `_failed_agent_stderr_tail_warn_unavailable` and `_emit_failed_agent_stderr_tail_line`, plus `emit_failed_agent_stderr_tail_file_raw`. S041 only scans each file for post-`larch_quiet_init` writes, so this is not an active lint break today, but it weakens the stated quiet-init safety story and invites a future quiet caller to invoke `emit_failed_agent_stderr_tail_file_raw` and route fences into the quiet log instead of chat. **Suggested fix:** Align the header/contract with reality (document `larch_err` as the quiet-safe path, `emit_failed_agent_stderr_tail_file_raw` as non-quiet-only), and either move the raw emitter to `run-external-agent.sh` or add a comment/assertion that quiet-init callers must never call the raw variants.
- **Reviewer**: dyn-fd-contract-output.txt
- **Concern**: - **code-quality** `scripts/lib-failed-agent-stderr-tail.sh:4-5,15-40,227-236` — The header and contract still describe a “no raw `>&2` except `emit_failed_agent_stderr_tail_raw`” invariant, but the library now sources `lib-quiet.sh` and contains additional raw-`>&2` fallbacks in `_failed_agent_stderr_tail_warn_unavailable` and `_emit_failed_agent_stderr_tail_line`, plus `emit_failed_agent_stderr_tail_file_raw`. S041 only scans each file for post-`larch_quiet_init` writes, so this is not an active lint break today, but it weakens the stated quiet-init safety story and invites a future quiet caller to invoke `emit_failed_agent_stderr_tail_file_raw` and route fences into the quiet log instead of chat. **Suggested fix:** Align the header/contract with reality (document `larch_err` as the quiet-safe path, `emit_failed_agent_stderr_tail_file_raw` as non-quiet-only), and either move the raw emitter to `run-external-agent.sh` or add a comment/assertion that quiet-init callers must never call the raw variants.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: code-quality: skills/review/scripts/collect-findings.sh:87-150
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] replay_collector_failed_stderr_tails lacks signature dedup and runs only when captured collector stderr is empty. If §3.8 stderr is not captured but sidecars exist, /review can emit N full tails for N identical root causes. Tee collector stderr like plan-review-loop or share dedup replay helper with collect-agent-results §3.8.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_42

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_42: **security** `skills/review/scripts/collect-findings.sh:143-147,286-290` — On successful collect (`collector_rc=0`), `replay_collector_failed_stderr_tails` and the subsequent replay of `$collector_stderr` copy tail blocks to FD 2 with no `redact-secrets.sh` / `redact-tmpdir-paths.sh` pass (FINDING_3 tee path). That inherits the `.stderr-tail` trust model above; a collector failure path at `298-299` applies secrets redaction only, not tmpdir redaction, on the combined log. **Suggested fix:** Pipe all collector stderr replay (live tee and `replay_collector_failed_stderr_tails` output) through `redact-tmpdir-paths.sh | redact-secrets.sh` before `printf`/`larch_err`, or only replay tails produced by a read-time `render_failed_agent_stderr_tail` call.
- **Reviewer**: dyn-redaction-coverage-output.txt
- **Concern**: - **security** `skills/review/scripts/collect-findings.sh:143-147,286-290` — On successful collect (`collector_rc=0`), `replay_collector_failed_stderr_tails` and the subsequent replay of `$collector_stderr` copy tail blocks to FD 2 with no `redact-secrets.sh` / `redact-tmpdir-paths.sh` pass (FINDING_3 tee path). That inherits the `.stderr-tail` trust model above; a collector failure path at `298-299` applies secrets redaction only, not tmpdir redaction, on the combined log. **Suggested fix:** Pipe all collector stderr replay (live tee and `replay_collector_failed_stderr_tails` output) through `redact-tmpdir-paths.sh | redact-secrets.sh` before `printf`/`larch_err`, or only replay tails produced by a read-time `render_failed_agent_stderr_tail` call.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_48

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_48: **risk-integration** `scripts/hook-anti-read-poll.sh:24-34,208-214` — Task-output counters key on `session_hash` derived from `session_id` → `conversation_id` → `nosession` (or `nosession-${HOOK_ANTI_READ_POLL_DISCRIMINATOR}`). When both IDs are absent—the default in most harness payloads via `mk_bash_payload` / `mk_payload` without a fifth argument—all concurrent callers share one `state-taskout-<nosession-hash>-<cwd_hash>-<task_id>.tsv` bucket for 600s. That can produce spurious “Task-output poll detected” reminders when unrelated sessions on the same machine/repo cwd poll different tasks with the same normalized id, or when parallel offline runs share `TMPDIR` and cwd. The harness only isolates via `HOOK_ANTI_READ_POLL_DISCRIMINATOR` in the dedicated `=== nosession discriminators ===` case; routine tests do not set it. **Suggested fix:** Prefer a platform-stable discriminator when metadata is missing (e.g. hook-provided process/session token if Claude Code exposes one), or hash additional fields (`transcript_path`, `hook_event_id`, parent PID from env). Document that production relies on `session_id`/`conversation_id` always being present; add a harness-wide default discriminator (or require `session_id` in all test payloads) so parallel `make` shards cannot cross-talk.
- **Reviewer**: dyn-hook-blast-radius-output.txt
- **Concern**: - **risk-integration** `scripts/hook-anti-read-poll.sh:24-34,208-214` — Task-output counters key on `session_hash` derived from `session_id` → `conversation_id` → `nosession` (or `nosession-${HOOK_ANTI_READ_POLL_DISCRIMINATOR}`). When both IDs are absent—the default in most harness payloads via `mk_bash_payload` / `mk_payload` without a fifth argument—all concurrent callers share one `state-taskout-<nosession-hash>-<cwd_hash>-<task_id>.tsv` bucket for 600s. That can produce spurious “Task-output poll detected” reminders when unrelated sessions on the same machine/repo cwd poll different tasks with the same normalized id, or when parallel offline runs share `TMPDIR` and cwd. The harness only isolates via `HOOK_ANTI_READ_POLL_DISCRIMINATOR` in the dedicated `=== nosession discriminators ===` case; routine tests do not set it. **Suggested fix:** Prefer a platform-stable discriminator when metadata is missing (e.g. hook-provided process/session token if Claude Code exposes one), or hash additional fields (`transcript_path`, `hook_event_id`, parent PID from env). Document that production relies on `session_id`/`conversation_id` always being present; add a harness-wide default discriminator (or require `session_id` in all test payloads) so parallel `make` shards cannot cross-talk.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: code-quality: scripts/lib-failed-agent-stderr-tail.sh:209-224
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Global digit normalization in failed_agent_stderr_signature may over-collapse distinct failures. Two slots failing with different HTTP 401 vs 403 messages could hash equal; second slot suppressed with no distinct tail shown. Narrow sed normalization or dedup on exact redacted tail equality; add harness for distinct numeric messages.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: code-quality: scripts/collect-agent-results.sh:1451-1469
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Inline KV parsing in the dedup loop duplicates patterns used elsewhere in the collector. Future field-order or parsing fixes may update one loop and miss dedup. Extract a shared result_field parser helper.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: correctness: scripts/run-external-agent.sh:263-270
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] TIMED_OUT selects stderr source after appending wrapper text to .diag, unlike FAILED and unlike plan FINDING_6. Empty sidecar and output at timeout: tail is only the generic timeout line from .diag, not agent stderr. Select _stderr_src before appending the timeout line to .diag, matching the FAILED branch.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: correctness: skills/review/scripts/collect-findings.sh:87-148
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] replay_collector_failed_stderr_tails omits collector signature dedup. Collector stderr empty but identical .stderr-tail sidecars on many slots: replay emits N full fences instead of one tail plus suppression lines. Share the §3.8 signature map in replay, or ensure collector stderr always captures §3.8 output when sidecars exist.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

