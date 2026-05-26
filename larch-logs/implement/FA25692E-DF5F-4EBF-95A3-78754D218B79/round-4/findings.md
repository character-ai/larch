### FINDING_1: code-quality: scripts/parse-codex-usage.sh:78-92
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] jq slurps the full JSONL file into $events before processing, contradicting the plan's line-streaming requirement. Long Codex runs can produce very large ${OUTPUT}.events.jsonl files; slurping raises peak memory and reintroduces the class of bug the plan's jq -nR streaming regression was meant to prevent. Refactor to streaming reduce over inputs | fromjson? without materializing the full event array; keep harness assertions green.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/lib-external-launcher-common.sh:33-71
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] New external_launcher_record_usage_from_events has no sibling .md update in this branch. Maintainers editing Cursor/Codex launchers cannot discover parse-fail sidecar append or token-record vs ledger modes from the canonical lib doc. Update scripts/lib-external-launcher-common.md with argv, fail-closed behavior, and output modes.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/lib-codex-launcher-common.md:1-9
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] codex_launcher_record_usage_from_events wrapper is undocumented in the per-tool stub. Contributors may not know the new entry point exists without reading launch scripts. Add wrapper to the stub and cross-link parse-codex-usage.md.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: scripts/parse-codex-usage.sh:34-92
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Monolithic ~60-line jq with dual rollup/reduce paths is hard to maintain. Future Codex schema changes require editing fragile inline jq; higher risk of subtle double-count or last-wins bugs. Split into staged jq filter or documented filter file plus bash bucket math.
- **Suggested revision**: Address the concern above.

### FINDING_5: correctness: scripts/parse-codex-usage.sh:79-82
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Last token_usage event wins; no test for multiple token_usage lines. If Codex emits more than one token_usage rollup per run, earlier usage is dropped and cost under-reports. Validate real CLI behavior; add multi-token_usage fixture and document policy.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: scripts/parse-codex-usage.sh:83-88,119-122
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate cached_tokens > input_tokens guard in jq and bash. Redundant logic increases drift risk if one site changes. Keep jq-only enforcement unless a non-jq fallback exists.
- **Suggested revision**: Address the concern above.

### FINDING_7: architecture: scripts/launch-review.sh:560-562 vs scripts/launch-codex-implement.sh:358
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Review gates token capture on EXIT_CODE==0; implement records unconditionally. Failed implement runs may still ledger Codex tokens while failed review runs do not, confusing cross-lane cost comparisons. Document intentional asymmetry or align gating policy across launchers.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: scripts/launch-review.sh:560-562
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Review records Codex usage only when EXIT_CODE is 0; implement and CI record whenever JSONL parses. Codex review exits 1 with valid token_usage in .events.jsonl: no codex_review ledger row, session cost omits Codex while implement/CI would record the same events. Document asymmetry in launcher docs or align all three launchers on the same exit-code vs parse-success rule.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: scripts/parse-codex-usage.sh:79-82
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] When token_usage events exist, parser uses last row only instead of summing multiple token_usage rows. Multiple incremental token_usage events (non-cumulative): TOTAL reflects last delta only; cost understated. Validate against real CLI; if incremental rows are possible, sum token_usage events or detect monotonic cumulative rollups.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: scripts/parse-codex-usage.sh:37-51
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] has_tokenish ignores total_tokens-only token_usage events. Stream only has {"type":"token_usage","total_tokens":N} without per-bucket fields: fail-closed, zero Codex cost in reports. Extend probes if Codex ships total-only rollups, or keep fail-closed with an explicit diagnostic.
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: scripts/test-token-vendor-scrapers.sh:223-249
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Per-bucket BLENDED_WARN regression stops at direct token-cost.sh flags, not render-cost-line.sh. A regression that zeroes D_IN/D_CACHED/D_OUT before render-cost-line would still show blended-rate warnings in final-summary while token-cost-only tests pass. Add a case through render-cost-line.sh (or render-final-summary wiring) with per-bucket Codex inputs and assert no BLENDED_WARN on stderr.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: scripts/test-render-cost-line.sh:11-33
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] render-cost-line harness never exercises per-bucket Codex CLI flags. The codex_args per-bucket branch at render-cost-line.sh:65-68 could break without failing make test-render-cost-line. Add one render-cost-line test using --codex-input-tokens/--codex-cached-input-tokens/--codex-output-tokens and compare to token-cost output.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: scripts/parse-codex-usage.sh:79-92
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Last token_usage event wins over summed per-turn usage. Future CLI emitting a partial final token_usage after richer per-turn events would under-report Codex cost silently. Document and fixture-test multi token_usage behavior; assert chosen rollup policy explicitly.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: scripts/launch-codex-implement.sh:358 vs scripts/launch-review.sh:560-561
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Implement records usage on failed exits; review does not; no implement harness for failure+usage. Failed implement run with JSONL usage may write vendor rows while failed review does not—contract drift untested. Add test-codex-implementer stub: non-zero exit + usage JSONL; assert ledger presence matches intended policy.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: scripts/test-lib-external-launcher-common.sh:1-141
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] external_launcher_record_usage_from_events lacks unit tests. Refactor regressions in token-record vs ledger paths or sidecar diagnostic append may slip until launcher integration tests fail. Add unit cases for record_usage_from_events success, fail-closed, and sidecar append.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: skills/implement/scripts/test-codex-implementer.sh:647-756
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Test 10 skipped entirely when jq is missing. Local make test-codex-implementer without jq passes without exercising --json or fail-closed ledger behavior. Split jq-independent argv/ledger-absence checks from jq JSONL row assertions.
- **Suggested revision**: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] risk-integration: branch-wide
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Branch bundles #2790 breadcrumb work and run-log flush with #2813 (~266 files). Unrelated harness failures can block merge despite solid Codex token tests. Triage CI failures by commit/file area; consider splitting PRs if CI noise persists.
- **Suggested revision**: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] architecture: scripts/test-parse-codex-usage.md:13
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Doc overstates co-location of launcher harnesses in shard 17. Contributors may assume test-launch-review runs in the same shard as test-parse-codex-usage. Clarify shard 17 holds parser + vendor-scrapers; launch-review/ci are shards 10/9.
- **Suggested revision**: Address the concern above.

### FINDING_19: **No command injection**: `EVENTS_FILE` is passed as a quoted `jq` input path; parsed values are digit-validated before `printf`/ledger writes; `token-ledger.sh` additionally enforces `is_uint` on bucket fields.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **No command injection**: `EVENTS_FILE` is passed as a quoted `jq` input path; parsed values are digit-validated before `printf`/ledger writes; `token-ledger.sh` additionally enforces `is_uint` on bucket fields.
- **Suggested revision**: Address the concern above.

### FINDING_20: **Fail-closed accounting**: Parse failure writes no ledger row / leaves `${OUTPUT}.token-record` empty; review launcher only records on `EXIT_CODE == 0`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Fail-closed accounting**: Parse failure writes no ledger row / leaves `${OUTPUT}.token-record` empty; review launcher only records on `EXIT_CODE == 0`.
- **Suggested revision**: Address the concern above.

### FINDING_21: **Secret / prompt leakage**: `*.events.jsonl` is excluded from `larch-log.sh` and `design-log-publish.sh`; `SECURITY.md` documents session-local-only handling; `test-design-log-publish.sh` asserts denied basenames (including `render-cache/`) do not publish.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Secret / prompt leakage**: `*.events.jsonl` is excluded from `larch-log.sh` and `design-log-publish.sh`; `SECURITY.md` documents session-local-only handling; `test-design-log-publish.sh` asserts denied basenames (including `render-cache/`) do not publish.
- **Suggested revision**: Address the concern above.

### FINDING_22: **Fixtures**: Checked-in JSONL contains only synthetic token counts, no credentials.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Fixtures**: Checked-in JSONL contains only synthetic token counts, no credentials.
- **Suggested revision**: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **security** `scripts/parse-codex-usage.sh:78-92` — The `jq` program materializes the entire events stream (`[inputs | …] as $events`) instead of true line-streaming. A hostile or buggy Codex run that emits a very large JSONL sidecar could cause high memory use in the launcher process (availability / same-UID DoS), not remote code execution. **Suggested fix:** If this becomes observable in production, cap file size before `jq` or switch to incremental reduction without building a full in-memory array.
- **Suggested revision**: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **security** `scripts/lib-external-launcher-common.sh:44-46` — On parse failure with a non-empty events file, `usage_err` is appended to the stderr sidecar. Diagnostics are fixed `larch_err` strings or generic `jq` errors (not event bodies), but sidecars can still carry session paths if `jq` echoes the input filename. Sidecars are publication-denied like events files; residual risk is operator-local forensics sharing. **Suggested fix:** Optional hardening: log parse failure only via `larch_err` to FD 3 / omit appending `usage_err` when it might contain paths.
- **Suggested revision**: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **security** `scripts/launch-review.sh:531-560` — Auth/transient classification remains stderr-only after stdout is split to `${OUTPUT}.events.jsonl`. This matches documented Codex CLI behavior and is tested; if a future CLI version routes auth/quota text only on the JSON stdout stream, retries would not trigger (operational misclassification, not credential bypass). **Suggested fix:** Monitor upstream CLI release notes; follow-up tee of non-JSON stdout lines into the sidecar only if needed.
- **Suggested revision**: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **security** `scripts/launch-codex-implement.sh:358` — Token capture runs regardless of `LAUNCHER_EXIT`, so a failed implementer run with a populated events file still records usage. Under the existing external-implementer trust model this is billing/integrity, not a new privilege boundary (compromised Codex already has workspace-write). **Suggested fix:** Align with `launch-review.sh` by gating `codex_launcher_record_usage_from_events` on `LAUNCHER_EXIT == 0` if under-reporting failed runs is desired.
- **Suggested revision**: Address the concern above.

### FINDING_27: risk-integration: scripts/parse-codex-usage.sh:79-92
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Trailing zero token_usage rollup discards earlier per-call usage Stream has msg.usage rows summing to real spend then a final type=token_usage with top-level zeros; parser takes rollup branch, TOTAL=0, fail-closed, no ledger row Prefer last non-zero token_usage or fall through to reduce/sum when final rollup is all-zero
- **Suggested revision**: Address the concern above.

### FINDING_28: architecture: scripts/launch-review.sh:560-561
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Review records tokens only on success; implement/CI record whenever parse succeeds Failed codex review with JSONL usage writes no vendor row; failed implement/CI with same JSONL would still record; session totals diverge Document lane policy or align exit-code gating across launchers
- **Suggested revision**: Address the concern above.

### FINDING_29: correctness: scripts/parse-codex-usage.sh:79
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Multiple token_usage events use last only, not sum If CLI emits incremental non-cumulative token_usage snapshots, reported totals undercount Document cumulative assumption; add fixture when CLI shape is known
- **Suggested revision**: Address the concern above.

### FINDING_30: risk-integration: scripts/parse-codex-usage.sh:78
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] jq slurps entire events file into memory Very long --json runs could use large RAM before parsing Consider streaming reduce if large sidecars appear in production
- **Suggested revision**: Address the concern above.

### FINDING_31: correctness: scripts/parse-codex-usage.sh:78-91
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Parser uses last type==token_usage rollup instead of summing all usage-bearing events as the plan requires. A Codex run whose JSONL contains per-call msg.usage rows plus a final token_usage line will bill only the rollup (or diverge from tests that assume full summation), conflicting with the plan edge case Multiple usage events per run summed across events. Align summation with the plan or formally change the contract in plan/docs/tests and add a mixed-stream regression for the chosen rule.
- **Suggested revision**: Address the concern above.

### FINDING_32: architecture: scripts/launch-review.sh:560-561 vs scripts/launch-codex-implement.sh:358
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Token recording is gated on EXIT_CODE==0 only in launch-review; implement and CI record whenever parse succeeds. A failed Codex review with parseable usage emits no ledger row while a failed implement/CI run with the same events would still attribute Codex cost, breaking the plan uniform launcher application. Standardize record-on-parse-success vs record-on-launcher-success across all three launchers and extend implement/CI harnesses to match test-launch-review.sh codex-failed-run.
- **Suggested revision**: Address the concern above.

### FINDING_33: correctness: scripts/lib-external-launcher-common.sh:44-46
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Shared helper appends parse-codex-usage stderr to the sidecar on parse failure; plan pseudocode silences stderr. Operators inspecting sidecar logs after a failed parse may see parser diagnostics mixed with Codex stderr, changing triage text not contemplated in the plan stderr-only auth contract. Remove sidecar append or document and test it in the three launcher .md siblings.
- **Suggested revision**: Address the concern above.

### FINDING_34: [OUT_OF_SCOPE] code-quality: scripts/parse-codex-usage.md:74
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Consumer list is incomplete. Doc readers may miss lib-external-launcher-common.sh as the canonical integration point. Add lib-external-launcher-common.sh and test-token-vendor-scrapers.sh to the consumer list.
- **Suggested revision**: Address the concern above.

