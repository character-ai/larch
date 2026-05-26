### FINDING_12: risk-integration: scripts/test-render-cost-line.sh:11-33
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] render-cost-line harness never exercises per-bucket Codex CLI flags. The codex_args per-bucket branch at render-cost-line.sh:65-68 could break without failing make test-render-cost-line. Add one render-cost-line test using --codex-input-tokens/--codex-cached-input-tokens/--codex-output-tokens and compare to token-cost output.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_15: risk-integration: scripts/test-lib-external-launcher-common.sh:1-141
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] external_launcher_record_usage_from_events lacks unit tests. Refactor regressions in token-record vs ledger paths or sidecar diagnostic append may slip until launcher integration tests fail. Add unit cases for record_usage_from_events success, fail-closed, and sidecar append.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_17: [OUT_OF_SCOPE] risk-integration: branch-wide
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Branch bundles #2790 breadcrumb work and run-log flush with #2813 (~266 files). Unrelated harness failures can block merge despite solid Codex token tests. Triage CI failures by commit/file area; consider splitting PRs if CI noise persists.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_18: [OUT_OF_SCOPE] architecture: scripts/test-parse-codex-usage.md:13
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Doc overstates co-location of launcher harnesses in shard 17. Contributors may assume test-launch-review runs in the same shard as test-parse-codex-usage. Clarify shard 17 holds parser + vendor-scrapers; launch-review/ci are shards 10/9.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_23: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **security** `scripts/parse-codex-usage.sh:78-92` — The `jq` program materializes the entire events stream (`[inputs | …] as $events`) instead of true line-streaming. A hostile or buggy Codex run that emits a very large JSONL sidecar could cause high memory use in the launcher process (availability / same-UID DoS), not remote code execution. **Suggested fix:** If this becomes observable in production, cap file size before `jq` or switch to incremental reduction without building a full in-memory array.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_24: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **security** `scripts/lib-external-launcher-common.sh:44-46` — On parse failure with a non-empty events file, `usage_err` is appended to the stderr sidecar. Diagnostics are fixed `larch_err` strings or generic `jq` errors (not event bodies), but sidecars can still carry session paths if `jq` echoes the input filename. Sidecars are publication-denied like events files; residual risk is operator-local forensics sharing. **Suggested fix:** Optional hardening: log parse failure only via `larch_err` to FD 3 / omit appending `usage_err` when it might contain paths.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_25: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **security** `scripts/launch-review.sh:531-560` — Auth/transient classification remains stderr-only after stdout is split to `${OUTPUT}.events.jsonl`. This matches documented Codex CLI behavior and is tested; if a future CLI version routes auth/quota text only on the JSON stdout stream, retries would not trigger (operational misclassification, not credential bypass). **Suggested fix:** Monitor upstream CLI release notes; follow-up tee of non-JSON stdout lines into the sidecar only if needed.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_26: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **security** `scripts/launch-codex-implement.sh:358` — Token capture runs regardless of `LAUNCHER_EXIT`, so a failed implementer run with a populated events file still records usage. Under the existing external-implementer trust model this is billing/integrity, not a new privilege boundary (compromised Codex already has workspace-write). **Suggested fix:** Align with `launch-review.sh` by gating `codex_launcher_record_usage_from_events` on `LAUNCHER_EXIT == 0` if under-reporting failed runs is desired.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_3: code-quality: scripts/lib-codex-launcher-common.md:1-9
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] codex_launcher_record_usage_from_events wrapper is undocumented in the per-tool stub. Contributors may not know the new entry point exists without reading launch scripts. Add wrapper to the stub and cross-link parse-codex-usage.md.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_34: [OUT_OF_SCOPE] code-quality: scripts/parse-codex-usage.md:74
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Consumer list is incomplete. Doc readers may miss lib-external-launcher-common.sh as the canonical integration point. Add lib-external-launcher-common.sh and test-token-vendor-scrapers.sh to the consumer list.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

