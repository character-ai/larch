### OOS_1: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 2. **risk-integration** `skills/shared/orchestrator-never.md` — The shared NEVER list still lacks the premature-notification recovery carve-out (filed as OOS #4280, blocked by #4268). The harness continues to pin only the result-file sleep-loop literal there. Intentional per plan non-goals; a future regression could drop recovery guidance from skill files while `orchestrator-never.md` stays stale.
- **Suggested revision**: Address the concern above.


### OOS_2: **risk-integration** `python/migration_lint.py:280-283` — The new retired-script lint prefilter skips every line that lacks `.sh` or `.md`, but `python/migrated-scripts.tsv` already contains retired paths with `.py`, `.awk`, `.jq`, `.bash`, and `.json` suffixes, such as `python/ci_cli.py` and `.claude/skills/.../combinable-issues-title-filter.jq`. This regresses `make lint-retired-scripts`: a tracked file can now reintroduce an exact retired path like `python/ci_cli.py` and the lint will never consider that line. **Suggested fix:** Replace the hard-coded `.sh` / `.md` gate with a basename-set prefilter only, or derive the allowed suffix gate from the actual retired manifest entries.
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: - **risk-integration** `python/migration_lint.py:280-283` — The new retired-script lint prefilter skips every line that lacks `.sh` or `.md`, but `python/migrated-scripts.tsv` already contains retired paths with `.py`, `.awk`, `.jq`, `.bash`, and `.json` suffixes, such as `python/ci_cli.py` and `.claude/skills/.../combinable-issues-title-filter.jq`. This regresses `make lint-retired-scripts`: a tracked file can now reintroduce an exact retired path like `python/ci_cli.py` and the lint will never consider that line. **Suggested fix:** Replace the hard-coded `.sh` / `.md` gate with a basename-set prefilter only, or derive the allowed suffix gate from the actual retired manifest entries.
- **Suggested revision**: Address the concern above.


### OOS_3: [OUT_OF_SCOPE] `skills/shared/orchestrator-never.md` lacks the premature-notification recovery carve-out (tracked as OOS #4280; explicitly out of plan scope). The branch widens the gap between skill-level and shared-level wait contracts rather than closing it.
- **Reviewer**: dyn-wait-contract-output.txt
- **Concern**: - `skills/shared/orchestrator-never.md` lacks the premature-notification recovery carve-out (tracked as OOS #4280; explicitly out of plan scope). The branch widens the gap between skill-level and shared-level wait contracts rather than closing it.
- **Suggested revision**: Address the concern above.


### OOS_4: [OUT_OF_SCOPE] risk-integration: AGENTS.md:85
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Stale cross-reference "NEVER #9" on the Monitor/polling bullet; rules are in NEVER #8. Operators land on envelope-validation guidance when debugging Monitor misuse. Update the reference to NEVER #8 (deferred by plan).
- **Suggested revision**: Address the concern above.


### OOS_5: [OUT_OF_SCOPE] architecture: skills/shared/orchestrator-never.md:11
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] orchestrator-never.md rule #4 bans until+sleep loops without the new recovery carve-out (OOS #4280). Recovery after premature notification may be refused when orchestrator-never is treated as authoritative. Add matching carve-out in orchestrator-never.md per #4280.
- **Suggested revision**: Address the concern above.


