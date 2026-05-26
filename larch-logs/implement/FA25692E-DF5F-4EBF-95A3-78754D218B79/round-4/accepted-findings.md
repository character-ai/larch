### FINDING_1: code-quality: scripts/parse-codex-usage.sh:78-92
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] jq slurps the full JSONL file into $events before processing, contradicting the plan's line-streaming requirement. Long Codex runs can produce very large ${OUTPUT}.events.jsonl files; slurping raises peak memory and reintroduces the class of bug the plan's jq -nR streaming regression was meant to prevent. Refactor to streaming reduce over inputs | fromjson? without materializing the full event array; keep harness assertions green.
- **Suggested revision**: Address the concern above.


### FINDING_11: risk-integration: scripts/test-token-vendor-scrapers.sh:223-249
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Per-bucket BLENDED_WARN regression stops at direct token-cost.sh flags, not render-cost-line.sh. A regression that zeroes D_IN/D_CACHED/D_OUT before render-cost-line would still show blended-rate warnings in final-summary while token-cost-only tests pass. Add a case through render-cost-line.sh (or render-final-summary wiring) with per-bucket Codex inputs and assert no BLENDED_WARN on stderr.
- **Suggested revision**: Address the concern above.


### FINDING_14: risk-integration: scripts/launch-codex-implement.sh:358 vs scripts/launch-review.sh:560-561
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Implement records usage on failed exits; review does not; no implement harness for failure+usage. Failed implement run with JSONL usage may write vendor rows while failed review does not—contract drift untested. Add test-codex-implementer stub: non-zero exit + usage JSONL; assert ledger presence matches intended policy.
- **Suggested revision**: Address the concern above.


### FINDING_2: code-quality: scripts/lib-external-launcher-common.sh:33-71
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] New external_launcher_record_usage_from_events has no sibling .md update in this branch. Maintainers editing Cursor/Codex launchers cannot discover parse-fail sidecar append or token-record vs ledger modes from the canonical lib doc. Update scripts/lib-external-launcher-common.md with argv, fail-closed behavior, and output modes.
- **Suggested revision**: Address the concern above.


### FINDING_27: risk-integration: scripts/parse-codex-usage.sh:79-92
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Trailing zero token_usage rollup discards earlier per-call usage Stream has msg.usage rows summing to real spend then a final type=token_usage with top-level zeros; parser takes rollup branch, TOTAL=0, fail-closed, no ledger row Prefer last non-zero token_usage or fall through to reduce/sum when final rollup is all-zero
- **Suggested revision**: Address the concern above.


### FINDING_32: architecture: scripts/launch-review.sh:560-561 vs scripts/launch-codex-implement.sh:358
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Token recording is gated on EXIT_CODE==0 only in launch-review; implement and CI record whenever parse succeeds. A failed Codex review with parseable usage emits no ledger row while a failed implement/CI run with the same events would still attribute Codex cost, breaking the plan uniform launcher application. Standardize record-on-parse-success vs record-on-launcher-success across all three launchers and extend implement/CI harnesses to match test-launch-review.sh codex-failed-run.
- **Suggested revision**: Address the concern above.


### FINDING_33: correctness: scripts/lib-external-launcher-common.sh:44-46
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Shared helper appends parse-codex-usage stderr to the sidecar on parse failure; plan pseudocode silences stderr. Operators inspecting sidecar logs after a failed parse may see parser diagnostics mixed with Codex stderr, changing triage text not contemplated in the plan stderr-only auth contract. Remove sidecar append or document and test it in the three launcher .md siblings.
- **Suggested revision**: Address the concern above.


### FINDING_7: architecture: scripts/launch-review.sh:560-562 vs scripts/launch-codex-implement.sh:358
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Review gates token capture on EXIT_CODE==0; implement records unconditionally. Failed implement runs may still ledger Codex tokens while failed review runs do not, confusing cross-lane cost comparisons. Document intentional asymmetry or align gating policy across launchers.
- **Suggested revision**: Address the concern above.


