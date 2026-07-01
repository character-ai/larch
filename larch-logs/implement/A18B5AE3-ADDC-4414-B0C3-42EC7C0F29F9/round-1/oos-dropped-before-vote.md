### OOS_1: [OUT_OF_SCOPE] Step 4 post-notification dropped “confirmed”
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-wait-contract
- **Severity**: nit
- **Concern**: Step 4 post-notification prose drops `confirmed` (`After confirmed completion` → `After completion`). On a premature non-empty notification before `.completed/step-4` exists, an orchestrator reading only this section may parse tail stdout early. Entry is still gated by the immediate-background wait rule, but the qualifier was a useful guard against acting before durable completion.

### OOS_2: [OUT_OF_SCOPE] #5639 circuit-breaker rationale trimmed
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-wait-contract
- **Severity**: nit
- **Concern**: The #5639 circuit-breaker text no longer states that every turn end counts toward the cap regardless of tool calls; only prose-only turns are called out. Core rules remain and hook behavior is unchanged, but operators reading only this file may underestimate what increments the counter or why the breaker exists.

### OOS_3: [OUT_OF_SCOPE] Duplication between design SKILL NEVER rules and design-background-wait.md
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: Duplication between design SKILL NEVER rules and `design-background-wait.md` creates maintenance burden when wait contracts change. Pre-existing; consumer dedup is out of plan scope.

### OOS_4: [OUT_OF_SCOPE] Run-log churn in branch history adds review noise
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-wait-contract
- **Severity**: nit
- **Concern**: Branch history includes `06339cb36 chore(larch-logs): flush …` alongside the prose-compress commit. That run-log churn is outside the plan’s two-file scope and may add review noise unrelated to the wait-contract change (expected `/implement` artifact per testing review).

