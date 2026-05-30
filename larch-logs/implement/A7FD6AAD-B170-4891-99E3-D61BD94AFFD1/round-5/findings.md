### FINDING_1: code-quality: scripts/launch-claude-review.sh:199-206
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] On failure, full subprocess stderr replay and bounded fenced tail both emit to chat from the same SUBPROCESS_STDERR. A Claude validation error (e.g. prompt outside allowed roots) can flood the transcript with the full stderr plus a near-duplicate fenced tail, exceeding the 5 KB bounded-surfacing goal. Use one chat-facing bounded path; gate _larch_emit_redacted_subprocess_stderr to file-only or voter-specific callers.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/run-external-agent.sh:297-316
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] FAILED --capture-stdout path can print redacted output preview and fenced stderr-tail from the same OUTPUT_FILE. Merged-stderr cursor/codex failures show duplicate redacted blocks in FD 2 for the #3119-style empty-output case. Skip the preview when _stderr_src equals OUTPUT_FILE or content would duplicate the sidecar fence.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/collect-agent-results.sh:1434-1494
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Collector reimplements fenced tail emission instead of calling a lib helper; test enforces the local name. Two sanitization/emission paths can drift (lib vs collector); harder to extend replay/dedup consistently. Add emit_failed_agent_stderr_tail_file_larch_err to the lib; delete _emit_collector_stderr_tail_file; fix test-run-external-agent assertion.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/review/scripts/collect-findings.sh:87-150
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] replay_collector_failed_stderr_tails lacks signature dedup and runs only when captured collector stderr is empty. If §3.8 stderr is not captured but sidecars exist, /review can emit N full tails for N identical root causes. Tee collector stderr like plan-review-loop or share dedup replay helper with collect-agent-results §3.8.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/lib-failed-agent-stderr-tail.sh:209-224
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Global digit normalization in failed_agent_stderr_signature may over-collapse distinct failures. Two slots failing with different HTTP 401 vs 403 messages could hash equal; second slot suppressed with no distinct tail shown. Narrow sed normalization or dedup on exact redacted tail equality; add harness for distinct numeric messages.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: scripts/collect-agent-results.sh:1451-1469
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Inline KV parsing in the dedup loop duplicates patterns used elsewhere in the collector. Future field-order or parsing fixes may update one loop and miss dedup. Extract a shared result_field parser helper.
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: scripts/lib-failed-agent-stderr-tail.sh:156-184
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] resolve_collector_stderr_tail_file only checks launch-stderr on the final REVIEWER_FILE path, not on earlier waterfall phase paths walked for .stderr-tail. Phase-1 launcher failure writes slot.txt.launch-stderr but terminal REVIEWER_FILE is slot-phase3.txt; collector finds no phase-3 tail and never reads base launch-stderr, so the #3202 launcher failure stays invisible in chat. While iterating collector_stderr_tail_candidates, also render from each ${_candidate}.launch-stderr before giving up (or add explicit phase-1 launch-stderr to the candidate list).
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: scripts/run-external-agent.sh:263-270
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] TIMED_OUT selects stderr source after appending wrapper text to .diag, unlike FAILED and unlike plan FINDING_6. Empty sidecar and output at timeout: tail is only the generic timeout line from .diag, not agent stderr. Select _stderr_src before appending the timeout line to .diag, matching the FAILED branch.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: skills/review/scripts/collect-findings.sh:87-148
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] replay_collector_failed_stderr_tails omits collector signature dedup. Collector stderr empty but identical .stderr-tail sidecars on many slots: replay emits N full fences instead of one tail plus suppression lines. Share the §3.8 signature map in replay, or ensure collector stderr always captures §3.8 output when sidecars exist.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: scripts/lib-failed-agent-stderr-tail.sh:203-224
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Aggressive digit normalization in failed_agent_stderr_signature can collapse distinct failures. Two errors differing only by line numbers hash equal; second failure is over-suppressed. Tighten normalization if production shows false dedup; document limitation in operator docs.
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: scripts/test-lib-failed-agent-stderr-tail.sh:43-49
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Non-numeric LARCH_FAILED_AGENT_STDERR_TAIL_LINES fallback to 30 is implemented but not tested per plan edge cases. Setting LARCH_FAILED_AGENT_STDERR_TAIL_LINES=abc could regress to empty/disabled tail behavior without CI catching it. Add harness cases for abc/30abc asserting failed_agent_stderr_tail_lines prints 30 and render still tails 30 lines.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: scripts/test-launch-claude-subprocess.sh:51-53
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan requires .stderr-tail before .done on failure; test only checks both files exist post-run. Reordering writes so .done precedes .stderr-tail could break collector handoff while tests stay green. Assert ordering via stat timestamps or a stub that errors if .done exists before .stderr-tail is written.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: scripts/test-launch-claude-review.sh:401-356
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Plan acceptance requires preserved full subprocess stderr re-emit for dispatch-code-voters; new tests cover fence/sidecar only. Removing _larch_emit_redacted_subprocess_stderr while keeping bounded fence could break voter execution-issues warnings undetected. Assert redacted full-line subprocess stderr on FD 2 in addition to the fenced tail block.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: skills/review/scripts/collect-findings.sh:283-285
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] replay_collector_failed_stderr_tails is untested when captured collector stderr is empty. Empty capture plus failed results and existing .stderr-tail sidecars might fail to reach chat if replay regresses. Add test-collect-findings case: sidecars present, LARCH_FAILED_AGENT_STDERR_TAIL_LINES=0 on collector, assert wrapper stderr still shows tails.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: scripts/test-dispatch-with-waterfall.sh:2848-2849
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Waterfall test only asserts .launch-stderr file exists on phase-3 hard fail. Empty or wrong sidecar could slip through; launcher root cause might stay invisible until production. Assert non-empty launch-stderr content from stub or wire a minimal waterfall-to-collector surfacing check.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: skills/review/scripts/test-collect-findings.sh:91-94
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Test comments refer to tee but implementation uses stderr file capture and replay. Future edits may reintroduce wrong tee pattern believing tests require it. Align comments and failure messages with capture-and-replay behavior in collect-findings.sh.
- **Suggested revision**: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] risk-integration: skills/design/scripts/test-plan-review-loop.sh:3901
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Design plan-review-loop captures collector stderr but lacks behavioral tail-surfacing test. #3119-style design panel failures might not reach chat if tee/FD routing regresses despite collector unit tests passing. Add plan-review-loop case with failing panel stubs asserting stderr tails on FD 2/4 when collect succeeds.
- **Suggested revision**: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] risk-integration: hooks/hooks.json (branch)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Unrelated hook-anti-read-poll expansion ships in the same branch as #3202. Increases CI time and coupling; failures may be attributed to the wrong feature during triage. Split or clearly label hook work; ensure hook harness stays in the same shard as related changes.
- **Suggested revision**: Address the concern above.

### FINDING_19: security: scripts/launch-claude-review.sh:199-206
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] On failure the launcher still re-emits the full redacted subprocess stderr file without line/byte bounds in addition to the new bounded stderr-tail fence. A single Claude validation failure can flood the orchestrator transcript with far more tool output than the 30-line/5 KiB tail contract while still being redacted-only. Cap or disable the legacy full stderr re-emit; rely on write_failed_agent_stderr_tail / collector §3.8 for bounded diagnostics.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: skills/review/scripts/collect-findings.sh:283-290
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] replay_collector_failed_stderr_tails runs when collector stderr is empty and does not apply failed_agent_stderr_signature dedup. Quiet-session routing can drop §3.8 stderr capture; replay then prints one full tail per failed slot even when root causes match multiplying redacted content in chat. Share collector dedup logic in replay or tee collect-agent-results stderr so §3.8 output is always captured once.
- **Suggested revision**: Address the concern above.

### FINDING_21: security: SECURITY.md:256
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Publishable *.stderr-tail artifacts live under the larch-logs gitleaks path allowlist after dual redaction at publish. A novel secret shape missed by redact-secrets.sh can be committed to a public fork without gitleaks catching it. Keep documented ops discipline; consider targeted gitleaks rules or a harness scan for stderr-tail artifacts outside allowlisted fixtures.
- **Suggested revision**: Address the concern above.

### FINDING_22: security: scripts/compose-collector-failure-log.sh:57-74
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Failure logs cat .stderr-tail sidecars directly while .launch-stderr uses render_failed_agent_stderr_tail. A corrupted or stale unredacted .stderr-tail sidecar could reach execution-issues before append-tool-failure --redact. Dump .stderr-tail through render_failed_agent_stderr_tail like launch-stderr.
- **Suggested revision**: Address the concern above.

### FINDING_23: security: scripts/lib-failed-agent-stderr-tail.sh:105-106
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Redaction spool temps use default mktemp permissions without chmod 600. On a shared TMPDIR host another user could read spool bytes between tail/redact and rm. chmod 600 immediately after each mktemp for spool and launch-stderr render temps.
- **Suggested revision**: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] security: scripts/compose-collector-failure-log.sh:66
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Pre-existing raw cat of .diag in failure bundles can include unredacted DIAG_DETAIL snippets. Unrelated to new stderr-tail sections but still leaks agent output snippets into review failure artifacts. Redact or render .diag through the same pipeline as launch-stderr when composing failure logs.
- **Suggested revision**: Address the concern above.

### FINDING_25: correctness: scripts/lib-failed-agent-stderr-tail.sh:168-182
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Ancestor phase .stderr-tail is chosen before the current slot .launch-stderr. Phase 2 codex leaves foo-phase2.txt.stderr-tail; phase 3 Claude launcher fails with only foo-phase3.txt.launch-stderr (e.g. timeout cap). Collector/chat show the phase-2 codex tail, not the launcher error. Check ${reviewer_file}.launch-stderr (render on demand) before collector_stderr_tail_candidates ancestor .stderr-tail lookup; add a harness with competing phase2 tail and phase3 launch-stderr.
- **Suggested revision**: Address the concern above.

### FINDING_26: architecture: skills/review/scripts/collect-findings.sh:87-149
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] replay_collector_failed_stderr_tails has no signature dedup. When collector_stderr stays empty but .stderr-tail sidecars exist, /review replays one full fenced block per failed slot (no ↩ suppression). Reuse failed_agent_stderr_signature and the collector sig-map logic in replay, or require collector stderr capture so replay is rare.
- **Suggested revision**: Address the concern above.

### FINDING_27: correctness: scripts/lib-failed-agent-stderr-tail.sh:193-207
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Phase stem fallback can surface an older phase tail for a new phase failure. Phase 3 fails with empty sidecar; phase 2 still has .stderr-tail from an earlier failure. Operator sees phase-2 root cause for a phase-3 slot. Narrow fallback conditions or rm ancestor .stderr-tail when advancing phases; document limits in lib-failed-agent-stderr-tail.md.
- **Suggested revision**: Address the concern above.

### FINDING_28: correctness: scripts/lib-failed-agent-stderr-tail.sh:203-224
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Heuristic dedup signature over-normalizes digits and paths. Distinct API/port failures hash equal; slots after the first emit only the suppression line and hide differing stderr. Reduce normalization aggressiveness or dedup on exact redacted tail bytes only.
- **Suggested revision**: Address the concern above.

### FINDING_29: correctness: scripts/collect-agent-results.sh:1470-1472
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] cap_hit results skip §3.8 stderr-tail emission. A cap-hit reviewer still has diagnostic stderr in sidecars; operator never sees it in chat or dedup pass. Emit tails for cap_hit unless product semantics require silence.
- **Suggested revision**: Address the concern above.

### FINDING_30: security: scripts/lib-failed-agent-stderr-tail.sh:964-967
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Redaction can empty the spool; render/write fail quietly. Stderr is only tokens; after redact the spool is empty, .stderr-tail is removed, chat gets at most WARN unavailable—same unrecoverable state as #3119 for secret-heavy stderr. Surface a bounded placeholder when source was non-empty but render returned empty.
- **Suggested revision**: Address the concern above.

### FINDING_31: correctness: scripts/lib-failed-agent-stderr-tail.sh:156-183
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Collector launch-stderr resolution omits ancestor-phase files required by the plan. Final REVIEWER_FILE is a later phase stem with no .launch-stderr while an earlier phase's .launch-stderr holds the launcher validation error; chat and dedup never surface it. Walk phase stems for the first non-empty *.launch-stderr (mirror .stderr-tail fallback) or amend the plan if primary-stem-only is intended.
- **Suggested revision**: Address the concern above.

### FINDING_32: correctness: scripts/test-launch-claude-subprocess.sh:51-53
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Harness does not assert .stderr-tail is written before .done. A future reorder could break the collector handoff race while tests still pass. Assert mtime ordering or document-order in the failure-path case.
- **Suggested revision**: Address the concern above.

### FINDING_33: architecture: scripts/lib-failed-agent-stderr-tail.sh:12-13
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Lib no longer matches plan's dependency-free / single-raw-&gt;2 invariant. Plan-level quiet-init guarantees rely on caller discipline and agent-lint exclusions rather than structure. Update plan/docs to lib-quiet coupling or split raw emitters from the sourced lib.
- **Suggested revision**: Address the concern above.

### FINDING_34: correctness: skills/review/scripts/collect-findings.sh:283-284
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Replay fallback does not apply collector signature dedup. If collector stderr were empty with multiple identical .stderr-tail sidecars, /review could emit duplicate fences. Reuse dedup in replay or tee collector stderr live per FINDING_3.
- **Suggested revision**: Address the concern above.

### FINDING_35: **code-quality** `scripts/collect-agent-results.sh:1434-1447`, `scripts/lib-failed-agent-stderr-tail.sh:186-196`, `skills/review/scripts/collect-findings.sh:74-85` — §3.8 and the `/review` replay path reimplement the same fenced tail loop locally (`_emit_collector_stderr_tail_file`, `_write_failed_stderr_tail_block`) instead of calling a single lib helper, while `scripts/lib-failed-agent-stderr-tail.md:30` claims the collector emits via shared lib machinery. The lib only exposes `emit_failed_agent_stderr_tail_larch_err` for `${output_file}.stderr-tail`, not arbitrary tail paths (retry/NS-retry/phase/`larch-launch-stderr-tail.*`), so the duplication is understandable but brittle: fence text, sanitization, and quiet routing can drift across three sites. `scripts/test-run-external-agent.sh:451-454` even asserts the collector-local symbol exists, locking in the fork. **Suggested fix:** Add `emit_failed_agent_stderr_tail_file_larch_err <tail_file>` (and optionally a dedup-aware batch helper) to `lib-failed-agent-stderr-tail.sh`, call it from §3.8 and from `replay_collector_failed_stderr_tails`, delete the parallel emitters, and point the regression grep at the lib function name.
- **Reviewer**: dyn-fd-contract-output.txt
- **Concern**: - **code-quality** `scripts/collect-agent-results.sh:1434-1447`, `scripts/lib-failed-agent-stderr-tail.sh:186-196`, `skills/review/scripts/collect-findings.sh:74-85` — §3.8 and the `/review` replay path reimplement the same fenced tail loop locally (`_emit_collector_stderr_tail_file`, `_write_failed_stderr_tail_block`) instead of calling a single lib helper, while `scripts/lib-failed-agent-stderr-tail.md:30` claims the collector emits via shared lib machinery. The lib only exposes `emit_failed_agent_stderr_tail_larch_err` for `${output_file}.stderr-tail`, not arbitrary tail paths (retry/NS-retry/phase/`larch-launch-stderr-tail.*`), so the duplication is understandable but brittle: fence text, sanitization, and quiet routing can drift across three sites. `scripts/test-run-external-agent.sh:451-454` even asserts the collector-local symbol exists, locking in the fork. **Suggested fix:** Add `emit_failed_agent_stderr_tail_file_larch_err <tail_file>` (and optionally a dedup-aware batch helper) to `lib-failed-agent-stderr-tail.sh`, call it from §3.8 and from `replay_collector_failed_stderr_tails`, delete the parallel emitters, and point the regression grep at the lib function name.
- **Suggested revision**: Address the concern above.

### FINDING_36: **code-quality** `scripts/lib-failed-agent-stderr-tail.sh:4-5,15-40,227-236` — The header and contract still describe a “no raw `>&2` except `emit_failed_agent_stderr_tail_raw`” invariant, but the library now sources `lib-quiet.sh` and contains additional raw-`>&2` fallbacks in `_failed_agent_stderr_tail_warn_unavailable` and `_emit_failed_agent_stderr_tail_line`, plus `emit_failed_agent_stderr_tail_file_raw`. S041 only scans each file for post-`larch_quiet_init` writes, so this is not an active lint break today, but it weakens the stated quiet-init safety story and invites a future quiet caller to invoke `emit_failed_agent_stderr_tail_file_raw` and route fences into the quiet log instead of chat. **Suggested fix:** Align the header/contract with reality (document `larch_err` as the quiet-safe path, `emit_failed_agent_stderr_tail_file_raw` as non-quiet-only), and either move the raw emitter to `run-external-agent.sh` or add a comment/assertion that quiet-init callers must never call the raw variants.
- **Reviewer**: dyn-fd-contract-output.txt
- **Concern**: - **code-quality** `scripts/lib-failed-agent-stderr-tail.sh:4-5,15-40,227-236` — The header and contract still describe a “no raw `>&2` except `emit_failed_agent_stderr_tail_raw`” invariant, but the library now sources `lib-quiet.sh` and contains additional raw-`>&2` fallbacks in `_failed_agent_stderr_tail_warn_unavailable` and `_emit_failed_agent_stderr_tail_line`, plus `emit_failed_agent_stderr_tail_file_raw`. S041 only scans each file for post-`larch_quiet_init` writes, so this is not an active lint break today, but it weakens the stated quiet-init safety story and invites a future quiet caller to invoke `emit_failed_agent_stderr_tail_file_raw` and route fences into the quiet log instead of chat. **Suggested fix:** Align the header/contract with reality (document `larch_err` as the quiet-safe path, `emit_failed_agent_stderr_tail_file_raw` as non-quiet-only), and either move the raw emitter to `run-external-agent.sh` or add a comment/assertion that quiet-init callers must never call the raw variants.
- **Suggested revision**: Address the concern above.

### FINDING_37: [OUT_OF_SCOPE] **Stdout `KEY=value` contract:** §3.8 runs after all `RESULTS[]` mutations and before `# --- 4. Emit structured results ---`; it only uses `larch_err` / a sig-map temp file, not `emit`/`printf` to stdout. The collector subshell in `collect-findings.sh` keeps stdout (`> "$collector_results_file"`) separate from stderr (`2>"$collector_stderr"`). Harness cases in `scripts/test-collect-agent-results.sh` (dedup/distinct/phase fallback) assert stdout stays free of tail bodies. No stdout-corruption defect found for the scoped invariants.
- **Reviewer**: dyn-fd-contract-output.txt
- **Concern**: - **Stdout `KEY=value` contract:** §3.8 runs after all `RESULTS[]` mutations and before `# --- 4. Emit structured results ---`; it only uses `larch_err` / a sig-map temp file, not `emit`/`printf` to stdout. The collector subshell in `collect-findings.sh` keeps stdout (`> "$collector_results_file"`) separate from stderr (`2>"$collector_stderr"`). Harness cases in `scripts/test-collect-agent-results.sh` (dedup/distinct/phase fallback) assert stdout stays free of tail bodies. No stdout-corruption defect found for the scoped invariants.
- **Suggested revision**: Address the concern above.

### FINDING_38: [OUT_OF_SCOPE] **`compose-collector-failure-log.sh`:** `_redacted_launch_stderr_body` uses `render_failed_agent_stderr_tail` to the composed log file only; callers redirect script stdout (`collect-findings.sh:233-257`, `plan-review-loop.sh:802-805`). No collector stdout interaction.
- **Reviewer**: dyn-fd-contract-output.txt
- **Concern**: - **`compose-collector-failure-log.sh`:** `_redacted_launch_stderr_body` uses `render_failed_agent_stderr_tail` to the composed log file only; callers redirect script stdout (`collect-findings.sh:233-257`, `plan-review-loop.sh:802-805`). No collector stdout interaction.
- **Suggested revision**: Address the concern above.

### FINDING_39: [OUT_OF_SCOPE] **`collect-findings.sh` replay:** When `collector_stderr` is empty and `collector_rc=0`, `replay_collector_failed_stderr_tails` re-resolves tails and prints via `_write_failed_stderr_tail_block` to FD 2/4 without the collector’s signature dedup; this is latent (normally §3.8 populates `collector_stderr` first) but worth knowing if replay ever becomes the primary path.
- **Reviewer**: dyn-fd-contract-output.txt
- **Concern**: - **`collect-findings.sh` replay:** When `collector_stderr` is empty and `collector_rc=0`, `replay_collector_failed_stderr_tails` re-resolves tails and prints via `_write_failed_stderr_tail_block` to FD 2/4 without the collector’s signature dedup; this is latent (normally §3.8 populates `collector_stderr` first) but worth knowing if replay ever becomes the primary path.
- **Suggested revision**: Address the concern above.

### FINDING_40: **security** `scripts/collect-agent-results.sh:170-172,1434-1446` — `resolve_collector_stderr_tail_file` prefers an existing `${candidate}.stderr-tail` and §3.8 `_emit_collector_stderr_tail_file` streams that file to FD 2 with only `sanitize_diagnostic_line` (control-character stripping), not `redact-secrets.sh` or `redact-tmpdir-paths.sh`. Production writers use `write_failed_agent_stderr_tail` (dual-redacted at write time), but any pre-existing sidecar beside reviewer outputs is treated as chat-ready; `skills/review/scripts/test-collect-findings.sh:112-118` plants unredacted tails and expects them verbatim on FD 2, so raw subprocess or tool output placed in `.stderr-tail` bypasses the #3202 redaction pipeline. **Suggested fix:** At emit time, never trust `.stderr-tail` bytes; re-run `render_failed_agent_stderr_tail` from the authoritative source (`.sidecar`, `${OUTPUT}.stderr`, or `.launch-stderr`) or pipe the sidecar through both redactors before `larch_err`.
- **Reviewer**: dyn-redaction-coverage-output.txt
- **Concern**: - **security** `scripts/collect-agent-results.sh:170-172,1434-1446` — `resolve_collector_stderr_tail_file` prefers an existing `${candidate}.stderr-tail` and §3.8 `_emit_collector_stderr_tail_file` streams that file to FD 2 with only `sanitize_diagnostic_line` (control-character stripping), not `redact-secrets.sh` or `redact-tmpdir-paths.sh`. Production writers use `write_failed_agent_stderr_tail` (dual-redacted at write time), but any pre-existing sidecar beside reviewer outputs is treated as chat-ready; `skills/review/scripts/test-collect-findings.sh:112-118` plants unredacted tails and expects them verbatim on FD 2, so raw subprocess or tool output placed in `.stderr-tail` bypasses the #3202 redaction pipeline. **Suggested fix:** At emit time, never trust `.stderr-tail` bytes; re-run `render_failed_agent_stderr_tail` from the authoritative source (`.sidecar`, `${OUTPUT}.stderr`, or `.launch-stderr`) or pipe the sidecar through both redactors before `larch_err`.
- **Suggested revision**: Address the concern above.

### FINDING_41: **security** `scripts/compose-collector-failure-log.sh:57-74` — `dump_section` applies `_redacted_launch_stderr_body` (via `render_failed_agent_stderr_tail`) for `*.launch-stderr`, but uses raw `cat` for `*.stderr-tail` while still embedding `${REVIEWER_FILE}.diag` unredacted. Composed output is appended to `execution-issues.md` through `append-tool-failure.sh --redact`, which runs only `redact-secrets.sh`, not `redact-tmpdir-paths.sh`, so tmpdir/session paths in a trusted-but-wrong `.stderr-tail` or `.diag` can reach durable operator logs without the dual pipeline used at capture. **Suggested fix:** Route `.stderr-tail` through `render_failed_agent_stderr_tail` (or an equivalent read-time dual-redact helper) in `dump_section`, matching the `.launch-stderr` branch.
- **Reviewer**: dyn-redaction-coverage-output.txt
- **Concern**: - **security** `scripts/compose-collector-failure-log.sh:57-74` — `dump_section` applies `_redacted_launch_stderr_body` (via `render_failed_agent_stderr_tail`) for `*.launch-stderr`, but uses raw `cat` for `*.stderr-tail` while still embedding `${REVIEWER_FILE}.diag` unredacted. Composed output is appended to `execution-issues.md` through `append-tool-failure.sh --redact`, which runs only `redact-secrets.sh`, not `redact-tmpdir-paths.sh`, so tmpdir/session paths in a trusted-but-wrong `.stderr-tail` or `.diag` can reach durable operator logs without the dual pipeline used at capture. **Suggested fix:** Route `.stderr-tail` through `render_failed_agent_stderr_tail` (or an equivalent read-time dual-redact helper) in `dump_section`, matching the `.launch-stderr` branch.
- **Suggested revision**: Address the concern above.

### FINDING_42: **security** `skills/review/scripts/collect-findings.sh:143-147,286-290` — On successful collect (`collector_rc=0`), `replay_collector_failed_stderr_tails` and the subsequent replay of `$collector_stderr` copy tail blocks to FD 2 with no `redact-secrets.sh` / `redact-tmpdir-paths.sh` pass (FINDING_3 tee path). That inherits the `.stderr-tail` trust model above; a collector failure path at `298-299` applies secrets redaction only, not tmpdir redaction, on the combined log. **Suggested fix:** Pipe all collector stderr replay (live tee and `replay_collector_failed_stderr_tails` output) through `redact-tmpdir-paths.sh | redact-secrets.sh` before `printf`/`larch_err`, or only replay tails produced by a read-time `render_failed_agent_stderr_tail` call.
- **Reviewer**: dyn-redaction-coverage-output.txt
- **Concern**: - **security** `skills/review/scripts/collect-findings.sh:143-147,286-290` — On successful collect (`collector_rc=0`), `replay_collector_failed_stderr_tails` and the subsequent replay of `$collector_stderr` copy tail blocks to FD 2 with no `redact-secrets.sh` / `redact-tmpdir-paths.sh` pass (FINDING_3 tee path). That inherits the `.stderr-tail` trust model above; a collector failure path at `298-299` applies secrets redaction only, not tmpdir redaction, on the combined log. **Suggested fix:** Pipe all collector stderr replay (live tee and `replay_collector_failed_stderr_tails` output) through `redact-tmpdir-paths.sh | redact-secrets.sh` before `printf`/`larch_err`, or only replay tails produced by a read-time `render_failed_agent_stderr_tail` call.
- **Suggested revision**: Address the concern above.

### FINDING_43: **security** `scripts/launch-claude-review.sh:186-203` — On non-zero exit, `_larch_emit_redacted_subprocess_stderr` replays the full captured subprocess stderr file to chat (unbounded) and can run with only `redact-secrets.sh` when `redact-tmpdir-paths.sh` is absent (`pipeline="$redact"`), while the new bounded tail path in `lib-failed-agent-stderr-tail.sh:103` requires both scripts. The same failure also calls `emit_failed_agent_stderr_tail_larch_err`, so operators may see duplicate diagnostics with inconsistent redaction strength. **Suggested fix:** Align subprocess replay with the bounded tail contract (use `render_failed_agent_stderr_tail` / drop full-file replay when the sidecar exists), and fail closed unless both redactors are executable—mirror `render_failed_agent_stderr_tail`’s guard.
- **Reviewer**: dyn-redaction-coverage-output.txt
- **Concern**: - **security** `scripts/launch-claude-review.sh:186-203` — On non-zero exit, `_larch_emit_redacted_subprocess_stderr` replays the full captured subprocess stderr file to chat (unbounded) and can run with only `redact-secrets.sh` when `redact-tmpdir-paths.sh` is absent (`pipeline="$redact"`), while the new bounded tail path in `lib-failed-agent-stderr-tail.sh:103` requires both scripts. The same failure also calls `emit_failed_agent_stderr_tail_larch_err`, so operators may see duplicate diagnostics with inconsistent redaction strength. **Suggested fix:** Align subprocess replay with the bounded tail contract (use `render_failed_agent_stderr_tail` / drop full-file replay when the sidecar exists), and fail closed unless both redactors are executable—mirror `render_failed_agent_stderr_tail`’s guard.
- **Suggested revision**: Address the concern above.

### FINDING_44: [OUT_OF_SCOPE] **Verified OK:** `dispatch-with-waterfall.sh:269,284` writes raw bytes only to `${output}.launch-stderr` on disk; every chat/log path checked (`resolve_collector_stderr_tail_file` at `lib-failed-agent-stderr-tail.sh:175-177`, `compose-collector-failure-log.sh:57-58`, `render_failed_agent_stderr_tail` at `lib-failed-agent-stderr-tail.sh:108`) runs `tail | redact-tmpdir-paths.sh | redact-secrets.sh` with spool-then-`head -c` (pipefail-safe at `107-115`). `design-log-publish.sh:302-308` dual-redacts all non-excluded staged files including publishable `*.stderr-tail`; `*.launch-stderr` is not excluded but is redacted on publish, not copied raw. `SECURITY.md:256` publish-time claim matches `design_publish_stage_file`.
- **Reviewer**: dyn-redaction-coverage-output.txt
- **Concern**: - **Verified OK:** `dispatch-with-waterfall.sh:269,284` writes raw bytes only to `${output}.launch-stderr` on disk; every chat/log path checked (`resolve_collector_stderr_tail_file` at `lib-failed-agent-stderr-tail.sh:175-177`, `compose-collector-failure-log.sh:57-58`, `render_failed_agent_stderr_tail` at `lib-failed-agent-stderr-tail.sh:108`) runs `tail | redact-tmpdir-paths.sh | redact-secrets.sh` with spool-then-`head -c` (pipefail-safe at `107-115`). `design-log-publish.sh:302-308` dual-redacts all non-excluded staged files including publishable `*.stderr-tail`; `*.launch-stderr` is not excluded but is redacted on publish, not copied raw. `SECURITY.md:256` publish-time claim matches `design_publish_stage_file`.
- **Suggested revision**: Address the concern above.

### FINDING_45: [OUT_OF_SCOPE] Raw `*.sidecar` / `*.diag` remain excluded from publish (`design-log-publish.sh:259`) and are outside the new tail feature; `.diag` is still `cat`’d unredacted into composed failure logs (pre-existing pattern).
- **Reviewer**: dyn-redaction-coverage-output.txt
- **Concern**: - Raw `*.sidecar` / `*.diag` remain excluded from publish (`design-log-publish.sh:259`) and are outside the new tail feature; `.diag` is still `cat`’d unredacted into composed failure logs (pre-existing pattern).
- **Suggested revision**: Address the concern above.

### FINDING_46: [OUT_OF_SCOPE] `gitleaks` does not scan `larch-logs/`; committed `*.stderr-tail` artifacts rely on publish-time redaction and operator hygiene, as documented in `SECURITY.md`.
- **Reviewer**: dyn-redaction-coverage-output.txt
- **Concern**: - `gitleaks` does not scan `larch-logs/`; committed `*.stderr-tail` artifacts rely on publish-time redaction and operator hygiene, as documented in `SECURITY.md`.
- **Suggested revision**: Address the concern above.

### FINDING_47: **risk-integration** `scripts/hook-anti-read-poll.sh:16-46,316-323` — Widening `hooks/hooks.json` to `Read|Bash` means every Bash PostToolUse runs this hook, but non-polling Bash does not exit before expensive work: after the `tool_name` gate it still performs multiple full-payload `jq` extractions (`cwd`, `session_id`/`conversation_id`), two `cksum` passes, `mkdir`/`chmod` on `${TMPDIR}/larch-read-poll`, then `jq` for `tool_input.command` and the full `extract_bash_task_output_poll_token` path (sed normalization, line loop, segment split, grep read-verb checks). A call like `ls` (harness `=== non-poll Bash is ignored ===`) still pays that cost; only state-file read/write is skipped when no token matches. With Bash far more frequent than Read, this materially increases per-invocation hook latency and the chance of brushing the 5s `hooks/hooks.json` timeout on large multiline commands, without a cheap prefilter (e.g. exit 0 when `command` lacks `tasks/` + `.output`). **Suggested fix:** Add a fast reject immediately after parsing `tool_input.command` (case-insensitive `*tasks/*` + `*.output*` substring) before session hashing and `state_dir` setup; defer `mkdir` and TSV I/O until a token is found. Optionally move `cwd`/session `jq` below that gate for the Bash branch only.
- **Reviewer**: dyn-hook-blast-radius-output.txt
- **Concern**: - **risk-integration** `scripts/hook-anti-read-poll.sh:16-46,316-323` — Widening `hooks/hooks.json` to `Read|Bash` means every Bash PostToolUse runs this hook, but non-polling Bash does not exit before expensive work: after the `tool_name` gate it still performs multiple full-payload `jq` extractions (`cwd`, `session_id`/`conversation_id`), two `cksum` passes, `mkdir`/`chmod` on `${TMPDIR}/larch-read-poll`, then `jq` for `tool_input.command` and the full `extract_bash_task_output_poll_token` path (sed normalization, line loop, segment split, grep read-verb checks). A call like `ls` (harness `=== non-poll Bash is ignored ===`) still pays that cost; only state-file read/write is skipped when no token matches. With Bash far more frequent than Read, this materially increases per-invocation hook latency and the chance of brushing the 5s `hooks/hooks.json` timeout on large multiline commands, without a cheap prefilter (e.g. exit 0 when `command` lacks `tasks/` + `.output`). **Suggested fix:** Add a fast reject immediately after parsing `tool_input.command` (case-insensitive `*tasks/*` + `*.output*` substring) before session hashing and `state_dir` setup; defer `mkdir` and TSV I/O until a token is found. Optionally move `cwd`/session `jq` below that gate for the Bash branch only.
- **Suggested revision**: Address the concern above.

### FINDING_48: **risk-integration** `scripts/hook-anti-read-poll.sh:24-34,208-214` — Task-output counters key on `session_hash` derived from `session_id` → `conversation_id` → `nosession` (or `nosession-${HOOK_ANTI_READ_POLL_DISCRIMINATOR}`). When both IDs are absent—the default in most harness payloads via `mk_bash_payload` / `mk_payload` without a fifth argument—all concurrent callers share one `state-taskout-<nosession-hash>-<cwd_hash>-<task_id>.tsv` bucket for 600s. That can produce spurious “Task-output poll detected” reminders when unrelated sessions on the same machine/repo cwd poll different tasks with the same normalized id, or when parallel offline runs share `TMPDIR` and cwd. The harness only isolates via `HOOK_ANTI_READ_POLL_DISCRIMINATOR` in the dedicated `=== nosession discriminators ===` case; routine tests do not set it. **Suggested fix:** Prefer a platform-stable discriminator when metadata is missing (e.g. hook-provided process/session token if Claude Code exposes one), or hash additional fields (`transcript_path`, `hook_event_id`, parent PID from env). Document that production relies on `session_id`/`conversation_id` always being present; add a harness-wide default discriminator (or require `session_id` in all test payloads) so parallel `make` shards cannot cross-talk.
- **Reviewer**: dyn-hook-blast-radius-output.txt
- **Concern**: - **risk-integration** `scripts/hook-anti-read-poll.sh:24-34,208-214` — Task-output counters key on `session_hash` derived from `session_id` → `conversation_id` → `nosession` (or `nosession-${HOOK_ANTI_READ_POLL_DISCRIMINATOR}`). When both IDs are absent—the default in most harness payloads via `mk_bash_payload` / `mk_payload` without a fifth argument—all concurrent callers share one `state-taskout-<nosession-hash>-<cwd_hash>-<task_id>.tsv` bucket for 600s. That can produce spurious “Task-output poll detected” reminders when unrelated sessions on the same machine/repo cwd poll different tasks with the same normalized id, or when parallel offline runs share `TMPDIR` and cwd. The harness only isolates via `HOOK_ANTI_READ_POLL_DISCRIMINATOR` in the dedicated `=== nosession discriminators ===` case; routine tests do not set it. **Suggested fix:** Prefer a platform-stable discriminator when metadata is missing (e.g. hook-provided process/session token if Claude Code exposes one), or hash additional fields (`transcript_path`, `hook_event_id`, parent PID from env). Document that production relies on `session_id`/`conversation_id` always being present; add a harness-wide default discriminator (or require `session_id` in all test payloads) so parallel `make` shards cannot cross-talk.
- **Suggested revision**: Address the concern above.

### FINDING_49: [OUT_OF_SCOPE] **Fail-open (scout item 4):** Parse/`jq` failures consistently `exit 0` (`12-13`, `15`, `301-302`, `317-318`, `326`); `emit_reminder` uses `|| true`; no `set -e`. Looks correct.
- **Reviewer**: dyn-hook-blast-radius-output.txt
- **Concern**: - **Fail-open (scout item 4):** Parse/`jq` failures consistently `exit 0` (`12-13`, `15`, `301-302`, `317-318`, `326`); `emit_reminder` uses `|| true`; no `set -e`. Looks correct.
- **Suggested revision**: Address the concern above.

### FINDING_50: [OUT_OF_SCOPE] **rm/ls/cp false positives (scout item 2):** `bash_segment_task_output_poll_token` requires `bash_has_read_verb` (`66-76`, `101-108`); non-read commands mentioning `tasks/<id>.output` should not count. Harness covers `ls`, `echo cat …`, `jq '…cat…'`, assignment decoys; no in-scope defect found for the cited rm/ls/cp case.
- **Reviewer**: dyn-hook-blast-radius-output.txt
- **Concern**: - **rm/ls/cp false positives (scout item 2):** `bash_segment_task_output_poll_token` requires `bash_has_read_verb` (`66-76`, `101-108`); non-read commands mentioning `tasks/<id>.output` should not count. Harness covers `ls`, `echo cat …`, `jq '…cat…'`, assignment decoys; no in-scope defect found for the cited rm/ls/cp case.
- **Suggested revision**: Address the concern above.

### FINDING_51: [OUT_OF_SCOPE] **TSV concurrency:** `handle_task_output_poll` / `handle_generic_read_poll` use read-modify-write without locking (`216-245`, `263-291`); overlapping PostToolUse invocations could under-count (miss reminder) rather than block tools—accepted heuristic risk, not introduced solely by the matcher change.
- **Reviewer**: dyn-hook-blast-radius-output.txt
- **Concern**: - **TSV concurrency:** `handle_task_output_poll` / `handle_generic_read_poll` use read-modify-write without locking (`216-245`, `263-291`); overlapping PostToolUse invocations could under-count (miss reminder) rather than block tools—accepted heuristic risk, not introduced solely by the matcher change.
- **Suggested revision**: Address the concern above.

### FINDING_52: [OUT_OF_SCOPE] **Documented parsing gaps:** `hook-anti-read-poll.md` and inline comments note `;`/`&&` splitting inside quotes and unexpanded `VAR=…/tasks/id.output` then `cat "$VAR"` as known limitations; tests pin several false-positive guards.
- **Reviewer**: dyn-hook-blast-radius-output.txt
- **Concern**: - **Documented parsing gaps:** `hook-anti-read-poll.md` and inline comments note `;`/`&&` splitting inside quotes and unexpanded `VAR=…/tasks/id.output` then `cat "$VAR"` as known limitations; tests pin several false-positive guards.
- **Suggested revision**: Address the concern above.

### FINDING_53: [OUT_OF_SCOPE] **#3202 stderr-tail work** (`lib-failed-agent-stderr-tail.sh`, collector dedup, Claude timeout clamp) is separate from hook blast-radius; not audited here beyond coexisting on the branch.
- **Reviewer**: dyn-hook-blast-radius-output.txt
- **Concern**: - **#3202 stderr-tail work** (`lib-failed-agent-stderr-tail.sh`, collector dedup, Claude timeout clamp) is separate from hook blast-radius; not audited here beyond coexisting on the branch.
- **Suggested revision**: Address the concern above.

