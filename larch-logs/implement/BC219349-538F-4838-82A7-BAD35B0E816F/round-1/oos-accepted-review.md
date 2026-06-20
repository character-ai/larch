### OOS_1: [OUT_OF_SCOPE] risk-integration: AGENTS.md
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] AGENTS.md still recommends design terminal-sentinel probes for premature background notifications while implement SKILL now forbids probing design sentinels. An /implement operator following AGENTS.md may probe $DESIGN_TMPDIR/.completed/*-terminal paths that implement never writes, wasting turns without recovery signal. Mirror the implement SKILL NEVER #8 carve-out in AGENTS.md.
- **Suggested revision**: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] correctness: python/audit_runs.py:713-715 vs skills/fluff-analysis/scripts/fluff-analysis.py:366-406
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] audit_runs and fluff-analysis use different emptiness predicates before tally fallback. JSONL containing only dict rows without outcome would suppress tally fallback in audit_runs but activate it in fluff-analysis, producing inconsistent counts between audit and fluff reports. Share one helper or apply the same outcome/non-empty-row filter in both consumers.
- **Suggested revision**: Address the concern above.


### OOS_3: [OUT_OF_SCOPE] architecture: skills/shared/orchestrator-never.md NEVER #3
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Design-centric recovery prose remains immediately after the new implement notification-only note. Implement orchestrators may read the generic probe-on-absent guidance as still applying to implement fences. Split design sentinel-probe guidance from implement notification-only recovery into separate sentences.
- **Suggested revision**: Address the concern above.


### OOS_4: [OUT_OF_SCOPE] architecture: skills/fluff-analysis/scripts/fluff-analysis.py:409-428
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Duplicate tally-fallback logic in fluff-analysis and audit_runs without shared tests. Implementations could diverge on edge cases over time. Extract shared helper or add cross-consumer parity fixture if drift becomes a concern.
- **Suggested revision**: Address the concern above.


### OOS_5: [OUT_OF_SCOPE] The anti-polling harness was updated for implement (`scripts/test-implement-anti-polling-rule.sh:122-128`, `scripts/test-implement-anti-polling-rule.md:48-50`), but it still pins AGENTS.md to design-style foreground-probe wording without an implement exception (`scripts/test-implement-anti-polling-rule.sh:102-116`). That lets CI pass while Tier-1 and skill-level implement recovery guidance stay contradictory.
- **Reviewer**: dyn-recovery-contract-output.txt
- **Concern**: - The anti-polling harness was updated for implement (`scripts/test-implement-anti-polling-rule.sh:122-128`, `scripts/test-implement-anti-polling-rule.md:48-50`), but it still pins AGENTS.md to design-style foreground-probe wording without an implement exception (`scripts/test-implement-anti-polling-rule.sh:102-116`). That lets CI pass while Tier-1 and skill-level implement recovery guidance stay contradictory.
- **Suggested revision**: Address the concern above.


