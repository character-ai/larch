### [Plan Review] FINDING_10

### FINDING_10: Resume SKILL.md prose contradicts itself on whether argv flags must match
- **Reviewer(s)**: 2 reviewers (codex-dyn-plan-coherence, codex-innovation)
- **Severity**: nit
- **Focus area**: risk-integration
- **Concern**: SKILL.md update step 4 says: "the new per-key argv flags ARE recorded in state on cold start, so resume must NOT re-pass them" — and adds: "On resume (state file present), the seven argv-init flags ... are silently ignored by `ship-pr.sh`; they may be omitted to keep the resume invocation short, but passing them is harmless." The two clauses are reconcilable but the "must NOT re-pass" / "passing them is harmless" wording is mildly contradictory.
- **Suggested revision**: Replace "must NOT re-pass them" with "do not need to re-pass them" so the clarification ("passing them is harmless") flows naturally. Or drop the clarification entirely and keep just "On resume, argv-init flags are silently ignored."

---


### [Plan Review] FINDING_7

### FINDING_7: DECISION_3 labeled "7 flags" but plan introduces 8 new flags total
- **Reviewer(s)**: 3 reviewers (cursor-dyn-plan-coherence ×3, codex-dyn-plan-coherence)
- **Severity**: nit
- **Focus area**: architecture
- **Concern**: DECISION_3 vote was "Only flags for varying values" with 7 named per-key flags. The plan also adds `--force-init-state`, making 8 new flags. The DECISION_3 label undercount confuses the relationship between the dialectic vote and the implemented surface.
- **Suggested revision**: Reword the DECISION_3 summary line to "7 caller-varying per-key flags plus 1 control flag (`--force-init-state`) — 8 new flags total." Note explicitly that `--force-init-state` is a control flag, not a state-key flag, so it doesn't count against the DECISION_3 minimum-flag-set vote.


