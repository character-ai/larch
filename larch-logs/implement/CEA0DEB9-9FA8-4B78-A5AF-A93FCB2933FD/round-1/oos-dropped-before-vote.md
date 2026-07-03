### OOS_1: [OUT_OF_SCOPE] Missing ratchet pins for trimmed rule 2/4/5 prose
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Rules 2/4/5 prose was trimmed without new pins; rule 2 was never pinned. Future trims could weaken dedup/notification guidance without CI detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Out of plan scope; add pins only if those NEVER rules need ratchet-style protection.

### OOS_2: [OUT_OF_SCOPE] No timeout/fallback harness coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: No harness simulates `AskUserQuestion` timeout or fallback orchestration. The prompt-only fix cannot be proven in CI, so regressions would depend on live agent behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Accept per plan scope or add a future offline orchestration contract test if tooling allows.

### OOS_3: [OUT_OF_SCOPE] Implement parity for no-response re-ask is out of issue scope
- **Reviewer(s)**: dyn-dyn-prompt-contract
- **Severity**: nit
- **Concern**: `/implement` Step 2.3 Q/A loops use `AskUserQuestion` without an equivalent no-response re-ask rule. Operators may expect parity after this `/design`-only fix, but that parity was explicitly out of issue scope.

### OOS_4: [OUT_OF_SCOPE] Implement run-log artifacts inflate the diff
- **Reviewer(s)**: dyn-dyn-prompt-contract
- **Severity**: nit
- **Concern**: The branch also adds implement run-log artifacts under `larch-logs/implement/CEA0DEB9-.../` alongside the two-file feature change. That is normal `/implement` output, not part of the planned diff, but it inflates the PR beyond `skills/design/SKILL.md` and `scripts/test-design-structure.sh`.

### OOS_5: [OUT_OF_SCOPE] Rule 4–5 compression tradeoff accepted
- **Reviewer(s)**: dyn-dyn-prompt-contract
- **Severity**: nit
- **Concern**: Rule 4–5 compression removed some rationale while retaining the pinned literals and the delegated background-wait reference. That matches the plan’s closure-ratchet tradeoff; no separate finding unless runtime regressions appear.

