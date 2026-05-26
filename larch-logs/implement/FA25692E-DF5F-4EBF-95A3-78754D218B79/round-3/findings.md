### FINDING_1: code-quality: scripts/launch-review.sh:560-581
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Identical parse-KV-record blocks are copy-pasted across launch-review launch-codex-implement and launch-codex-ci despite all sourcing lib-codex-launcher-common.sh. A future fix updates cache_read mapping or fail-closed guards in one launcher only; CI records per-bucket tokens while review still writes aggregate-only rows. Add codex_launcher_record_usage_from_events to lib-codex-launcher-common.sh and call it from all three launchers with raw= and optional token-record path.
- **Suggested revision**: Address the concern above.

### FINDING_2: correctness: scripts/parse-codex-usage.sh:36-43
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] jq treats empty usage objects as present blocking top-level token field fallback. Codex emits {"usage":{},"input_tokens":N} (0.125 token_usage shape); parser counts the event but sums zero and fail-closes leaving no ledger row despite real usage. Require a non-null token field before accepting a usage object or include top-level input_tokens in the per-field coalesce when nested usage is empty.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/launch-review.sh:561-565
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] launch-review appends parse-codex-usage stderr to sidecar on failure but implement and CI swallow parse stderr. An implement run with a non-empty events file and schema mismatch shows no parse diagnostic in sidecar.log while review would surface it in the sidecar. Document asymmetry in launcher .md siblings or add optional append_errors_to sidecar parameter to a shared helper.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: scripts/parse-codex-usage.md:47-49
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Documented input_tokens coalesce paths omit .msg.input_tokens and .input_tokens fallbacks present in jq. A contributor aligns jq to the doc and breaks codex-msg-token-usage.jsonl / Codex-native top-level token fields. Update parse-codex-usage.md coalesce list to match scripts/parse-codex-usage.sh lines 41-43 exactly.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] code-quality: (branch)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Branch mixes #2813 Codex token capture with breadcrumb lib-larch-log rollout and larch-logs flush in one PR. Reviewers and bisect blame conflate unrelated regressions; revert of one feature risks reverting the other. Split into focused PRs when feasible.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] code-quality: scripts/parse-codex-usage.sh:47-49
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] jq failures are reported as no usage events. Operator sees no usage events for a corrupt JSONL file when jq actually crashed or hit a parse error. Distinguish jq exit/status from zero-usage fail-closed in stderr diagnostics.
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: scripts/parse-codex-usage.sh:66-72
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] cached>input validation uses aggregated sums only not per-event Stream with one bad line (cached>input) plus valid lines passes aggregate check and emits wrong INPUT/CACHED_INPUT while TOTAL may look plausible In jq reduce fail-closed when any event coalesced cached exceeds coalesced input before summing; keep aggregate guard as backstop
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: scripts/parse-codex-usage.sh:36-44
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Parser sums all usage-bearing JSON objects with no token_usage type filter If Codex emits per-turn usage plus a final token_usage summary totals are double-counted and costs overstated Verify real --json stream; filter or dedupe summary events; extend codex-events smoke fixture
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: scripts/test-launch-review.sh
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Harness for SIDECAR=/dev/null no-parse contract removed in 8aef0664 Future change could record Codex tokens when sidecar is /dev/null without test catching it Restore stub test asserting no ledger row when sidecar init fails to /dev/null
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] architecture: scripts/launch-review.sh:510
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] run-external progress lines append to events.jsonl Bloat or rare parse confusion if progress text ever looks like JSON Out of scope; optional tee filter later
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: scripts/test-render-run-summary-callsites.sh:11-19
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Callsite harnesses grep only --claude-input-tokens, not Codex per-bucket flags in render-final-summary.sh / write-final-report.sh. A refactor removes --codex-input-tokens/--codex-cached-input-tokens forwarding; launchers still record buckets but final-summary cost lines hit render-cost-line aggregate fallback and BLENDED_WARN returns. Require --codex-input-tokens and --codex-cached-input-tokens in callsite tests, or add fixture-driven final-summary cost test with non-zero BUCKETS_codex and assert no blended-rate stderr.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: scripts/test-launch-review.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] SIDECAR=/dev/null fail-closed branch from launch-review.sh is undocumented in tests. Unwritable sidecar regressions could write vendor rows or read stale events when sidecar is /dev/null. Add harness with unwritable .sidecar: assert no codex vendor row and no token parse on /dev/null events path.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: scripts/test-parse-codex-usage.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Nested type token_usage + .usage shape only exercised in test-token-vendor-scrapers smoke, not parser unit harness. Parser break for that shape passes make test-parse-codex-usage but fails later in scraper smoke. Add one JSONL fixture line matching launch-codex-implement stub shape to test-parse-codex-usage.sh.
- **Suggested revision**: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `scripts/lib-quiet.sh:176-181` (pre-existing) — EXIT-trap chaining uses `eval` on a captured trap body. Not introduced or amplified by this branch’s Codex work; noted only because `lib-quiet.sh` is touched for breadcrumb streaming. **Suggested fix:** (follow-up) replace `eval` with a direct trap restore pattern if trap injection ever becomes a concern.
- **Suggested revision**: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **risk-integration** `scripts/launch-review.sh` / `scripts/launch-codex-implement.sh` / `scripts/launch-codex-ci.sh` (documented contract) — Auth/transient classification is stderr-only after splitting Codex stdout to the events sidecar. This is intentional and tested; a future Codex CLI regression that routes auth/quota text only on stdout would weaken retry classification without exposing credentials. **Suggested fix:** monitor via launcher tests; tee non-JSON stdout lines into the sidecar only if Codex behavior changes (plan follow-up).
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: scripts/launch-codex-implement.sh:358 and scripts/launch-codex-ci.sh:230
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Implement and CI launchers discard parse-codex-usage.sh stderr while review appends diagnostics to the sidecar when events are non-empty. After a Codex CLI or schema change, events.jsonl is non-empty but parsing fails; /implement or CI records no vendor row, BLENDED_WARN does not fire, and sidecar logs give no parse failure hint—silent Codex under-reporting. Mirror launch-review.sh: capture helper stderr to a temp file and append to SIDECAR_LOG when _codex_usage is empty and CODEX_EVENTS is non-empty.
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: scripts/parse-codex-usage.sh:36-44
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Synthetic usage detection increments usage_count for usage shells with no numeric token fields. Stream of only {"usage":{}}-style events exits with "no usage events" despite usage-shaped objects, obscuring zero-total vs missing-usage failures. Only increment count when at least one token field is non-zero, or use distinct stderr messages for zero totals vs no objects.
- **Suggested revision**: Address the concern above.

### FINDING_18: architecture: scripts/launch-review.sh:572-579
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Launchers do not verify TOTAL equals INPUT+CACHED_INPUT+OUTPUT before writing ledger/token-record rows. Helper regression could write inconsistent buckets that propagate into token-report and token-cost without a launcher guard. After parsing KV lines, assert totals and skip record-vendor when the identity fails.
- **Suggested revision**: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] risk-integration: skills/review-and-fix/scripts/review-and-fix.sh:256-257
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Other Codex call sites still use combined 2>&1 and no JSONL usage capture. /review-and-fix or lint-fix Codex runs may still miss per-bucket telemetry or trigger BLENDED_WARN outside the three fixed launchers. Follow-up: apply the same --json events sidecar + parse-codex-usage.sh pattern to those invokers.
- **Suggested revision**: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] code-quality: scripts/launch-codex-ci.sh:254
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] launch-codex-ci.sh always exits 0 while exposing failure via LAUNCHER_EXIT KV. Callers checking only shell exit may treat failed Codex CI as success; unrelated to bucket capture but affects failure recovery. Pre-existing; consider aligning exit code with LAUNCHER_EXIT in a separate change.
- **Suggested revision**: Address the concern above.

### FINDING_21: architecture: scripts/parse-codex-usage.md:47-58
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Per-field coalesce docs omit .msg.* token paths that jq uses. Fixture codex-msg-token-usage.jsonl and 0.125 top-level token_usage events rely on .msg.input_tokens; doc-only edits could drop jq paths and fail smoke tests silently in CI. Document .msg.input_tokens / .msg.cached_input_tokens / .msg.output_tokens in the coalesce lists to match parse-codex-usage.sh:41-43.
- **Suggested revision**: Address the concern above.

### FINDING_22: architecture: scripts/launch-review.md:69-74
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan-required reference to parse-codex-usage.md is missing. Operators/contributors reading launch-review.md may not find the formal contract for KV output and fail-closed semantics. Add an explicit pointer to scripts/parse-codex-usage.md next to the parse-codex-usage.sh mention.
- **Suggested revision**: Address the concern above.

