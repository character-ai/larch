### OOS_1: [OUT_OF_SCOPE] `skills/implement/references/stall-recovery.md:42-44` still documents only `protected-path` operator warnings and `step2-impl` recovery prose; it does not mention `submodule-restricted`. The branch updates `stall-recovery-report.md` but not this Step 18a procedure reference, so operators following that doc will not see submodule-specific routing.
- **Reviewer**: dyn-stall-recovery-output.txt
- **Concern**: - `skills/implement/references/stall-recovery.md:42-44` still documents only `protected-path` operator warnings and `step2-impl` recovery prose; it does not mention `submodule-restricted`. The branch updates `stall-recovery-report.md` but not this Step 18a procedure reference, so operators following that doc will not see submodule-specific routing.
- **Suggested revision**: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 1. **risk-integration** `skills/implement/references/stall-recovery.md:42-43` — Normative Step 18a prose documents protected-path inline resume but not `submodule-restricted`, while `skills/implement/SKILL.md` now has submodule-specific warnings and `RESUME_HINT=step2-impl`. Operators reading only the reference doc may miss the new class. **Suggested fix:** Add a parallel bullet for `submodule-restricted` when touching stall-recovery docs.
- **Suggested revision**: Address the concern above.


