### OOS_1: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-step5-launcher-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/step-5-review.sh:36-45` vs `python/review_and_fix.py:1525-1532` — Cap precedence still differs (shell: session-env → process env → default; Python `_dynamic_archetypes`: process env → session-env → default). This predates the fold (`step-5-entry.sh` used the same shell order). When sources disagree, the banner can show cap N while dispatch uses or rejects cap M. Worth aligning, but not introduced by this branch.
- **Suggested revision**: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-prompt-fences-output.txt
- **Concern**: - **architecture** `skills/implement/scripts/step-5-review.sh:36-49` and `python/review_and_fix.py:1525-1530` — Banner cap resolution remains session-env-first in the wrapper while `_dynamic_archetypes()` is process-env-first, then session-env. That mismatch predates this branch (`step-5-entry.sh` used the same order); this change preserves it rather than introducing it.
- **Suggested revision**: Address the concern above.


### OOS_3: [OUT_OF_SCOPE] correctness: skills/implement/scripts/step-5-review.sh:36-49
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Banner cap precedence (session-env then process) differs from review_and_fix._dynamic_archetypes (process then session-env). session-env=2 and process LARCH_DYNAMIC_ARCHETYPES_MAX=3 prints cap=2 but review runs with 3 dynamic archetypes. Pre-existing from step-5-entry.sh; align wrapper with _dynamic_archetypes or share one resolver.
- **Suggested revision**: Address the concern above.


### OOS_4: correctness: scripts/test-implement-anti-polling-rule.sh:75-77
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] Anti-polling harness still pins the old direct review-and-fix Step 5 literal after SKILL.md switched to step-5-review.sh bash scripts/test-implement-anti-polling-rule.sh fails, so make lint cannot stay green Update the pinned literal and docs/linting.md to match the new wrapper delegation while preserving the anti-polling assertion
- **Suggested revision**: Address the concern above.


### OOS_5: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 2. **risk-integration** `skills/implement/scripts/step-5-review.sh:36-47` — Banner `dynamic_archetypes_cap` uses session-env-first precedence (copied from `step-5-entry.sh`), while `python/review_and_fix.py:1525-1530` `_dynamic_archetypes()` uses process-env-first. When sources disagree, the banner can show cap N while dispatch uses cap M (pre-existing mismatch, not introduced here). **Suggested fix:** Align wrapper precedence with `_dynamic_archetypes()` or extract a shared resolver.
- **Suggested revision**: Address the concern above.


