# Review Round 1

- Mode: `diff`
- Accepted findings: 4
- Rejected findings: 3
- Exonerated findings: 2
- Neutral findings: 0

## Accepted Findings

### FINDING_3: correctness: scripts/auto-resolve-changelog.sh:2388-2428 scripts/ship-pr.sh:1320-1325
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] CHANGELOG.rst is routed through a Markdown ##-only merger. Real .rst changelogs rarely use ## headings, so auto-resolve exits 1 and the 30-minute vendor path is still used for .rst-only conflicts, contrary to the plan’s intent to treat .rst like .md for deterministic resolution. Add RST-aware parsing, or restrict the auto branch to supported formats and document .rst as vendor-only so the plan matches behavior.
- **Suggested revision**: Address the concern above.


### FINDING_4: correctness: scripts/ship-pr.sh:1320-1336
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] case arm uses .claude-plugin/plugin.json against basename _base_cf so plugin.json conflicts never hit git checkout --ours Rebase conflicts on .claude-plugin/plugin.json always go to vendor instead of deterministic ours resolution; extra latency/cost and diverges from implementation plan Match basename plugin.json with path guard on $_cf or case on full relative path for .claude-plugin/plugin.json
- **Suggested revision**: Address the concern above.


### FINDING_6: risk-integration: scripts/ship-pr.sh:1305-1357
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Missing CONFLICT_FILES= in rebase stdout leaves vendor_conflict_csv empty. Vendor runs without --conflict-files even though conflicts may exist, so the plan’s conflict context injection is skipped on parse failure or stale helpers. Fall back to git diff --name-only --diff-filter=U when kv_value is empty before launching the vendor.
- **Suggested revision**: Address the concern above.


### FINDING_8: risk-integration: scripts/test-ship-pr.sh:417-578
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No harness for CHANGELOG.rst or bare CHANGELOG in run_rebase_rebump pre-pass Regression in non-md changelog handling or case wiring could ship untested Extend fixtures to cover CHANGELOG.rst and CHANGELOG conflict filenames
- **Suggested revision**: Address the concern above.


