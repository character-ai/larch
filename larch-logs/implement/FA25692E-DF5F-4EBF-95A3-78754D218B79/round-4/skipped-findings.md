### FINDING_1: code-quality: scripts/parse-codex-usage.sh:78-92
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] jq slurps the full JSONL file into $events before processing, contradicting the plan's line-streaming requirement. Long Codex runs can produce very large ${OUTPUT}.events.jsonl files; slurping raises peak memory and reintroduces the class of bug the plan's jq -nR streaming regression was meant to prevent. Refactor to streaming reduce over inputs | fromjson? without materializing the full event array; keep harness assertions green.
- **Suggested revision**: Address the concern above.



### FINDING_11: risk-integration: scripts/test-token-vendor-scrapers.sh:223-249
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Per-bucket BLENDED_WARN regression stops at direct token-cost.sh flags, not render-cost-line.sh. A regression that zeroes D_IN/D_CACHED/D_OUT before render-cost-line would still show blended-rate warnings in final-summary while token-cost-only tests pass. Add a case through render-cost-line.sh (or render-final-summary wiring) with per-bucket Codex inputs and assert no BLENDED_WARN on stderr.
- **Suggested revision**: Address the concern above.



### FINDING_2: code-quality: scripts/lib-external-launcher-common.sh:33-71
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] New external_launcher_record_usage_from_events has no sibling .md update in this branch. Maintainers editing Cursor/Codex launchers cannot discover parse-fail sidecar append or token-record vs ledger modes from the canonical lib doc. Update scripts/lib-external-launcher-common.md with argv, fail-closed behavior, and output modes.
- **Suggested revision**: Address the concern above.



### FINDING_27: risk-integration: scripts/parse-codex-usage.sh:79-92
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Trailing zero token_usage rollup discards earlier per-call usage Stream has msg.usage rows summing to real spend then a final type=token_usage with top-level zeros; parser takes rollup branch, TOTAL=0, fail-closed, no ledger row Prefer last non-zero token_usage or fall through to reduce/sum when final rollup is all-zero
- **Suggested revision**: Address the concern above.



