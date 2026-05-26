### [rejected] FINDING_1

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_1: code-quality: scripts/launch-review.sh:560-581
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Identical parse-KV-record blocks are copy-pasted across launch-review launch-codex-implement and launch-codex-ci despite all sourcing lib-codex-launcher-common.sh. A future fix updates cache_read mapping or fail-closed guards in one launcher only; CI records per-bucket tokens while review still writes aggregate-only rows. Add codex_launcher_record_usage_from_events to lib-codex-launcher-common.sh and call it from all three launchers with raw= and optional token-record path.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_12: risk-integration: scripts/test-launch-review.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] SIDECAR=/dev/null fail-closed branch from launch-review.sh is undocumented in tests. Unwritable sidecar regressions could write vendor rows or read stale events when sidecar is /dev/null. Add harness with unwritable .sidecar: assert no codex vendor row and no token parse on /dev/null events path.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_16: risk-integration: scripts/launch-codex-implement.sh:358 and scripts/launch-codex-ci.sh:230
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Implement and CI launchers discard parse-codex-usage.sh stderr while review appends diagnostics to the sidecar when events are non-empty. After a Codex CLI or schema change, events.jsonl is non-empty but parsing fails; /implement or CI records no vendor row, BLENDED_WARN does not fire, and sidecar logs give no parse failure hint—silent Codex under-reporting. Mirror launch-review.sh: capture helper stderr to a temp file and append to SIDECAR_LOG when _codex_usage is empty and CODEX_EVENTS is non-empty.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: correctness: scripts/parse-codex-usage.sh:36-44
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Synthetic usage detection increments usage_count for usage shells with no numeric token fields. Stream of only {"usage":{}}-style events exits with "no usage events" despite usage-shaped objects, obscuring zero-total vs missing-usage failures. Only increment count when at least one token field is non-zero, or use distinct stderr messages for zero totals vs no objects.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: architecture: scripts/launch-review.sh:572-579
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Launchers do not verify TOTAL equals INPUT+CACHED_INPUT+OUTPUT before writing ledger/token-record rows. Helper regression could write inconsistent buckets that propagate into token-report and token-cost without a launcher guard. After parsing KV lines, assert totals and skip record-vendor when the identity fails.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_2: correctness: scripts/parse-codex-usage.sh:36-43
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] jq treats empty usage objects as present blocking top-level token field fallback. Codex emits {"usage":{},"input_tokens":N} (0.125 token_usage shape); parser counts the event but sums zero and fail-closes leaving no ledger row despite real usage. Require a non-null token field before accepting a usage object or include top-level input_tokens in the per-field coalesce when nested usage is empty.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_21: architecture: scripts/parse-codex-usage.md:47-58
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Per-field coalesce docs omit .msg.* token paths that jq uses. Fixture codex-msg-token-usage.jsonl and 0.125 top-level token_usage events rely on .msg.input_tokens; doc-only edits could drop jq paths and fail smoke tests silently in CI. Document .msg.input_tokens / .msg.cached_input_tokens / .msg.output_tokens in the coalesce lists to match parse-codex-usage.sh:41-43.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_22: architecture: scripts/launch-review.md:69-74
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan-required reference to parse-codex-usage.md is missing. Operators/contributors reading launch-review.md may not find the formal contract for KV output and fail-closed semantics. Add an explicit pointer to scripts/parse-codex-usage.md next to the parse-codex-usage.sh mention.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_3: code-quality: scripts/launch-review.sh:561-565
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] launch-review appends parse-codex-usage stderr to sidecar on failure but implement and CI swallow parse stderr. An implement run with a non-empty events file and schema mismatch shows no parse diagnostic in sidecar.log while review would surface it in the sidecar. Document asymmetry in launcher .md siblings or add optional append_errors_to sidecar parameter to a shared helper.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_4: code-quality: scripts/parse-codex-usage.md:47-49
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Documented input_tokens coalesce paths omit .msg.input_tokens and .input_tokens fallbacks present in jq. A contributor aligns jq to the doc and breaks codex-msg-token-usage.jsonl / Codex-native top-level token fields. Update parse-codex-usage.md coalesce list to match scripts/parse-codex-usage.sh lines 41-43 exactly.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_7: correctness: scripts/parse-codex-usage.sh:66-72
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] cached>input validation uses aggregated sums only not per-event Stream with one bad line (cached>input) plus valid lines passes aggregate check and emits wrong INPUT/CACHED_INPUT while TOTAL may look plausible In jq reduce fail-closed when any event coalesced cached exceeds coalesced input before summing; keep aggregate guard as backstop
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: correctness: scripts/parse-codex-usage.sh:36-44
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Parser sums all usage-bearing JSON objects with no token_usage type filter If Codex emits per-turn usage plus a final token_usage summary totals are double-counted and costs overstated Verify real --json stream; filter or dedupe summary events; extend codex-events smoke fixture
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_9: correctness: scripts/test-launch-review.sh
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Harness for SIDECAR=/dev/null no-parse contract removed in 8aef0664 Future change could record Codex tokens when sidecar is /dev/null without test catching it Restore stub test asserting no ledger row when sidecar init fails to /dev/null
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

