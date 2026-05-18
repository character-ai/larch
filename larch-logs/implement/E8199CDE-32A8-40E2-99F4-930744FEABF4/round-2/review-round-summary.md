# Review Round 2

- Mode: `diff`
- Accepted findings: 4
- Rejected findings: 5
- Exonerated findings: 4
- Neutral findings: 0

## Accepted Findings

### FINDING_1: **Important** `risk-integration` `skills/implement/SKILL.md:278` drops parent-provided `LARCH_DYNAMIC_ARCHETYPES_MAX` when `/implement` is invoked with `--session-env`. The new handoff contract says parent session-env files may carry `LARCH_DYNAMIC_ARCHETYPES_MAX=<0..4>` (`skills/shared/subskill-invocation.md:167-169`), and `session-setup.sh` only preserves it when it owns `--write-session-env` (`scripts/session-setup.sh:420-422`), but `/implement` rewrites its own session-env and only includes `--dynamic-archetypes` when `dynamic_archetypes_value` came from an explicit `/implement` flag (`skills/implement/SKILL.md:266-279`). Concrete scenario: a parent writes `LARCH_DYNAMIC_ARCHETYPES_MAX=0` to disable scout and invokes `/implement --session-env parent/session-env.sh`; Step 0 drops the key, `scripts/run-step5-review.sh:111-159` sees no session key, and `review-and-fix.sh` defaults back to cap `4`, running dynamic reviewers anyway. Fix by having `/implement` read and validate `LARCH_DYNAMIC_ARCHETYPES_MAX` from the caller `SESSION_ENV_PATH` when no explicit flag was parsed, then pass that value into `write-session-env.sh`, or switch Step 0 to a session-setup/write-session-env path that preserves the validated caller key.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` `skills/implement/SKILL.md:278` drops parent-provided `LARCH_DYNAMIC_ARCHETYPES_MAX` when `/implement` is invoked with `--session-env`. The new handoff contract says parent session-env files may carry `LARCH_DYNAMIC_ARCHETYPES_MAX=<0..4>` (`skills/shared/subskill-invocation.md:167-169`), and `session-setup.sh` only preserves it when it owns `--write-session-env` (`scripts/session-setup.sh:420-422`), but `/implement` rewrites its own session-env and only includes `--dynamic-archetypes` when `dynamic_archetypes_value` came from an explicit `/implement` flag (`skills/implement/SKILL.md:266-279`). Concrete scenario: a parent writes `LARCH_DYNAMIC_ARCHETYPES_MAX=0` to disable scout and invokes `/implement --session-env parent/session-env.sh`; Step 0 drops the key, `scripts/run-step5-review.sh:111-159` sees no session key, and `review-and-fix.sh` defaults back to cap `4`, running dynamic reviewers anyway. Fix by having `/implement` read and validate `LARCH_DYNAMIC_ARCHETYPES_MAX` from the caller `SESSION_ENV_PATH` when no explicit flag was parsed, then pass that value into `write-session-env.sh`, or switch Step 0 to a session-setup/write-session-env path that preserves the validated caller key.
- **Suggested revision**: Address the concern above.


### FINDING_5: correctness: skills/implement/SKILL.md:1348-1352
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Step 5 `dynamic_archetypes_cap` derivation ignores process env tier used by `review-and-fix.sh`. `LARCH_DYNAMIC_ARCHETYPES_MAX=1` in shell, no flags, no session key: review uses cap 1 but breadcrumb can show cap=4. Mirror review-and-fix resolution for the printed cap or document intentional divergence.
- **Suggested revision**: Address the concern above.


### FINDING_6: correctness: skills/implement/SKILL.md:1348-1352
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Step 5 banner derives dynamic_archetypes_cap only from explicit flags or session-env (fallback 4), ignoring non-empty process env that review-and-fix honors. Operator exports LARCH_DYNAMIC_ARCHETYPES_MAX=1 without persisting it to session-env and without /implement dynamic flags; Step 5 prints cap=4 while review-and-fix uses 1. Mirror review-and-fix resolution in Step 5 prose (include process env) or persist resolved cap to session-env whenever process env is set; align banner with runtime.
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: skills/implement/SKILL.md:1348-1352
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Step 5 breadcrumb derivation for dynamic_archetypes_cap ignores process LARCH_DYNAMIC_ARCHETYPES_MAX. review-and-fix.sh uses env before session default; operator with only shell env sees printed cap 4 while scout runs at env N. Mirror review-and-fix priority (env before session fallback) or remove misleading cap from prose.
- **Suggested revision**: Address the concern above.


